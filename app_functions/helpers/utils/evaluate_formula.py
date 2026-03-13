import re
import ast
import math
from typing import Callable, Any, Mapping, Literal, Iterable

from classes.datafeed import Datafeed
from common.complex_types import DfValueMap
from utils.ts_utils import create_grid
from app_functions.helpers.utils.constants import DEFAULT_TOT_RESET_VALUE
from app_functions.helpers.utils import formula_functions


# validate AST nodes to prevent unsafe constructs
ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.IfExp,
    ast.Compare,
    ast.IsNot,
    ast.Constant,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.FloorDiv,
    ast.USub,
    ast.UAdd,
    ast.Tuple,
    ast.List,
    ast.Dict,
)

MATH_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "sqrt": math.sqrt,
    "pow": math.pow,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "exp": math.exp,
    "log": math.log,
}


def get_bundle(bundle_name: str) -> Mapping[str, Callable[..., Any]]:
    """Return a validated formula-function bundle by name."""
    bundle = formula_functions.__dict__.get(bundle_name)
    if bundle is None:
        raise ValueError(f"Function bundle '{bundle_name}' does not exist")
    if not isinstance(bundle, Mapping):
        raise ValueError(f"Function bundle '{bundle_name}' has invalid format")

    for func_name, func_impl in bundle.items():
        if not callable(func_impl):
            raise ValueError(f"Function '{func_name}' in bundle '{bundle_name}' is not callable")

    return bundle


class _Validator(ast.NodeVisitor):
    def generic_visit(self, node):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"Unsafe expression node: {node.__class__.__name__}")
        super().generic_visit(node)


def _split_top_level_sub_args(raw_args: str) -> tuple[str, str]:
    depth = 0
    in_string = False
    string_quote = ""

    for i, ch in enumerate(raw_args):
        if in_string:
            if ch == string_quote and (i == 0 or raw_args[i - 1] != "\\"):
                in_string = False
            continue

        if ch in ('"', "'"):
            in_string = True
            string_quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            left = raw_args[:i].strip()
            right = raw_args[i + 1:].strip()
            if not left or not right:
                raise ValueError("Incorrect formula")
            return left, right

    raise ValueError("Incorrect formula")


def _replace_sub_calls(expr: str) -> str:
    """Rewrites SUB(a, b) into (a if a is not None else b), supports nesting."""
    out = expr

    while True:
        start = out.find("SUB(")
        if start == -1:
            return out

        i = start + 3
        depth = 1
        in_string = False
        string_quote = ""

        while i < len(out):
            ch = out[i]
            if in_string:
                if ch == string_quote and out[i - 1] != "\\":
                    in_string = False
            else:
                if ch in ('"', "'"):
                    in_string = True
                    string_quote = ch
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        break
            i += 1

        if depth != 0:
            raise ValueError("Incorrect formula")

        inner = out[start + 4: i]
        left, right = _split_top_level_sub_args(inner)
        replacement = f"(({left}) if ({left}) is not None else ({right}))"
        out = out[:start] + replacement + out[i + 1:]


def _unwrap_total(expr: str) -> tuple[bool, str]:
    """Extract TOTAL(inner_expr) when TOTAL is the root expression."""
    stripped = expr.strip()
    if not stripped.startswith("TOTAL("):
        return False, expr

    i = len("TOTAL(")
    depth = 1
    in_string = False
    string_quote = ""

    while i < len(stripped):
        ch = stripped[i]
        if in_string:
            if ch == string_quote and stripped[i - 1] != "\\":
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                string_quote = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
        i += 1

    if depth != 0 or i != len(stripped) - 1:
        raise ValueError("Incorrect formula")

    return True, stripped[len("TOTAL("): i]


def evaluate_formula(
    df: Datafeed,
    df_value_map: DfValueMap,
    settings: Mapping[str, Any],
    funcs: Iterable[str],
    start_rts: int,
    end_rts: int,
    add_to_alarm_payload: Callable[[str, dict | None, int, Literal["e", "w", "i"]], None],
    **kwargs: Any,
) -> None:
    """
    Evaluate a derived-datafeed formula over (start_rts, end_rts] and write results
    directly into df_value_map under df.name.

    Supported formula syntax examples:
    SUB(dfs["Water total 1"], 0) + sqrt(SUB(dfs["Bdn temp"], stgs["temp_subst"]))
    TOTAL(dfs["water_impulses"] * stgs["water_weight"])

    Rules and behavior:
    - Datafeed references use same-timestamp syntax: dfs["name"].
    - Setting references use stgs["key"].
    - SUB(value, fallback) substitutes only when value is None.
    - TOTAL(expr) is supported only as the root wrapper; for each timestamp,
        expr is accumulated onto the previous value.
    - Available callable names include built-in math functions
        (sqrt, pow, sin, cos, tan, exp, log) plus functions loaded from
        bundles listed in funcs.
    - Formula text is tokenized and then all whitespace in the safe expression
        is removed before AST parsing.

    Execution details:
    - kwargs["last_value"] seeds TOTAL accumulation (defaults to 0 when missing/None).
    - kwargs["tot_reset_value"] overrides the TOTAL reset threshold
        (defaults to DEFAULT_TOT_RESET_VALUE).
    - If any required dfs value is None at a timestamp, that timestamp is
        silently skipped (no alarm, no output value).
    - Setup/validation errors (invalid grid, missing settings/bundles, malformed
        formula) raise ValueError.
    - Per-timestamp evaluation errors are reported via add_to_alarm_payload with
        warning severity and evaluation continues.
    """

    # extract formula and remove all non-printable characters and spaces
    formula = "".join(ch for ch in df.formula if ch.isprintable())
    tres = df.time_resample
    use_total, formula = _unwrap_total(formula)

    # Build runtime function namespace from math + requested bundles.
    runtime_functions: dict[str, Callable[..., Any]] = dict(MATH_FUNCTIONS)
    for bundle_name in funcs:
        bundle = get_bundle(bundle_name)
        for func_name, func_impl in bundle.items():
            runtime_functions[func_name] = func_impl

    raw_last_value = kwargs.get("last_value")
    last_value = 0 if raw_last_value is None else raw_last_value
    raw_tot_reset_value = kwargs.get("tot_reset_value")
    tot_reset_value = DEFAULT_TOT_RESET_VALUE if raw_tot_reset_value is None else raw_tot_reset_value

    # --- parse formula to find referenced datafeeds, functions and settings ---
    # find all occurrences like dfs["Some name"] and stgs["key"]
    df_names: set[str] = set(re.findall(r'dfs\["([^\"]+)"\]', formula))
    setting_names: set[str] = set(re.findall(r'stgs\["([^\"]+)"\]', formula))

    # create evaluation grid based on derived df time_resample
    try:
        grid = create_grid(start_rts + df.time_resample, end_rts, df.time_resample)
    except Exception as e:
        raise ValueError(f"Unable to create grid, {e}")

    # prepare replacements for tokens in formula to create a safe expression
    # replace dfs["Name"] -> __DF_<idx>
    repl_map: dict[str, str] = {}
    df_token_map: dict[str, str] = {}
    for i, name in enumerate(sorted(df_names)):
        token = f"__DF_{i}"
        repl_map[f'dfs["{name}"]'] = token
        df_token_map[token] = name

    # replace stgs["key"] -> __SET_<idx>
    set_map: dict[str, Any] = {}
    for i, name in enumerate(sorted(setting_names)):
        token = f"__SET_{i}"
        repl_map[f'stgs["{name}"]'] = token
        # pull value from provided settings dict (top-level)
        if (sv := settings.get(name)) is None:
            raise ValueError(f"Setting '{name}' referenced in formula is missing")
        set_map[token] = sv

    # build the safe expression string by replacing long tokens
    safe_expr = formula
    # sort by length to avoid partial replacement issues
    for k in sorted(repl_map.keys(), key=lambda x: -len(x)):
        safe_expr = safe_expr.replace(k, repl_map[k])

    # convert SUB(value1, value2) syntax into Python expression
    safe_expr = _replace_sub_calls(safe_expr)

    # At this stage, dfs/stgs names are already tokenized, so global whitespace
    # removal cannot corrupt quoted datafeed/setting names.
    safe_expr = re.sub(r"\s+", "", safe_expr)

    try:
        expr_ast = ast.parse(safe_expr, mode="eval")
        _Validator().visit(expr_ast)
        compiled = compile(expr_ast, "<formula>", mode="eval")
    except Exception:
        # parsing/validation failure almost always means the formula is malformed
        raise ValueError(f"Incorrect formula; safe_expr={safe_expr!r}")

    # evaluate expression for each point in the grid
    for ts in grid:
        line = df_value_map.get(ts, {})

        # if any required df value is missing, skip this timestamp silently
        if any(line.get(name) is None for name in df_names):
            continue

        # prepare variable namespace for eval: map tokens, settings and available funcs
        namespace: dict[str, Any] = {"__builtins__": None, "tres": tres, **runtime_functions}

        # fill same-timestamp datafeed values
        for token, name in df_token_map.items():
            namespace[token] = line.get(name)

        # fill settings tokens
        for token, val in set_map.items():
            namespace[token] = val
        try:
            # eval with restricted globals only (no builtins)
            result = eval(compiled, namespace)
            if use_total:  # if this is a totalizer created internally, then its value should be restricted
                if result + last_value > tot_reset_value:
                    last_value = 0
                result = last_value + result
        except Exception as e:
            add_to_alarm_payload(f"Error while evaluating formula for {df.name}: {e}", None, ts, "w")
        else:
            # store result directly in the provided value map under derived df's name
            if ts not in df_value_map:
                df_value_map[ts] = {}
            df_value_map[ts][df.name] = result
            if result is not None:
                last_value = result

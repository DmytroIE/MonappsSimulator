import ast
import math
from functools import lru_cache
from typing import Any, Callable, Mapping

from classes.datafeed import Datafeed
from common.complex_types import DfValueMap
from utils.ts_utils import create_grid
from app_functions.helpers.utils import formula_functions


ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.IfExp,
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
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Is,
    ast.IsNot,
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


class _Validator(ast.NodeVisitor):
    def generic_visit(self, node):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"Unsafe expression node: {node.__class__.__name__}")
        super().generic_visit(node)


@lru_cache(maxsize=10)
def _get_function_from_bundle(bundle_name: str, function_name: str) -> Callable[..., Any]:
    """Load and cache function callables from formula bundles."""
    bundle = formula_functions.__dict__.get(bundle_name)
    if bundle is None:
        raise ValueError(f"Function bundle '{bundle_name}' does not exist")
    if not isinstance(bundle, Mapping):
        raise ValueError(f"Function bundle '{bundle_name}' has invalid format")

    fn = bundle.get(function_name)
    if fn is None:
        raise ValueError(
            f"Function '{function_name}' does not exist in bundle '{bundle_name}'"
        )
    if not callable(fn):
        raise ValueError(
            f"Function '{function_name}' in bundle '{bundle_name}' is not callable"
        )
    return fn


def _validate_formula_object(formula_obj: Any) -> dict[str, Any]:
    """Validate a formula object and return it in a typed form."""
    if not isinstance(formula_obj, dict):
        raise ValueError("Formula should be an object")

    tokens = formula_obj.get("tokens")
    formula = formula_obj.get("formula")

    if not isinstance(tokens, dict):
        raise ValueError("Formula field 'tokens' should be an object")
    if not isinstance(formula, str) or not formula.strip():
        raise ValueError("Formula field 'formula' should be a non-empty string")

    return formula_obj


def _build_token_maps(
    tokens: Mapping[str, Any],
    settings: Mapping[str, Any],
) -> tuple[
    dict[str, str],
    dict[str, tuple[str, str | None]],
    dict[str, Any],
    dict[str, Callable[..., Any]],
]:
    """
    Build token maps for datafeeds/settings/functions.

    Returns:
    - token_types: token -> type
    - datafeed_tokens: token -> (df_name, fallback_setting_token|None)
    - setting_tokens: token -> concrete value
    - function_tokens: token -> callable
    """
    token_types: dict[str, str] = {}
    datafeed_tokens: dict[str, tuple[str, str | None]] = {}
    setting_tokens: dict[str, Any] = {}
    function_tokens: dict[str, Callable[..., Any]] = {}

    for token_name, token_meta in tokens.items():
        if not isinstance(token_name, str) or not token_name.isidentifier():
            raise ValueError(f"Token '{token_name}' is not a valid identifier")
        if not isinstance(token_meta, dict):
            raise ValueError(f"Token '{token_name}' metadata should be an object")

        token_type = token_meta.get("type")
        if token_type not in {"datafeed", "setting", "function"}:
            raise ValueError(
                f"Token '{token_name}' has invalid type '{token_type}'"
            )

        token_types[token_name] = token_type

    for token_name, token_meta in tokens.items():
        token_type = token_meta["type"]

        if token_type == "datafeed":
            df_name = token_meta.get("name")
            if not isinstance(df_name, str) or not df_name:
                raise ValueError(
                    f"Datafeed token '{token_name}' should have a non-empty 'name'"
                )

            fallback_token = token_meta.get("fallback")
            if fallback_token is not None:
                if not isinstance(fallback_token, str):
                    raise ValueError(
                        f"Datafeed token '{token_name}' fallback should be a token name"
                    )
                if token_types.get(fallback_token) != "setting":
                    raise ValueError(
                        f"Datafeed token '{token_name}' fallback '{fallback_token}' "
                        "should reference a setting token"
                    )

            datafeed_tokens[token_name] = (df_name, fallback_token)

        elif token_type == "setting":
            setting_name = token_meta.get("name")
            if not isinstance(setting_name, str) or not setting_name:
                raise ValueError(
                    f"Setting token '{token_name}' should have a non-empty 'name'"
                )

            if (setting_value := settings.get(setting_name)) is None:
                raise ValueError(
                    f"Setting '{setting_name}' referenced by token '{token_name}' is missing"
                )
            setting_tokens[token_name] = setting_value

        elif token_type == "function":
            function_name = token_meta.get("name")
            bundle_name = token_meta.get("bundle")

            if not isinstance(function_name, str) or not function_name:
                raise ValueError(
                    f"Function token '{token_name}' should have a non-empty 'name'"
                )
            if not isinstance(bundle_name, str) or not bundle_name:
                raise ValueError(
                    f"Function token '{token_name}' should have a non-empty 'bundle'"
                )

            function_tokens[token_name] = _get_function_from_bundle(
                bundle_name, function_name
            )

    return token_types, datafeed_tokens, setting_tokens, function_tokens


def evaluate_formula(
    df: Datafeed,
    df_value_map: DfValueMap,
    settings: Mapping[str, Any],
    start_rts: int,
    end_rts: int,
    last_value: int | float,
) -> None:
    """
    Evaluate a JSON-described formula over (start_rts, end_rts] and write results
    directly into df_value_map under df.name.

    Formula structure expected in df.formula:
    {
      "tokens": {
        "t": {"type": "datafeed", "name": "Temp", "fallback": "t_fb"},
        "t_fb": {"type": "setting", "name": "temp_subst"},
        "calc": {"type": "function", "name": "calc_bdn_amount", "bundle": "steam_water"}
      },
      "formula": "calc(t, ... )"
    }

    Built-in tokens always available in namespace:
    - tr: target datafeed time_resample (df.time_resample)
    - lv: last_value provided by caller

    Runtime behavior:
    - Pre-loop validation may raise ValueError for invalid JSON/token schema,
      missing settings/functions, grid creation failure, or compilation failure.
    - For each timestamp, datafeed tokens are resolved from df_value_map at ts;
      datafeed fallback (if configured) is applied from setting token value.
    - If at least one datafeed token is still None after fallback, the timestamp
      is silently skipped.
    """
    formula_obj = _validate_formula_object(df.formula)
    token_defs = formula_obj["tokens"]
    formula_expr: str = formula_obj["formula"]

    token_types, datafeed_tokens, setting_tokens, function_tokens = _build_token_maps(
        token_defs, settings
    )

    # Formula can contain whitespace/newlines from JSON formatting; AST handles it,
    # but we normalize for predictable debug output.
    safe_expr = "".join(ch for ch in formula_expr if ch.isprintable())

    try:
        expr_ast = ast.parse(safe_expr, mode="eval")
        _Validator().visit(expr_ast)
    except Exception as e:
        raise ValueError(f"Incorrect formula, {e}")

    # Ensure all identifiers used in expression are known tokens or built-ins.
    used_names = {node.id for node in ast.walk(expr_ast) if isinstance(node, ast.Name)}
    allowed_names = set(token_types.keys()) | set(MATH_FUNCTIONS.keys()) | {"tr", "lv"}
    unknown_names = used_names - allowed_names
    if unknown_names:
        raise ValueError(
            "Unknown token(s) in formula: " + ", ".join(sorted(unknown_names))
        )

    compiled = compile(expr_ast, "<formula>", mode="eval")

    grid = create_grid(start_rts + df.time_resample, end_rts, df.time_resample)

    for ts in grid:
        line = df_value_map.get(ts, {})

        namespace: dict[str, Any] = {
            "__builtins__": None,
            "tr": df.time_resample,
            "lv": last_value,
            **MATH_FUNCTIONS,
            **function_tokens,
            **setting_tokens,
        }

        has_missing_data = False
        for token_name, (df_name, fallback_token) in datafeed_tokens.items():
            value = line.get(df_name)
            if value is None and fallback_token is not None:
                value = setting_tokens[fallback_token]
            namespace[token_name] = value
            if value is None:
                has_missing_data = True

        if has_missing_data:
            continue

        result = eval(compiled, namespace)

        if ts not in df_value_map:
            df_value_map[ts] = {}
        df_value_map[ts][df.name] = result

        if result is not None:
            last_value = result

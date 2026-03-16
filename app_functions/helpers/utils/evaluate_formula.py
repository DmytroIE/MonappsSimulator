import ast
import json
import math
from functools import lru_cache
from types import CodeType
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


def _total(tot_value: int | float, value: int | float, reset_value: int | float) -> int | float:
    if tot_value + value > reset_value:
        tot_value = 0
    tot_value += value
    return tot_value


def _diff(current_value: int | float | None, previous_value: int | float | None) -> int | float | None:
    if current_value is None:
        return None
    if previous_value is None:
        return 0
    return current_value - previous_value


INTERNAL_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "sqrt": math.sqrt,
    "pow": math.pow,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "exp": math.exp,
    "log": math.log,
    "total": _total,
    "diff": _diff,
}


class _Validator(ast.NodeVisitor):
    def generic_visit(self, node):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"Unsafe expression node: {node.__class__.__name__}")
        super().generic_visit(node)


class _BuiltinCallTransformer(ast.NodeTransformer):
    """Transforms helper calls for builtin formula functions.

    - diff(token) -> diff(token, __PREV_token)
    - total(value, reset) -> total(lv, value, reset)
    """

    def __init__(self, datafeed_token_names: set[str]):
        super().__init__()
        self._datafeed_token_names = datafeed_token_names
        self.prev_token_map: dict[str, str] = {}

    def visit_Call(self, node: ast.Call):
        self.generic_visit(node)

        if isinstance(node.func, ast.Name):
            if node.func.id == "diff":
                if len(node.args) != 1 or node.keywords:
                    raise ValueError("Function 'diff' expects exactly one positional token argument")

                arg = node.args[0]
                if not isinstance(arg, ast.Name) or arg.id not in self._datafeed_token_names:
                    raise ValueError("Function 'diff' argument should be a datafeed token")

                prev_token = f"__PREV_{arg.id}"
                self.prev_token_map[arg.id] = prev_token
                new_node = ast.Call(
                    func=node.func,
                    args=[arg, ast.Name(id=prev_token, ctx=ast.Load())],
                    keywords=[],
                )
                return ast.copy_location(new_node, node)

            if node.func.id == "total":
                if node.keywords:
                    raise ValueError("Function 'total' does not support keyword arguments")

                if len(node.args) == 2:
                    new_node = ast.Call(
                        func=node.func,
                        args=[ast.Name(id="lv", ctx=ast.Load()), node.args[0], node.args[1]],
                        keywords=[],
                    )
                    return ast.copy_location(new_node, node)

                if len(node.args) != 3:
                    raise ValueError("Function 'total' expects 2 or 3 positional arguments")

        return node


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


def _serialize_formula_object(formula_obj: dict[str, Any]) -> str:
    """Build a canonical JSON key for formula caching."""
    try:
        return json.dumps(formula_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except Exception as e:
        raise ValueError(f"Formula object is not JSON-serializable: {e}")


@lru_cache(maxsize=10)
def _get_compiled_formula_artifacts(formula_key: str) -> tuple[CodeType, tuple[tuple[str, str], ...]]:
    """Parse/transform/validate/compile formula expression and cache the result."""
    try:
        formula_obj = json.loads(formula_key)
    except Exception as e:
        raise ValueError(f"Formula cache key is invalid JSON: {e}")

    formula_obj = _validate_formula_object(formula_obj)
    token_defs = formula_obj["tokens"]
    formula_expr: str = formula_obj["formula"]

    token_types: dict[str, str] = {}
    for token_name, token_meta in token_defs.items():
        if not isinstance(token_name, str) or not token_name.isidentifier():
            raise ValueError(f"Token '{token_name}' is not a valid identifier")
        if not isinstance(token_meta, dict):
            raise ValueError(f"Token '{token_name}' metadata should be an object")

        token_type = token_meta.get("type")
        if token_type not in {"datafeed", "setting", "function"}:
            raise ValueError(f"Token '{token_name}' has invalid type '{token_type}'")
        token_types[token_name] = token_type

    datafeed_token_names = {
        token_name for token_name, token_type in token_types.items() if token_type == "datafeed"
    }

    # Formula can contain whitespace/newlines from formatting; AST handles it,
    # but we normalize for predictable debug output.
    safe_expr = "".join(ch for ch in formula_expr if ch.isprintable())

    try:
        expr_ast = ast.parse(safe_expr, mode="eval")
        builtin_transformer = _BuiltinCallTransformer(datafeed_token_names)
        expr_ast = builtin_transformer.visit(expr_ast)
        expr_ast = ast.fix_missing_locations(expr_ast)
        _Validator().visit(expr_ast)
    except Exception as e:
        raise ValueError(f"Incorrect formula, {e}")

    # Ensure all identifiers used in expression are known tokens or built-ins.
    used_names = {node.id for node in ast.walk(expr_ast) if isinstance(node, ast.Name)}
    allowed_names = (
        set(token_types.keys())
        | set(INTERNAL_FUNCTIONS.keys())
        | {"tr", "lv"}
        | set(builtin_transformer.prev_token_map.values())
    )
    unknown_names = used_names - allowed_names
    if unknown_names:
        raise ValueError(
            "Unknown token(s) in formula: " + ", ".join(sorted(unknown_names))
        )

    compiled = compile(expr_ast, "<formula>", mode="eval")
    prev_token_items = tuple(sorted(builtin_transformer.prev_token_map.items()))
    return compiled, prev_token_items


def get_compiled_formula_cache_info() -> dict[str, int | None]:
    """Return LRU cache stats for compiled formula artifacts."""
    info = _get_compiled_formula_artifacts.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "maxsize": info.maxsize,
        "currsize": info.currsize,
    }


def clear_compiled_formula_cache() -> None:
    """Clear cached compiled formula artifacts."""
    _get_compiled_formula_artifacts.cache_clear()


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
    - datafeed_tokens: token -> (df_name, fallback_setting_name|None)
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
                        f"Datafeed token '{token_name}' fallback should be a setting name"
                    )
                if fallback_token not in settings:
                    raise ValueError(
                        f"Datafeed token '{token_name}' fallback '{fallback_token}' "
                        "should reference an existing setting name"
                    )

            datafeed_tokens[token_name] = (df_name, fallback_token)

        elif token_type == "setting":
            setting_name = token_meta.get("name")
            if not isinstance(setting_name, str) or not setting_name:
                raise ValueError(
                    f"Setting token '{token_name}' should have a non-empty 'name'"
                )

            if setting_name not in settings:
                raise ValueError(
                    f"Setting '{setting_name}' referenced by token '{token_name}' is missing"
                )
            setting_value = settings[setting_name]
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
        Evaluate a tokenized formula object over (start_rts, end_rts] and write
        resulting values into df_value_map under df.name.

        Expected df.formula structure:
        {
            "tokens": {
                "t": {"type": "datafeed", "name": "Temp", "fallback": "temp_subst"},
                "temp_subst": {"type": "setting", "name": "temp_subst"},
                "calc": {"type": "function", "name": "calc_bdn_amount", "bundle": "steam_water"}
            },
            "formula": "total(calc(diff(t), k), reset)"
        }

        Available built-ins in expression namespace:
        - tr: target datafeed time_resample (df.time_resample)
        - lv: caller-provided last_value
        - internal functions: sqrt, pow, sin, cos, tan, exp, log, total, diff

        Builtin call transformations before compilation:
        - diff(token) -> diff(token, __PREV_token)
        - total(value, reset) -> total(lv, value, reset)

        Compilation is cached with LRU(maxsize=10), keyed by canonical JSON of
        the formula object after validation.

        Runtime behavior:
        - Pre-loop validation may raise ValueError (invalid formula/tokens,
            missing settings/functions, unsafe/invalid expression, grid failures).
        - For each timestamp, datafeed token values are loaded from df_value_map;
            if missing, configured datafeed fallback is taken from settings.
        - If any datafeed token is still None after fallback, the timestamp is
            silently skipped.
        - For transformed diff calls, previous raw values are read from
            ts - df.time_resample (without fallback).
    """
    formula_obj = _validate_formula_object(df.formula)
    token_defs = formula_obj["tokens"]

    token_types, datafeed_tokens, setting_tokens, function_tokens = _build_token_maps(
        token_defs, settings
    )

    formula_key = _serialize_formula_object(formula_obj)
    compiled, prev_token_items = _get_compiled_formula_artifacts(formula_key)
    prev_token_map = dict(prev_token_items)

    grid = create_grid(start_rts + df.time_resample, end_rts, df.time_resample)

    for ts in grid:
        line = df_value_map.get(ts, {})

        namespace: dict[str, Any] = {
            "__builtins__": None,
            "tr": df.time_resample,
            "lv": last_value,
            **INTERNAL_FUNCTIONS,
            **function_tokens,
            **setting_tokens,
        }

        has_missing_data = False
        for token_name, (df_name, fallback_token) in datafeed_tokens.items():
            value = line.get(df_name)
            if value is None and fallback_token is not None:
                value = settings[fallback_token]
            namespace[token_name] = value
            if value is None:
                has_missing_data = True

        # Fill transformed diff(...) helper variables with previous raw values
        # (from ts - target_df.time_resample), without fallback application.
        prev_line = df_value_map.get(ts - df.time_resample, {})
        for datafeed_token, prev_token in prev_token_map.items():
            prev_df_name = datafeed_tokens[datafeed_token][0]
            namespace[prev_token] = prev_line.get(prev_df_name)

        if has_missing_data:
            continue

        result = eval(compiled, namespace)

        if ts not in df_value_map:
            df_value_map[ts] = {}
        df_value_map[ts][df.name] = result

        if result is not None:
            last_value = result

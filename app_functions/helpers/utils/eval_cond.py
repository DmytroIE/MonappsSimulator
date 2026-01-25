from typing import Literal, Any

type CondLiteral = Literal[">", "<", ">=", "<=", "==", "!="]


def eval_cond(first: Any, cond: CondLiteral, second: Any) -> bool:
    if cond == "==":
        return first == second
    elif cond == "!=":
        return first != second
    elif cond == ">":
        return first > second
    elif cond == ">=":
        return first >= second
    elif cond == "<":
        return first < second
    elif cond == "<=":
        return first <= second

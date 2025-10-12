from typing import Literal, Any
from widgets.SignalManager import SignalManager
from utils.ts_utils import create_now_ts_ms


def add_to_alarm_log(
    type: Literal["ERROR", "WARNING", "INFO"],
    msg: str,
    ts: int | None = None,
    instance: Any = "Django",
    status: str = "",
):

    if ts is None:
        ts = create_now_ts_ms()

    if not status:
        status = "IN"

    SignalManager.add_to_alarm_log.emit(
        {"ts": ts, "msg": msg, "type": type, "status": status.upper(), "instance": str(instance)}
    )

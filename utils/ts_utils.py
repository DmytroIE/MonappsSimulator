from datetime import datetime, timezone
from typing import List


def create_ts_ms_from_iso_str(iso_string: str) -> int:
    """
    Takes an ISO-formatted string and converts it into int.
    """
    dt = datetime.fromisoformat(iso_string)
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        dt = dt.replace(tzinfo=timezone.utc)

    timestamp_ms = int(dt.timestamp() * 1000)
    return timestamp_ms


def create_ts_ms_from_dt_obj(dt: datetime) -> int:
    """
    Takes an aware datetime object and converts it into int.
    """

    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("Input datetime object is not aware")

    timestamp_ms = int(dt.timestamp() * 1000)
    return timestamp_ms


def ceil_timestamp(dt: int, interval: int) -> int:
    k, modulo = divmod(dt, interval)
    if modulo > 0:
        k += 1
    return k * interval


def floor_timestamp(dt: int, interval: int) -> int:
    k, _ = divmod(dt, interval)
    return k * interval


def create_grid(start_rts: int, end_rts: int, t_resample: int) -> List[int]:
    if end_rts < start_rts:
        raise ValueError("Input parameters for grid are not valid, end_rts < start_rts")

    if (end_rts - start_rts) % t_resample != 0:
        raise ValueError("Input parameters for grid are not valid, (end_rts - start_rts) % t_resample != 0")

    grid = [start_rts]  # as minimum, if 'start_rts' == 'end_rts', this array with a single element will be returned
    t = start_rts
    while t < end_rts:
        t += t_resample
        grid.append(t)

    return grid


def create_dt_from_ts_ms(ts: int) -> datetime:
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)


def create_now_ts_ms() -> int:
    return create_ts_ms_from_dt_obj(datetime.now(tz=timezone.utc))


def get_floored_now_ts(time_resample: int) -> int:
    return floor_timestamp(create_now_ts_ms(), time_resample)

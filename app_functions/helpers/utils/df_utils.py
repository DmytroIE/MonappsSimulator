import re

from classes.datafeed import Datafeed
from classes.dfreading import DfReading


def get_datafeeds_of_series(df_map: dict[str, Datafeed], series_name: str) -> list[Datafeed]:
    dfs: list[Datafeed] = [df for df in df_map.values() if df.name.startswith(series_name)]
    return dfs


def get_last_df_reading(df: Datafeed) -> DfReading | None:
    last_dfr = DfReading.objects.filter(datafeed__id=df.pk).order_by("time").last()
    if last_dfr is None:
        return None
    if df.last_reading_ts != last_dfr.time:
        raise ValueError(f"Datafeed '{df.name}' last_reading_ts is different from the last reading in db")
    return last_dfr


def get_df_readings(df: Datafeed, start_ts: int, end_ts: int) -> list[DfReading]:
    return list(DfReading.objects.filter(datafeed__id=df.pk, time__gte=start_ts, time__lte=end_ts))


def get_df_name_part(df: Datafeed, template: str) -> str:
    """
    Returns the part of the df name after the template. May be useful when
    it's necessary to extract "Boilerhouse" from "Water total Boilerhouse" just
    knowing "Water total".

    :param df: Datafeed to be processed
    :type df: Datafeed
    :param template: The "constant" part of the df name
    :type template: str
    :return: The volatile part
    :rtype: str | None
    """
    pattern = template + r"\s+(.*)"
    match = re.search(pattern, df.name.strip())
    if match is None:
        return ""
    return match.group(1)

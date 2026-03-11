import re
from typing import Mapping

from classes.datafeed import Datafeed
from classes.dfreading import DfReading


def get_df_map_of_series(df_map: Mapping[str, Datafeed], series_name: str) -> Mapping[str, Datafeed]:
    ser_df_map: dict[str, Datafeed] = {df.name: df for df in df_map.values() if df.name.startswith(series_name)}
    return ser_df_map


def get_last_df_reading(df: Datafeed) -> DfReading | None:
    if df.last_reading_ts is None:
        return None
    return DfReading.objects.filter(datafeed__id=df.pk, time=df.last_reading_ts).first()


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

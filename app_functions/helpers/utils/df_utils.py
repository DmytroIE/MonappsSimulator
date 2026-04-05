import re
from collections.abc import Iterable
from typing import Mapping

from classes.datafeed import Datafeed
from classes.dfreading import DfReading

from common.complex_types import DfValueMap


def get_df_value_map(datafeeds: Iterable[Datafeed], start_rts: int, end_rts: int) -> DfValueMap:
    """
    Builds a map of datafeed values for the interval (start_rts, end_rts].
    The map is indexed by timestamps and df names:
    {
        timestamp1: {df_name1: value, df_name2: value, ...},
        timestamp2: {df_name1: value, df_name2: value, ...},
        ...}
    and sorted by timestamps. Only readings of datafeeds from the 'datafeeds' list are included.
    """

    df_value_map: DfValueMap = {}

    for df in datafeeds:
        df_readings = list(
            DfReading.objects.filter(datafeed__id=df.pk, time__gt=start_rts, time__lte=end_rts).order_by("time")
        )

        if len(df_readings) == 0:
            continue

        for dfr in df_readings:
            if dfr.time not in df_value_map:
                df_value_map[dfr.time] = {}
            df_value_map[dfr.time][df.name] = dfr.value

    df_value_map = dict(sorted(df_value_map.items()))

    return df_value_map


def update_df_value_map(df_value_map: DfValueMap, datafeeds: Iterable[Datafeed], start_rts: int, end_rts: int) -> None:
    """Updates the 'df_value_map' with readings of datafeeds from the 'datafeeds' list
    for the interval (start_rts, end_rts]. The map is indexed by timestamps and df names:
    {
        timestamp1: {df_name1: value, df_name2: value, ...},
        timestamp2: {df_name1: value, df_name2: value, ...},
        ...
    }
    and sorted by timestamps. Only readings of datafeeds from the 'datafeeds' list are included."""
    for df in datafeeds:
        df_readings = list(
            DfReading.objects.filter(datafeed__id=df.pk, time__gt=start_rts, time__lte=end_rts).order_by("time")
        )

        if len(df_readings) == 0:
            continue

        for dfr in df_readings:
            if dfr.time not in df_value_map:
                df_value_map[dfr.time] = {}
            df_value_map[dfr.time][df.name] = dfr.value

    # ensure the map is sorted after the update
    df_value_map = dict(sorted(df_value_map.items()))


def add_readings_to_df_value_map(df_value_map: DfValueMap, readings: Iterable[DfReading]) -> None:
    """Adds readings of a datafeed to the 'df_value_map'"""
    for dfr in readings:
        if dfr.time not in df_value_map:
            df_value_map[dfr.time] = {}
        datafeed = dfr.datafeed
        df_value_map[dfr.time][datafeed.name] = dfr.value


def add_value_to_df_value_map(df_value_map: DfValueMap, df_name: str, ts: int, value: float | int) -> None:
    """Adds a value of a datafeed to the 'df_value_map' for a given timestamp"""
    if ts not in df_value_map:
        df_value_map[ts] = {}
    df_value_map[ts][df_name] = value


def merge_df_value_maps(df_value_map1: DfValueMap, df_value_map2: DfValueMap) -> DfValueMap:
    """Merges two df value maps into one. If there are readings with the same timestamp in both maps,
    the values for these readings will be merged. The resulting map is sorted by timestamps."""
    merged_map = dict(df_value_map1)  # start with the first map
    for ts, values in df_value_map2.items():
        if ts not in merged_map:
            merged_map[ts] = values
        else:
            merged_map[ts].update(values)  # merge values for the same timestamp
    return dict(sorted(merged_map.items()))


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

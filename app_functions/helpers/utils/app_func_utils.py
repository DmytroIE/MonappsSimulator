from collections.abc import Iterable
from collections import ChainMap

from common.constants import settings

from classes.application import Application
from classes.datafeed import Datafeed
from classes.dfreading import DfReading
from common.complex_types import DfValueMap
from utils.ts_utils import floor_timestamp


def get_end_rts(
    nat_dfs: Iterable[Datafeed], app_time_resample: int, start_rts: int, num_der_dfs: int
) -> tuple[int, bool]:

    df_last_rtss = []

    for df in nat_dfs:

        last_dfr_rts_to_use = df.ts_to_start_with
        # df.ts_to_start_with is not always the ts of the last dfr,
        # sometimes (after restoration) it can be greater

        if last_dfr_rts_to_use is None or last_dfr_rts_to_use <= start_rts:
            df_last_rtss.append(start_rts)
        else:
            df_last_rtss.append(last_dfr_rts_to_use)

    if len(df_last_rtss) == 0:
        smallest_rts_in_all_last_dfrs = start_rts
    else:
        smallest_rts_in_all_last_dfrs = min(df_last_rtss)
    num_app_time_resample_periods = (smallest_rts_in_all_last_dfrs - start_rts) // app_time_resample
    if num_app_time_resample_periods == 0:
        # If there are datafeeds with 'time_resample' smaller than the 'app_time_resample',
        # then it is possible that there are not enough dfrs to cover even one app 'time_resample' interval.
        # In this case, there's nothing to do and the function returns the 'start_rts'.
        return start_rts, False

    num_dfrs_per_one_app_time_resample = num_der_dfs
    for df in nat_dfs:
        num_dfrs_per_one_app_time_resample += app_time_resample // df.time_resample

    num_app_time_resample_periods_corrected = (
        settings.NUM_MAX_DFREADINGS_TO_PROCESS // num_dfrs_per_one_app_time_resample
    )
    num_app_time_resample_periods_corrected = max(1, num_app_time_resample_periods_corrected)  # protection against 0

    end_rts_by_max_num_dfrs = start_rts + app_time_resample * num_app_time_resample_periods_corrected
    floored_smallest_rts_in_all_last_dfrs = floor_timestamp(smallest_rts_in_all_last_dfrs, app_time_resample)
    end_rts = min(floored_smallest_rts_in_all_last_dfrs, end_rts_by_max_num_dfrs)

    is_catching_up = floored_smallest_rts_in_all_last_dfrs > end_rts

    return end_rts, is_catching_up


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


def get_df_maps_from_app(app: Application) -> ChainMap[str, Datafeed]:
    """Builds a map of datafeeds (both native and derived) used in the app, indexed by their names."""
    native_df_qs = app.get_native_df_qs()
    native_df_map = {df.name: df for df in native_df_qs}
    derived_df_qs = app.get_derived_df_qs()
    derived_df_map = {df.name: df for df in derived_df_qs}
    df_map = ChainMap(native_df_map, derived_df_map)
    return df_map

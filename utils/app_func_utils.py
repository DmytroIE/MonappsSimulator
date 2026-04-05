from collections import ChainMap
from collections.abc import Iterable

from classes.application import Application
from classes.datafeed import Datafeed

from common.constants import settings
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


def get_df_maps_from_app(app: Application) -> ChainMap[str, Datafeed]:
    """Builds a map of datafeeds (both native and derived) used in the app, indexed by their names."""
    native_df_qs = app.get_native_df_qs()
    native_df_map = {df.name: df for df in native_df_qs}
    derived_df_qs = app.get_derived_df_qs()
    derived_df_map = {df.name: df for df in derived_df_qs}
    df_map = ChainMap(native_df_map, derived_df_map)
    return df_map

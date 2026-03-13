import logging
from functools import partial

from classes.application import Application
from classes.datafeed import Datafeed
from classes.dfreading import DfReading
from common.complex_types import DerivedDfReadingMap, UpdateMap
from app_functions.helpers.utils.app_func_utils import get_end_rts, get_df_value_map, get_df_maps_from_app
from app_functions.helpers.utils.df_utils import get_last_df_reading
from utils.ts_utils import create_grid
from utils.alarm_utils import add_to_alarm_payload
from app_functions.helpers.utils.app_func_settings_bundle import AppFuncSettingsBundle
from app_functions.helpers.utils.evaluate_formula import evaluate_formula

from .schemas import AppFuncSettingsModel as AfsModel

logger = logging.getLogger("#mon_VER1_1_0_0")


def function(app: Application, derived_df_reading_map: DerivedDfReadingMap, update_map: UpdateMap) -> None:
    """
    This function is for pure monitoring. It doesn't do any calculation and generate
    insigts, it just moves the cursor in order to evaluate the app health.
    """

    logger.info("App function starts executing...")

    # get datafeeds
    df_map = get_df_maps_from_app(app)
    [native_df_map, derived_df_map] = df_map.maps

    for df in derived_df_map.values():
        derived_df_reading_map[df.name] = {"df": df, "new_df_readings": []}

    # prepare other variables
    alarm_payload = update_map.get("alarm_payload")
    if alarm_payload is None:
        alarm_payload = {}
        update_map["alarm_payload"] = alarm_payload

    # get end time
    start_rts = app.cursor_ts
    end_rts, is_catching_up = get_end_rts(native_df_map.values(), app.time_resample, start_rts, len(derived_df_map))

    if end_rts <= start_rts:  # not all datafeed have readings with ts > cursor_ts
        return

    settings_bundle = AppFuncSettingsBundle[AfsModel](app.settings, AfsModel)

    df_value_map = get_df_value_map(native_df_map.values(), start_rts, end_rts)

    # prepare a map for datafeeds with formulas
    df_with_formula_map = {}
    for df in derived_df_map.values():
        if df.formula == "":
            continue

        df_with_formula_map[df.name] = {"df": df, "last_value": None}
        if df.data_type.is_totalizer:
            last_dfr = get_last_df_reading(df)
            if last_dfr is not None:
                df_with_formula_map[df.name]["last_value"] = last_dfr.value

    # creating the grid
    grid = create_grid(start_rts + app.time_resample, end_rts, app.time_resample)

    # moving along the grid and calculate df readings for datafeeds with formulas
    for rts in grid:
        one_step_alarm_payload = {rts: {}}

        app_settings = settings_bundle.get_settings(rts)

        add_to_alarm_payload_part = partial(add_to_alarm_payload, one_step_alarm_payload)

        for df_with_formula_row in df_with_formula_map.values():
            df: Datafeed = df_with_formula_row["df"]
            last_value = df_with_formula_row["last_value"]
            evaluate_formula(
                df,
                df_value_map,
                app_settings.model_dump(),
                app.func_bundles,
                rts - app.time_resample,
                rts,
                add_to_alarm_payload_part,
                last_value=last_value,
                tot_reset_value=app_settings.int_tot_reset_value,
            )

        # update at the end of the cycle

        # create df readings for datafeeds with formulas within the current bin
        for df_with_formula_row in df_with_formula_map.values():
            df: Datafeed = df_with_formula_row["df"]
            timestamps = sorted(df_value_map.keys())
            for ts in timestamps:
                if rts - app.time_resample < ts <= rts:
                    row = df_value_map[ts]
                    if df.name in row:
                        value = row[df.name]
                        dfr = DfReading(time=ts, value=value, datafeed=df, restored=False)
                        derived_df_reading_map[df.name]["new_df_readings"].append(dfr)
                        if df.data_type.is_totalizer:
                            df_with_formula_row["last_value"] = value

        # update app output
        update_map["cursor_ts"] = rts
        update_map["is_catching_up"] = is_catching_up

        for t, p in one_step_alarm_payload.items():
            if alarm_payload.get(t) is None:
                alarm_payload[t] = p
            else:
                alarm_payload[t].update(p)

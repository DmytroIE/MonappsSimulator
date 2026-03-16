import logging
from functools import partial
from classes.application import Application
from classes.datafeed import Datafeed
from classes.dfreading import DfReading
from utils.ts_utils import create_grid
from common.complex_types import DerivedDfReadingMap, UpdateMap
from common.constants import STATUS_FIELD_NAME, CURR_STATE_FIELD_NAME, CurrStateTypes
from utils.alarm_utils import add_to_alarm_payload

from app_functions.helpers.utils.app_func_utils import get_end_rts, get_df_value_map, get_df_maps_from_app
from app_functions.helpers.utils.occ_cluster_list import OccurrenceClusterList
from app_functions.helpers.automatas.status_type1 import (
    Automata as StAutomata,
)
from app_functions.helpers.utils.totalaizer_utils import (
    straighten_tot_readings,
    get_boundaries_of_overlapping_tot_readings,
)
from app_functions.helpers.utils.app_func_settings_bundle import AppFuncSettingsBundle
from app_functions.helpers.utils.df_utils import get_df_map_of_series, get_last_df_reading
from app_functions.helpers.utils.evaluate_formula import evaluate_formula, get_compiled_formula_cache_info

from .schemas import AppState, AppFuncSettingsModel as AfsModel

logger = logging.getLogger("#ccr_SMW_TOT_1_0_0")


def function(app: Application, derived_df_reading_map: DerivedDfReadingMap, update_map: UpdateMap) -> None:

    logger.info("App function starts executing...")

    # get datafeeds
    df_map = get_df_maps_from_app(app)
    [native_df_map, derived_df_map] = df_map.maps
    steam_tot_df_map = get_df_map_of_series(df_map, "Steam total")
    mu_water_tot_df_map = get_df_map_of_series(df_map, "Make-up water total")
    lost_water_tot_df_map = get_df_map_of_series(df_map, "Lost water total")
    crr_df = derived_df_map["Cond return rate"]
    curr_state_df = derived_df_map[CURR_STATE_FIELD_NAME]
    status_df = derived_df_map[STATUS_FIELD_NAME]

    for df in derived_df_map.values():
        derived_df_reading_map[df.name] = {"df": df, "new_df_readings": []}

    # prepare other variables
    alarm_payload = update_map.get("alarm_payload")
    if alarm_payload is None:
        alarm_payload = {}
        update_map["alarm_payload"] = alarm_payload

    # at least one steam totalizer and one water totalizer df should exist
    # if len(steam_tot_df_map) == 0 or len(mu_water_tot_df_map) == 0:
    #     add_to_alarm_payload(alarm_payload, "No steam or water totalizer", {}, app.cursor_ts, "w")
    #     update_map["health"] = HealthGrades.WARNING
    #     return

    # get end time
    start_rts = app.cursor_ts
    end_rts, is_catching_up = get_end_rts(native_df_map.values(), app.time_resample, start_rts, len(derived_df_map))

    if end_rts <= start_rts:  # not all datafeed have readings with ts > cursor_ts
        return

    # getting app settings and state
    settings_bundle = AppFuncSettingsBundle[AfsModel](app.settings, AfsModel)  # validation and default values
    app_state = AppState(**app.state)

    # prepare some variables for the status automata
    st_automata_int_state = app_state.st_automata_int_state
    all_occs = OccurrenceClusterList(app_state.all_occs)

    # prepare a map for datafeeds with formulas
    df_with_formula_map = {}
    for df in derived_df_map.values():
        if df.formula.get("formula") is None:
            continue

        df_with_formula_map[df.name] = {"df": df, "last_value": 0}
        if df.data_type.is_totalizer:
            last_dfr = get_last_df_reading(df)
            if last_dfr is not None:
                df_with_formula_map[df.name]["last_value"] = last_dfr.value

    # Getting all native df values
    # and values for derived dfs with formulas within the whole period to optimize the performance.
    # The derived df values will be only from 'start_rts + app.time_resample - window_length' to 'start_rts'
    # and new values will be created while moving along the grid
    app_settings = settings_bundle.get_settings(start_rts)
    window_length = int(app_settings.window_length_coef * app.time_resample)
    all_dfs_to_get_values_for = list(native_df_map.values()) + [row["df"] for row in df_with_formula_map.values()]
    df_value_map = get_df_value_map(all_dfs_to_get_values_for, start_rts + app.time_resample - window_length, end_rts)

    # creating the grid
    grid = create_grid(start_rts + app.time_resample, end_rts, app.time_resample)

    # moving along the grid and run the main logic of the app for each point
    for rts in grid:
        one_step_alarm_payload = {rts: {}}
        crr = None
        curr_state = None
        status = None

        # settings are the same within the 'app.time_resample' interval
        app_settings = settings_bundle.get_settings(rts)

        add_to_alarm_payload_part = partial(add_to_alarm_payload, one_step_alarm_payload)

        # create values for derived datafeeds with formulas for the current bin
        # all derived readings should have timestamps > 'update_map["cursor_ts"]'

        for df_with_formula_row in df_with_formula_map.values():
            df: Datafeed = df_with_formula_row["df"]
            last_value = df_with_formula_row["last_value"]
            evaluate_formula(
                df,
                df_value_map,
                app_settings.model_dump(),
                rts - app.time_resample,
                rts,
                last_value
            )

        # create a status automata
        st_automata = StAutomata(
            st_automata_int_state,
            add_to_alarm_payload_part,
            app_settings.undef_cid,
            app_settings.ok_from_undef_cid,
            app_settings.ok_from_warn_cid,
            app_settings.warn_cid,
        )

        # creating a window df_value_map for the current timestamp
        window_length = int(app_settings.window_length_coef * app.time_resample)
        # copy is needed as the 'straighten_tot_readings' function modifies the df_value_map in place
        window_df_value_map = {ts: vals.copy() for ts, vals in df_value_map.items() if rts - window_length < ts <= rts}

        # then it is necessary to put the readings in order before further processing
        all_totalizers = [*steam_tot_df_map.values(), *mu_water_tot_df_map.values(), *lost_water_tot_df_map.values()]
        for df in all_totalizers:
            straighten_tot_readings(window_df_value_map, df.name)

        result = get_boundaries_of_overlapping_tot_readings(
            window_df_value_map,
            all_totalizers,
            margin_ms=app_settings.overlap_margin,
        )

        if result is None:  # no overlap
            add_to_alarm_payload(one_step_alarm_payload, "No overlapping readings", None, rts, "w")
            curr_state = CurrStateTypes.UNDEFINED
        else:
            left_boundary_ts, right_boundary_ts, tot_df_boundary_value_map = result
            min_window_length = (
                min(app_settings.min_window_length_coef, app_settings.window_length_coef) * app.time_resample
            )  # protection from 'min_window_length_coef' being greater than 'window_length_coef'
            if right_boundary_ts - left_boundary_ts < min_window_length:
                add_to_alarm_payload(one_step_alarm_payload, "Min window length not met", None, rts, "w")
                curr_state = CurrStateTypes.UNDEFINED
            else:
                steam_generated = 0
                for df in steam_tot_df_map.values():
                    steam_generated += (
                        tot_df_boundary_value_map[df.name]["right_val"] - tot_df_boundary_value_map[df.name]["left_val"]
                    )

                if steam_generated < app_settings.min_steam_gen_value:
                    add_to_alarm_payload(one_step_alarm_payload, "No steam was generated over the period", None, rts, "i")
                    curr_state = CurrStateTypes.UNDEFINED
                else:
                    # calculate amount of water losses
                    water_lost = 0
                    for df in lost_water_tot_df_map.values():
                        water_lost += (
                            tot_df_boundary_value_map[df.name]["right_val"]
                            - tot_df_boundary_value_map[df.name]["left_val"]
                        )

                    # calculate the amount of water consumed
                    mu_water_consumed = 0
                    for df in mu_water_tot_df_map.values():
                        mu_water_consumed += (
                            tot_df_boundary_value_map[df.name]["right_val"]
                            - tot_df_boundary_value_map[df.name]["left_val"]
                        )

                    # calculate condensate return rate
                    water_diff = mu_water_consumed - water_lost
                    if water_diff < 0:
                        # protection from wrong readings when water losses are greater than make-up water consumption
                        add_to_alarm_payload(
                            one_step_alarm_payload, "Water losses are greater than make-up water consumption", None, rts, "w"
                        )
                        water_diff = 0
                    if water_diff > steam_generated:
                        # protection from wrong readings when water difference is greater than steam generated
                        add_to_alarm_payload(
                            one_step_alarm_payload, "Water difference is greater than steam generated", None, rts, "w"
                        )
                        water_diff = steam_generated
                    crr = (steam_generated - water_diff) / steam_generated * 100.0
                    logger.debug(f"----------> CRR = {crr}")
                    if crr < app_settings.crr_warning_threshold:
                        curr_state = CurrStateTypes.WARNING
                        add_to_alarm_payload(one_step_alarm_payload, "Condensate return rate is below threshold", None, rts, "w")
                    else:
                        curr_state = CurrStateTypes.OK

        # update interval maps
        all_occs_updated = all_occs.create_copy_for_appending()
        all_occs_updated.append_occurrence(curr_state.value)  # NOTE: 'value' to serialize JSON

        # evaluate status
        # execute ST finite automata
        st_automata.execute(all_occs_updated)
        status = st_automata.get_status()

        # update at the end of the cycle

        # create df readings from values only if this cycle iteration was successful
        # so that last derived readings are always synced with 'cursor_ts' (no readings behind 'cursor_ts')
        # also finding the last values for totalizer-type datafeeds
        if crr is not None:
            crr_dfr = DfReading(time=rts, value=crr, datafeed=crr_df, restored=False)
            derived_df_reading_map[crr_df.name]["new_df_readings"].append(crr_dfr)
        if curr_state is not None:
            cs_dfr = DfReading(time=rts, value=curr_state, datafeed=curr_state_df, restored=False)
            derived_df_reading_map[CURR_STATE_FIELD_NAME]["new_df_readings"].append(cs_dfr)
        if status is not None:
            st_dfr = DfReading(time=rts, value=status, datafeed=status_df, restored=False)
            derived_df_reading_map[STATUS_FIELD_NAME]["new_df_readings"].append(st_dfr)
        # create df readings for datafeeds with formulas within the current bin
        for df_with_formula_row in df_with_formula_map.values():
            df: Datafeed = df_with_formula_row["df"]
            timestamps = sorted(df_value_map.keys())
            for ts in timestamps:
                if rts - app.time_resample < ts <= rts:  # only readings within the current bin
                    row = df_value_map[ts]
                    if df.name in row:
                        value = row[df.name]
                        dfr = DfReading(time=ts, value=value, datafeed=df, restored=False)
                        derived_df_reading_map[df.name]["new_df_readings"].append(dfr)
                        if df.data_type.is_totalizer:
                            df_with_formula_row["last_value"] = value
                        # print(f"Created tot {value} at time {create_dt_from_ts_ms(ts)} - {ts}")

        # get the internal state to use it in the next iteration
        st_automata_int_state = st_automata.get_internal_state()
        all_occs = all_occs_updated  # update the occurrence cluster list

        # update app output
        update_map["cursor_ts"] = rts
        update_map["is_catching_up"] = is_catching_up

        updated_state = {
            "st_automata_int_state": st_automata_int_state.model_dump() if st_automata_int_state is not None else None,
            "all_occs": all_occs,
        }

        update_map["state"] = updated_state

        for t, p in one_step_alarm_payload.items():
            if alarm_payload.get(t) is None:
                alarm_payload[t] = p
            else:
                alarm_payload[t].update(p)

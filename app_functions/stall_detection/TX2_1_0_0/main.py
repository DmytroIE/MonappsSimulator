import logging
from functools import partial
from classes.application import Application
from classes.dfreading import DfReading
from utils.ts_utils import create_grid
from common.complex_types import DerivedDfReadingMap, UpdateMap
from common.constants import STATUS_FIELD_NAME, CURR_STATE_FIELD_NAME
from app_functions.helpers.utils.app_func_utils import get_end_rts, get_df_value_map, get_df_maps_from_app
from utils.alarm_utils import add_to_alarm_payload

from app_functions.helpers.utils.occ_cluster_list import OccurrenceClusterList
from app_functions.helpers.automatas.curr_state_type1 import Automata as CsAutomata
from app_functions.helpers.automatas.status_type1 import Automata as StAutomata
from app_functions.helpers.utils.app_func_settings_bundle import AppFuncSettingsBundle

from .schemas import AppState, AppFuncSettingsModel as AfsModel

logger = logging.getLogger("#stall_TX2_1_0_0")


def function(app: Application, derived_df_reading_map: DerivedDfReadingMap, update_map: UpdateMap) -> None:

    logger.info("App function starts executing...")

    # get datafeeds
    df_map = get_df_maps_from_app(app)
    [native_df_map, derived_df_map] = df_map.maps
    temp_in_df = df_map["Temp in"]
    temp_out_df = df_map["Temp out"]
    status_df = derived_df_map[STATUS_FIELD_NAME]
    curr_state_df = derived_df_map[CURR_STATE_FIELD_NAME]

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

    # get app settings and state
    settings_bundle = AppFuncSettingsBundle[AfsModel](app.settings, AfsModel)  # validation and default values
    app_state = AppState(**app.state)

    # prepare some variables for automatas
    cs_automata_int_state = app_state.cs_automata_int_state
    st_automata_int_state = app_state.st_automata_int_state
    all_occs = OccurrenceClusterList(app_state.all_occs)

    # get new df values as a map
    df_value_map = get_df_value_map(native_df_map.values(), start_rts, end_rts)

    # create grid
    grid = create_grid(start_rts + app.time_resample, end_rts, app.time_resample)

    # moving along the grid
    for rts in grid:
        one_step_alarm_payload = {rts: {}}
        curr_state = None
        status = None

        app_settings = settings_bundle.get_settings(rts)

        add_to_alarm_payload_part = partial(add_to_alarm_payload, one_step_alarm_payload)

        # create the current state automata
        cs_automata = CsAutomata(
            cs_automata_int_state,
            add_to_alarm_payload_part,
            "Data is invalid",
            "Stall detected",
            count_thres=app_settings.cs_delay_trans_counts,
        )
        # create the status automata
        st_automata = StAutomata(
            st_automata_int_state,
            add_to_alarm_payload_part,
            app_settings.undef_cid,
            app_settings.ok_from_undef_cid,
            app_settings.ok_from_warn_cid,
            app_settings.warn_cid,
        )

        # evaluate current state
        line = df_value_map.get(rts, None)
        temp_in = None
        temp_out = None
        if line is not None:
            temp_in = line.get(temp_in_df.name, None)
            temp_out = line.get(temp_out_df.name, None)

        cs_err_flag = temp_in is None or temp_out is None or temp_out - temp_in > app_settings.temp_diff_error_threshold
        cs_off_flag = not cs_err_flag and temp_in <= app_settings.temp_in_threshold
        cs_ok_flag = not cs_err_flag and not cs_off_flag and temp_in - temp_out <= app_settings.delta_temp
        cs_warn_flag = not cs_err_flag and not cs_off_flag and temp_in - temp_out > app_settings.delta_temp

        # execute current finite automata
        cs_automata.execute(rts, cs_err_flag, cs_off_flag, cs_ok_flag, cs_warn_flag)
        curr_state = cs_automata.get_curr_state()

        # update interval maps
        all_occs_updated = all_occs.create_copy_for_appending()
        all_occs_updated.append_occurrence(curr_state.value)

        # evaluate status
        # execute ST finite automata
        st_automata.execute(all_occs_updated)
        status = st_automata.get_status()

        # update at the end of the cycle
        if curr_state is not None:
            cs_dfr = DfReading(time=rts, value=curr_state, datafeed=curr_state_df, restored=False)
            derived_df_reading_map[CURR_STATE_FIELD_NAME]["new_df_readings"].append(cs_dfr)

        if status is not None:
            st_dfr = DfReading(time=rts, value=status, datafeed=status_df, restored=False)
            derived_df_reading_map[STATUS_FIELD_NAME]["new_df_readings"].append(st_dfr)

        cs_automata_int_state = cs_automata.get_internal_state()
        st_automata_int_state = st_automata.get_internal_state()
        all_occs = all_occs_updated

        # update app output
        update_map["cursor_ts"] = rts
        update_map["is_catching_up"] = is_catching_up

        update_map["health"] = cs_automata.get_health_from_app()

        updated_state = {
            "cs_automata_int_state": cs_automata_int_state.model_dump() if cs_automata_int_state is not None else None,
            "st_automata_int_state": st_automata_int_state.model_dump() if st_automata_int_state is not None else None,
            "all_occs": all_occs,
        }

        update_map["state"] = updated_state

        for t, p in one_step_alarm_payload.items():
            if alarm_payload.get(t) is None:
                alarm_payload[t] = p
            else:
                alarm_payload[t].update(p)

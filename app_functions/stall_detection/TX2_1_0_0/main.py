import logging
from functools import partial
from classes.application import Application
from classes.datafeed import Datafeed
from classes.dfreading import DfReading
from utils.ts_utils import create_grid
from common.complex_types import AppFuncReturn, DerivedDfReadingMap, UpdateMap
from common.constants import STATUS_FIELD_NAME, CURR_STATE_FIELD_NAME
from utils.app_func_utils import get_end_rts, get_df_value_map
from utils.alarm_utils import add_to_alarm_payload

from app_functions.helpers.utils.occ_cluster_list import OccurrenceClusterList
from app_functions.helpers.automatas.curr_state_type1 import Automata as CsAutomata
from app_functions.helpers.automatas.status_type1 import Automata as StAutomata

from .schemas import AppState, AppFuncSettings

logger = logging.getLogger("#stall_TX2_1_0_0")


def function(
    app: Application, native_df_map: dict[str, Datafeed], derived_df_map: dict[str, Datafeed]
) -> AppFuncReturn:

    logger.info("'stall_detection_TX2_1_0_0' starts executing...")

    # get datafeeds
    temp_in_df = native_df_map["Temp in"]
    temp_out_df = native_df_map["Temp out"]
    status_df = derived_df_map[STATUS_FIELD_NAME]
    curr_state_df = derived_df_map[CURR_STATE_FIELD_NAME]

    # prepare other variables
    update_map: UpdateMap = {}
    alarm_payload = {}  # {1734567890123: {"e": {"Wrong data":{}, "Something else": {"st": "in"}}, "w": {...}}, ...}

    derived_df_reading_map: DerivedDfReadingMap = {
        STATUS_FIELD_NAME: {"df": status_df, "new_df_readings": []},
        CURR_STATE_FIELD_NAME: {"df": curr_state_df, "new_df_readings": []},
    }

    # get end time
    start_rts = app.cursor_ts
    num_df_to_process = 4  # 4 is because we use 2 temperature datafeeds + curr_state datafeed + status datafeed
    end_rts, is_catching_up = get_end_rts(native_df_map.values(), app.time_resample, start_rts, num_df_to_process)

    if end_rts > start_rts:  # all datafeed have readings with ts > cursor_ts

        # -1- get app settings
        settings = AppFuncSettings(**app.settings)  # validation and default values
        app_state = AppState(**app.state)
        # -2- Create automatas
        add_to_alarm_payload_part = partial(add_to_alarm_payload, alarm_payload)

        # -2-1- create the current state automata

        cs_automata_int_state = app_state.cs_automata_int_state
        cs_automata = CsAutomata(
            cs_automata_int_state,
            add_to_alarm_payload_part,
            "Data is invalid",
            "Stall detected",
            count_thres=settings.cs_delay_trans_counts,
        )
        # -2-2- create the status automata
        st_automata_int_state = app_state.st_automata_int_state
        st_automata = StAutomata(
            st_automata_int_state,
            add_to_alarm_payload_part,
            settings.undef_cid,
            settings.ok_from_undef_cid,
            settings.ok_from_warn_cid,
            settings.warn_cid,
        )

        all_occs = OccurrenceClusterList(app_state.all_occs)

        # -3- get new df values as a map
        df_value_map = get_df_value_map(native_df_map.values(), start_rts, end_rts)

        # -5- create grid
        grid = create_grid(start_rts + app.time_resample, end_rts, app.time_resample)

        # -6- moving along the grid
        for rts in grid:
            alarm_payload[rts] = {}  # NOTE: this is very important, add at least an empty dict for each rts

            # -6-1- evaluate current state
            line = df_value_map.get(rts, None)
            temp_in = None
            temp_out = None
            if line is not None:
                temp_in = line.get(temp_in_df.name, None)
                temp_out = line.get(temp_out_df.name, None)

            cs_err_flag = temp_in is None or temp_out is None or temp_out - temp_in > settings.temp_diff_error_threshold
            cs_off_flag = not cs_err_flag and temp_in <= settings.temp_in_threshold
            cs_ok_flag = not cs_err_flag and temp_in - temp_out <= settings.delta_temp
            cs_warn_flag = not cs_err_flag and temp_in - temp_out > settings.delta_temp

            # execute CS finite automata
            cs_automata.execute(rts, cs_err_flag, cs_off_flag, cs_ok_flag, cs_warn_flag)

            # get the results
            curr_state = cs_automata.get_curr_state()

            cs_dfr = DfReading(time=rts, value=curr_state, datafeed=curr_state_df, restored=False)
            derived_df_reading_map[CURR_STATE_FIELD_NAME]["new_df_readings"].append(cs_dfr)

            logger.debug(f"Curr State Automata state = {cs_automata.get_state()}")

            # -6-2- update interval maps
            all_occs.append_occurrence(curr_state.value)  # NOTE: 'value' to serialize JSON

            # -6-3- evaluate status

            # execute ST finite automata
            st_automata.execute(all_occs)

            # get the results
            status = st_automata.get_status()

            st_dfr = DfReading(time=rts, value=status, datafeed=status_df, restored=False)
            derived_df_reading_map[STATUS_FIELD_NAME]["new_df_readings"].append(st_dfr)

            logger.debug(f"Status Automata state = {st_automata.get_state()}")

        # -7-  update app output
        update_map["cursor_ts"] = end_rts
        update_map["is_catching_up"] = is_catching_up
        update_map["alarm_payload"] = alarm_payload
        update_map["health"] = cs_automata.get_health_from_app()

        updated_state = {
            "cs_automata_int_state": cs_automata.get_internal_state_as_dict(),
            "st_automata_int_state": st_automata.get_internal_state_as_dict(),
            "all_occs": all_occs,
        }

        update_map["state"] = updated_state

    return derived_df_reading_map, update_map

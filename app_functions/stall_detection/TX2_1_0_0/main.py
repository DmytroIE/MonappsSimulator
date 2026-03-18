import logging
from functools import partial

from app_functions.helpers.classes.app_function import AppFunction

from common.constants import STATUS_FIELD_NAME, CURR_STATE_FIELD_NAME
from app_functions.helpers.utils.app_func_utils import add_value_to_df_value_map
from utils.alarm_utils import add_to_alarm_payload

from app_functions.helpers.utils.occ_cluster_list import OccurrenceClusterList
from app_functions.helpers.automatas.curr_state_type1 import Automata as CsAutomata
from app_functions.helpers.automatas.status_type1 import Automata as StAutomata

from .schemas import AppState, AppFuncSettingsModel as AfsModel

logger = logging.getLogger("#stall_TX2_1_0_0")


class MonitoringAppFunction(AppFunction[AfsModel]):

    def __init__(self):
        super().__init__(AfsModel, logger)

    def _prepare_custom_variables(self):
        app_state = AppState(**self.app.state)
        self.cs_automata_int_state = app_state.cs_automata_int_state
        self.st_automata_int_state = app_state.st_automata_int_state
        self.all_occs = OccurrenceClusterList(app_state.all_occs)

    def _calculate_within_cycle(self):
        add_to_alarm_payload_part = partial(add_to_alarm_payload, self.one_step_alarm_payload)

        self.cs_automata = CsAutomata(
            self.cs_automata_int_state,
            add_to_alarm_payload_part,
            "Data is invalid",
            "Stall detected",
            count_thres=self.app_settings_valid_from.cs_delay_trans_counts,
        )

        # create a status automata
        self.st_automata = StAutomata(
            self.st_automata_int_state,
            add_to_alarm_payload_part,
            self.app_settings_valid_from.undef_cid,
            self.app_settings_valid_from.ok_from_undef_cid,
            self.app_settings_valid_from.ok_from_warn_cid,
            self.app_settings_valid_from.warn_cid,
        )

        # evaluate current state
        line = self.df_value_map.get(self.rts, None)
        temp_in = None
        temp_out = None
        if line is not None:
            temp_in = line.get("Temp in", None)
            temp_out = line.get("Temp out", None)

        cs_err_flag = (
            temp_in is None
            or temp_out is None
            or temp_out - temp_in > self.app_settings_valid_from.temp_diff_error_threshold
        )
        cs_off_flag = not cs_err_flag and temp_in <= self.app_settings_valid_from.temp_in_threshold
        cs_ok_flag = (
            not cs_err_flag and not cs_off_flag and temp_in - temp_out <= self.app_settings_valid_from.delta_temp
        )
        cs_warn_flag = (
            not cs_err_flag and not cs_off_flag and temp_in - temp_out > self.app_settings_valid_from.delta_temp
        )

        # execute current finite automata
        self.cs_automata.execute(self.rts, cs_err_flag, cs_off_flag, cs_ok_flag, cs_warn_flag)
        curr_state = self.cs_automata.get_curr_state()
        add_value_to_df_value_map(self.df_value_map, CURR_STATE_FIELD_NAME, self.rts, curr_state.value)

        # update interval maps
        self.all_occs_updated = self.all_occs.create_copy_for_appending()
        self.all_occs_updated.append_occurrence(curr_state.value)

        # evaluate status
        # execute ST finite automata
        self.st_automata.execute(self.all_occs_updated)
        status = self.st_automata.get_status()
        add_value_to_df_value_map(self.df_value_map, STATUS_FIELD_NAME, self.rts, status.value)

    def _update_additional_outputs(self):
        self.cs_automata_int_state = self.cs_automata.get_internal_state()
        self.st_automata_int_state = self.st_automata.get_internal_state()
        self.all_occs = self.all_occs_updated  # update the occurrence cluster list

        updated_state = {
            "st_automata_int_state": (
                self.st_automata_int_state.model_dump() if self.st_automata_int_state is not None else None
            ),
            "cs_automata_int_state": (
                self.cs_automata_int_state.model_dump() if self.cs_automata_int_state is not None else None
            ),
            "all_occs": self.all_occs,
        }
        self.update_map["state"] = updated_state


function = MonitoringAppFunction()

from functools import partial

from app_functions.helpers.classes.app_function import AppFunction
from app_functions.helpers.utils.df_utils import add_value_to_df_value_map
from common.constants import STATUS_FIELD_NAME, CURR_STATE_FIELD_NAME, CurrStateTypes
from utils.alarm_utils import add_to_alarm_payload

from app_functions.helpers.utils.occ_cluster_list import OccurrenceClusterList
from app_functions.helpers.automatas.status_type1 import (
    Automata as StAutomata,
)
from app_functions.helpers.utils.totalaizer_utils import (
    straighten_tot_readings,
    get_boundaries_of_overlapping_tot_readings,
)
from app_functions.helpers.utils.df_utils import get_df_map_of_series

from .schemas import AppState, AppFuncSettingsModel as AfsModel


class CrrAppFunction(AppFunction[AfsModel]):

    def __init__(self):
        super().__init__(AfsModel)

    def _prepare_before_getting_df_value_map(self):
        first_grid_rts = self.start_rts + self.app.time_resample
        window_length = int(
            self.settings_bundle.get_settings(first_grid_rts).window_length_coef * self.app.time_resample
        )
        self.value_map_start_rts = first_grid_rts - window_length

    def _prepare_custom_variables(self):
        self.steam_tot_df_map = get_df_map_of_series(self.df_map, "Steam total")
        self.mu_water_tot_df_map = get_df_map_of_series(self.df_map, "Make-up water total")
        self.lost_water_tot_df_map = get_df_map_of_series(self.df_map, "Lost water total")
        app_state = AppState(**self.app.state)
        self.st_automata_int_state = app_state.st_automata_int_state
        self.all_occs = OccurrenceClusterList(app_state.all_occs)

    def _calculate_within_cycle(self):
        add_to_alarm_payload_part = partial(add_to_alarm_payload, self.one_step_alarm_payload)

        # create a status automata
        self.st_automata = StAutomata(
            self.st_automata_int_state,
            add_to_alarm_payload_part,
            self.app_settings_valid_from.undef_cid,
            self.app_settings_valid_from.ok_from_undef_cid,
            self.app_settings_valid_from.ok_from_warn_cid,
            self.app_settings_valid_from.warn_cid,
        )

        # creating a window df_value_map for the current timestamp
        window_length = int(self.app_settings_valid_from.window_length_coef * self.app.time_resample)
        # copy is needed as the 'straighten_tot_readings' function modifies the df_value_map in place
        window_df_value_map = {
            ts: vals.copy() for ts, vals in self.df_value_map.items() if self.rts - window_length < ts <= self.rts
        }

        # then it is necessary to put the readings in order before further processing
        all_totalizers = [
            *self.steam_tot_df_map.values(),
            *self.mu_water_tot_df_map.values(),
            *self.lost_water_tot_df_map.values(),
        ]
        for df in all_totalizers:
            straighten_tot_readings(window_df_value_map, df.name)

        result = get_boundaries_of_overlapping_tot_readings(
            window_df_value_map,
            all_totalizers,
            margin_ms=self.app_settings_valid_from.overlap_margin,
        )

        if result is None:  # no overlap
            add_to_alarm_payload(self.one_step_alarm_payload, "No overlapping readings", None, self.rts, "w")
            curr_state = CurrStateTypes.UNDEFINED
        else:
            left_boundary_ts, right_boundary_ts, tot_df_boundary_value_map = result
            min_window_length = (
                min(
                    self.app_settings_valid_from.min_window_length_coef, self.app_settings_valid_from.window_length_coef
                )
                * self.app.time_resample
            )  # protection from 'min_window_length_coef' being greater than 'window_length_coef'
            if right_boundary_ts - left_boundary_ts < min_window_length:
                add_to_alarm_payload(self.one_step_alarm_payload, "Min window length not met", None, self.rts, "w")
                curr_state = CurrStateTypes.UNDEFINED
            else:
                steam_generated = 0
                for df in self.steam_tot_df_map.values():
                    steam_generated += (
                        tot_df_boundary_value_map[df.name]["right_val"] - tot_df_boundary_value_map[df.name]["left_val"]
                    )

                if steam_generated < self.app_settings_valid_from.min_steam_gen_value:
                    add_to_alarm_payload(
                        self.one_step_alarm_payload, "No steam was generated over the period", None, self.rts, "i"
                    )
                    curr_state = CurrStateTypes.UNDEFINED
                else:
                    # calculate amount of water losses
                    water_lost = 0
                    for df in self.lost_water_tot_df_map.values():
                        water_lost += (
                            tot_df_boundary_value_map[df.name]["right_val"]
                            - tot_df_boundary_value_map[df.name]["left_val"]
                        )

                    # calculate the amount of water consumed
                    mu_water_consumed = 0
                    for df in self.mu_water_tot_df_map.values():
                        mu_water_consumed += (
                            tot_df_boundary_value_map[df.name]["right_val"]
                            - tot_df_boundary_value_map[df.name]["left_val"]
                        )

                    # calculate condensate return rate
                    water_diff = mu_water_consumed - water_lost
                    if water_diff < 0:
                        # protection from wrong readings when water losses are greater than make-up water consumption
                        add_to_alarm_payload(
                            self.one_step_alarm_payload,
                            "Water losses are greater than make-up water consumption",
                            None,
                            self.rts,
                            "w",
                        )
                        water_diff = 0
                    if water_diff > steam_generated:
                        # protection from wrong readings when water difference is greater than steam generated
                        add_to_alarm_payload(
                            self.one_step_alarm_payload,
                            "Water difference is greater than steam generated",
                            None,
                            self.rts,
                            "w",
                        )
                        water_diff = steam_generated
                    crr = (steam_generated - water_diff) / steam_generated * 100.0
                    self.logger.debug(f">>> CRR = {crr}")
                    add_value_to_df_value_map(self.df_value_map, "Cond return rate", self.rts, crr)

                    if crr < self.app_settings_valid_from.crr_warning_threshold:
                        curr_state = CurrStateTypes.WARNING
                        add_to_alarm_payload(
                            self.one_step_alarm_payload,
                            "Condensate return rate is below threshold",
                            None,
                            self.rts,
                            "w",
                        )
                    else:
                        curr_state = CurrStateTypes.OK

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
        self.st_automata_int_state = self.st_automata.get_internal_state()
        self.all_occs = self.all_occs_updated  # update the occurrence cluster list

        updated_state = {
            "st_automata_int_state": (
                self.st_automata_int_state.model_dump() if self.st_automata_int_state is not None else None
            ),
            "all_occs": self.all_occs,
        }
        self.update_map["state"] = updated_state


function = CrrAppFunction()

import logging
from functools import partial
from math import sqrt
from classes.application import Application
from classes.datafeed import Datafeed
from classes.dfreading import DfReading
from utils.ts_utils import create_grid
from common.complex_types import AppFuncReturn, DerivedDfReadingMap, UpdateMap
from common.constants import STATUS_FIELD_NAME, CURR_STATE_FIELD_NAME, CurrStateTypes, HealthGrades
from utils.app_func_utils import get_end_rts, get_df_value_map
from utils.alarm_utils import add_to_alarm_payload

from app_functions.helpers.utils.occ_cluster_list import OccurrenceClusterList
from app_functions.helpers.automatas.status_type1 import Automata as StAutomata
from app_functions.helpers.utils.totalaizer_utils import (
    straighten_tot_readings,
    get_boundaries_of_overlapping_tot_readings,
)
from app_functions.helpers.utils.app_func_settings_bundle import AppFuncSettingsBundle
from app_functions.helpers.utils.steam_utils import get_pres_from_sat_temp
from app_functions.helpers.utils.df_utils import get_datafeeds_of_series

from .schemas import AppState, AppFuncSettingsModel as AfsModel

logger = logging.getLogger("#ccr_SMW_TOT_1_0_0")


def function(
    app: Application, native_df_map: dict[str, Datafeed], derived_df_map: dict[str, Datafeed]
) -> AppFuncReturn:

    logger.info("'crr_SMW_TOT_1_0_0' starts executing...")

    # get datafeeds
    steam_tot_dfs = get_datafeeds_of_series(native_df_map, "Steam total {}")
    water_tot_dfs = get_datafeeds_of_series(native_df_map, "Water total {}")
    bdn_valve_state_dfs = get_datafeeds_of_series(native_df_map, "Bdn valve {} state")
    bdn_temp_dfs = get_datafeeds_of_series(native_df_map, "Bdn temp {}")
    bdn_water_mass_dfs = get_datafeeds_of_series(derived_df_map, "Bdn water mass {}")

    crr_df = derived_df_map["Cond return rate"]
    curr_state_df = derived_df_map[CURR_STATE_FIELD_NAME]
    status_df = derived_df_map[STATUS_FIELD_NAME]

    derived_df_reading_map: DerivedDfReadingMap = {
        "Cond return rate": {"df": crr_df, "new_df_readings": []},
        CURR_STATE_FIELD_NAME: {"df": curr_state_df, "new_df_readings": []},
        STATUS_FIELD_NAME: {"df": status_df, "new_df_readings": []},
    }
    derived_df_reading_map.update({df.name: {"df": df, "new_df_readings": []} for df in bdn_water_mass_dfs})

    # prepare other variables
    update_map: UpdateMap = {}
    alarm_payload = {}

    # at least one steam totalizer and one water totalizer df should exist
    if len(steam_tot_dfs) == 0 or len(water_tot_dfs) == 0:
        update_map["cursor_ts"] = app.cursor_ts
        update_map["is_catching_up"] = False
        update_map["alarm_payload"] = alarm_payload
        update_map["health"] = HealthGrades.ERROR
        return derived_df_reading_map, update_map

    # get end time
    start_rts = app.cursor_ts
    end_rts, is_catching_up = get_end_rts(native_df_map.values(), app.time_resample, start_rts, len(derived_df_map))

    if end_rts > start_rts:  # all datafeed have readings with ts > cursor_ts

        # getting app settings
        settings_bundle = AppFuncSettingsBundle[AfsModel](app.settings, AfsModel)  # validation and default values
        base_settings = settings_bundle.get_settings()

        app_state = AppState(**app.state)

        # create the status automata
        add_to_alarm_payload_part = partial(add_to_alarm_payload, alarm_payload)
        st_automata_int_state = app_state.st_automata_int_state
        st_automata = StAutomata(
            st_automata_int_state,
            add_to_alarm_payload_part,
            base_settings.undef_cid,
            base_settings.ok_from_undef_cid,
            base_settings.ok_from_warn_cid,
            base_settings.warn_cid,
        )

        all_occs = OccurrenceClusterList(app_state.all_occs)

        # creating the grid
        grid = create_grid(start_rts + app.time_resample, end_rts, app.time_resample)

        # moving along the grid
        for rts in grid:
            alarm_payload[rts] = {}  # NOTE: this is very important, add at least an empty dict for each rts

            settings_valid_from = settings_bundle.get_settings(rts)
            window_length = int(settings_valid_from.window_length_coef * app.time_resample)
            df_value_map = get_df_value_map(native_df_map.values(), rts - window_length, rts)

            # for datafeeds totalizers, it is necessary to put the readings in order before further processing
            tot_dfs = [*steam_tot_dfs, *water_tot_dfs]
            for df in tot_dfs:
                straighten_tot_readings(df_value_map, df.name)

            result = get_boundaries_of_overlapping_tot_readings(df_value_map, tot_dfs)
            if result is None:  # no overlap
                add_to_alarm_payload(alarm_payload, "No overlapping readings", {}, rts, "e")
                curr_state = CurrStateTypes.UNDEFINED
            else:
                left_boundary_ts, right_boundary_ts, tot_df_boundary_value_map = result
                min_window_length = settings_valid_from.min_window_length_coef * app.time_resample
                if right_boundary_ts - left_boundary_ts < min_window_length:
                    add_to_alarm_payload(alarm_payload, "Min window length not met", {}, rts, "e")
                    curr_state = CurrStateTypes.UNDEFINED
                else:
                    steam_generated = 0
                    for df in steam_tot_dfs:
                        steam_generated += (
                            tot_df_boundary_value_map[df.name]["right_val"]
                            - tot_df_boundary_value_map[df.name]["left_val"]
                        )

                    if steam_generated < settings_valid_from.min_steam_gen_value:
                        add_to_alarm_payload(alarm_payload, "No steam was generated over the period", {}, rts, "i")
                        curr_state = CurrStateTypes.UNDEFINED
                    else:
                        # calculate amount of blowdown water
                        bdn_water_drained = 0
                        for idx, dfs in enumerate(zip(bdn_valve_state_dfs, bdn_temp_dfs, bdn_water_mass_dfs)):
                            bdn_vlv_df, bdn_temp_df, bdn_water_mass_df = dfs
                            kv = settings_valid_from.bvalve_kvs[idx]
                            aux_coeff = kv * bdn_vlv_df.time_resample / 3600000
                            for ts, line in df_value_map.items():
                                valve_open = line.get(bdn_vlv_df.name, False)
                                bdn_temp = line.get(bdn_temp_df.name, 0)
                                bdn_pres = get_pres_from_sat_temp(bdn_temp)
                                w = sqrt(bdn_pres * 0.9) * 1000 * aux_coeff  # TODO: replace '1000' with density(T)
                                if bdn_water_mass_df.last_reading_ts is None or ts > bdn_water_mass_df.last_reading_ts:
                                    bdn_water_dfr = DfReading(
                                        time=ts, value=w, datafeed=bdn_water_mass_df, restored=False
                                    )
                                    derived_df_reading_map[bdn_water_mass_df.name]["new_df_readings"].append(
                                        bdn_water_dfr
                                    )
                                if valve_open and ts >= left_boundary_ts and ts <= right_boundary_ts:
                                    bdn_water_drained += w

                        water_consumed = 0
                        for df in water_tot_dfs:
                            water_consumed += (
                                tot_df_boundary_value_map[df.name]["right_val"]
                                - tot_df_boundary_value_map[df.name]["left_val"]
                            )

                        crr = (steam_generated + bdn_water_drained - water_consumed) / steam_generated * 100.0
                        crr = min(100.0, crr)
                        crr = max(0.0, crr)
                        if crr_df.last_reading_ts is None or rts > crr_df.last_reading_ts:
                            crr_dfr = DfReading(time=rts, value=crr, datafeed=crr_df, restored=False)
                            derived_df_reading_map[crr_df.name]["new_df_readings"].append(crr_dfr)
                        if crr < settings_valid_from.crr_warning_threshold:
                            curr_state = CurrStateTypes.WARNING
                            add_to_alarm_payload(
                                alarm_payload, "Condensate return rate is below threshold", {}, rts, "e"
                            )
                        else:
                            curr_state = CurrStateTypes.OK

            cs_dfr = DfReading(time=rts, value=curr_state, datafeed=curr_state_df, restored=False)
            derived_df_reading_map[CURR_STATE_FIELD_NAME]["new_df_readings"].append(cs_dfr)

            logger.debug(f"Curr State = {curr_state}")

            # update interval maps
            all_occs.append_occurrence(curr_state.value)  # NOTE: 'value' to serialize JSON

            # evaluate status

            # execute ST finite automata
            st_automata.execute(all_occs)

            # get the results
            status = st_automata.get_status()

            st_dfr = DfReading(time=rts, value=status, datafeed=status_df, restored=False)
            derived_df_reading_map[STATUS_FIELD_NAME]["new_df_readings"].append(st_dfr)

            logger.debug(f"Status Automata state = {st_automata.get_state()}")

        # update app output
        update_map["cursor_ts"] = end_rts
        update_map["is_catching_up"] = is_catching_up
        update_map["alarm_payload"] = alarm_payload
        update_map["health"] = HealthGrades.OK

        updated_state = {
            "st_automata_int_state": st_automata.get_internal_state_as_dict(),
            "all_occs": all_occs,
        }

        update_map["state"] = updated_state

    return derived_df_reading_map, update_map

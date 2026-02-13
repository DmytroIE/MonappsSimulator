import logging
from functools import partial
from math import sqrt
from classes.application import Application
from classes.datafeed import Datafeed
from classes.dfreading import DfReading
from utils.ts_utils import create_grid, floor_timestamp, ceil_timestamp
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
from app_functions.helpers.utils.steam_utils import get_pres_from_sat_temp, get_water_density_from_sat_temp
from app_functions.helpers.utils.df_utils import (
    get_datafeeds_of_series,
    get_last_df_reading,
    get_df_readings,
    get_df_name_part,
)

from .schemas import AppState, AppFuncSettingsModel as AfsModel

logger = logging.getLogger("#ccr_SMW_TOT_1_0_0")


def function(
    app: Application, native_df_map: dict[str, Datafeed], derived_df_map: dict[str, Datafeed]
) -> AppFuncReturn:

    logger.info("'crr_SMW_TOT_1_0_0' starts executing...")

    # get datafeeds
    steam_tot_dfs = get_datafeeds_of_series(native_df_map, "Steam total")
    water_tot_dfs = get_datafeeds_of_series(native_df_map, "Water total")

    bdn_water_tot_dfs = get_datafeeds_of_series(derived_df_map, "Bdn water total")
    crr_df = derived_df_map["Cond return rate"]
    curr_state_df = derived_df_map[CURR_STATE_FIELD_NAME]
    status_df = derived_df_map[STATUS_FIELD_NAME]

    derived_df_reading_map: DerivedDfReadingMap = {
        "Cond return rate": {"df": crr_df, "new_df_readings": []},
        CURR_STATE_FIELD_NAME: {"df": curr_state_df, "new_df_readings": []},
        STATUS_FIELD_NAME: {"df": status_df, "new_df_readings": []},
    }
    derived_df_reading_map.update({df.name: {"df": df, "new_df_readings": []} for df in bdn_water_tot_dfs})

    # prepare other variables
    alarm_payload = {}
    update_map: UpdateMap = {
        "health": HealthGrades.OK,
        "alarm_payload": alarm_payload,
        "is_catching_up": False,
        "cursor_ts": app.cursor_ts,
    }

    # at least one steam totalizer and one water totalizer df should exist
    if len(steam_tot_dfs) == 0 or len(water_tot_dfs) == 0:
        add_to_alarm_payload(alarm_payload, "No steam or water totalizer", {}, app.cursor_ts, "e")
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
            update_map["health"] = HealthGrades.UNDEFINED

            # settings are the same within the 'app.time_resample' interval
            settings_valid_from = settings_bundle.get_settings(rts)

            # check datafeeds and parameters
            # For water and steam totalizers, if no pulse weight is provided, the default value of 1 is used
            # For bdn water totalizers, if there are no corresponding datafeeds for valve state and bdn temperature,
            # as well as if there is no substitution value for bdn temperature in case when there's no datafeed,
            # the whole set is excluded from the calculation
            warning = False

            steam_tot_weights = []
            for df in steam_tot_dfs:
                volat_name_part = get_df_name_part(df, "Steam total")
                if (weight := settings_valid_from.steam_tot_weights.get(volat_name_part)) is None:
                    add_to_alarm_payload(
                        alarm_payload,
                        f"Pulse weight for steam totalizer '{volat_name_part}' not provided and set to 1",
                        {},
                        rts,
                        "w",
                    )
                    warning = True
                    steam_tot_weights.append(1.0)
                else:
                    steam_tot_weights.append(weight)

            water_tot_weights = []
            for df in water_tot_dfs:
                volat_name_part = get_df_name_part(df, "Water total")
                if (weight := settings_valid_from.water_tot_weights.get(volat_name_part)) is None:
                    add_to_alarm_payload(
                        alarm_payload,
                        f"Pulse weight for water totalizer '{volat_name_part}' not provided and set to 1",
                        {},
                        rts,
                        "w",
                    )
                    warning = True
                    water_tot_weights.append(1.0)
                else:
                    water_tot_weights.append(weight)

            bdn_valve_state_dfs = []
            bdn_temp_dfs = []
            bdn_temp_dfs_and_subst_values = []
            bdn_valve_kvs = []
            new_bdn_water_tot_dfs = []
            for df in bdn_water_tot_dfs:
                volat_name_part = get_df_name_part(df, "Bdn water total")
                if (kv := settings_valid_from.bdn_valve_kvs.get(volat_name_part)) is None:
                    add_to_alarm_payload(
                        alarm_payload, f"kv for blowdown valve '{volat_name_part}' not provided, excluded", {}, rts, "w"
                    )
                    warning = True
                    continue
                if (bdn_valve_state_df := native_df_map.get(f"Bdn valve state {volat_name_part}")) is None:
                    add_to_alarm_payload(
                        alarm_payload,
                        f"Blowdown valve state df '{volat_name_part}' does not exist, excluded",
                        {},
                        rts,
                        "w",
                    )
                    warning = True
                    continue
                if (bdn_temp_df := native_df_map.get(f"Bdn temp {volat_name_part}")) is None:
                    if (bdn_temp_subst_value := settings_valid_from.bdn_temp_subst_values.get(volat_name_part)) is None:
                        add_to_alarm_payload(
                            alarm_payload,
                            f"Substitution value for blowdown temp '{volat_name_part}' not provided, excluded",
                            {},
                            rts,
                            "w",
                        )
                        warning = True
                        continue
                bdn_valve_state_dfs.append(bdn_valve_state_df)
                bdn_temp_dfs_and_subst_values.append(bdn_temp_df or bdn_temp_subst_value)
                if bdn_temp_df:
                    bdn_temp_dfs.append(bdn_temp_df)
                new_bdn_water_tot_dfs.append(df)
                bdn_valve_kvs.append(kv)

            bdn_water_tot_dfs = new_bdn_water_tot_dfs
            if warning:
                update_map["health"] = max(update_map["health"], HealthGrades.WARNING)

            # get values for steam and water totalizers (native totalizers)
            window_length = int(settings_valid_from.window_length_coef * app.time_resample)

            nat_tot_dfs = [*steam_tot_dfs, *water_tot_dfs]
            tot_df_value_map = get_df_value_map(nat_tot_dfs, rts - window_length, rts)

            # then it is necessary to put the readings in order before further processing
            for df in nat_tot_dfs:
                straighten_tot_readings(tot_df_value_map, df.name)

            result = get_boundaries_of_overlapping_tot_readings(tot_df_value_map, nat_tot_dfs)

            # regardless of what the result is, it is necessary to create bdn water totalizer readings
            # for the current bin
            bdn_df_value_map = get_df_value_map([*bdn_valve_state_dfs, *bdn_temp_dfs], rts - app.time_resample, rts)

            for bdn_valve_state_df, bdn_temp_df_or_subst_value, bdn_water_tot_df, kv in zip(
                bdn_valve_state_dfs, bdn_temp_dfs_and_subst_values, bdn_water_tot_dfs, bdn_valve_kvs
            ):
                aux_coeff = kv * bdn_valve_state_df.time_resample / 3600000
                last_dfr = get_last_df_reading(bdn_water_tot_df)
                last_dfr_ts = last_dfr.time if last_dfr is not None else 0
                acc_value = last_dfr.value if last_dfr is not None else 0
                for ts, line in bdn_df_value_map.items():
                    if ts <= last_dfr_ts:
                        continue  # just in case, to avoid overwriting existing df readings
                    valve_open = line.get(bdn_valve_state_df.name)
                    if isinstance(bdn_temp_df_or_subst_value, Datafeed):
                        bdn_temp = line.get(bdn_temp_df_or_subst_value.name)
                    else:
                        bdn_temp = bdn_temp_df_or_subst_value
                    if valve_open is None or bdn_temp is None:
                        continue
                    valve_open = 1 if valve_open else 0
                    bdn_pres = get_pres_from_sat_temp(bdn_temp)
                    density = get_water_density_from_sat_temp(bdn_temp)
                    # 0.9 is a coefficient that accounts for backpressure in the blowdown line
                    if acc_value > settings_valid_from.bdn_water_tot_reset_value:
                        acc_value = 0  # reset the totalizer value in order not to have very high values
                    acc_value += sqrt(bdn_pres * 0.9) * density * aux_coeff * valve_open

                    # create a new df reading
                    bdn_water_dfr = DfReading(time=ts, value=acc_value, datafeed=bdn_water_tot_df, restored=False)
                    derived_df_reading_map[bdn_water_tot_df.name]["new_df_readings"].append(bdn_water_dfr)

            if result is None:  # no overlap
                add_to_alarm_payload(alarm_payload, "No overlapping readings", {}, rts, "w")
                curr_state = CurrStateTypes.UNDEFINED
            else:
                left_boundary_ts, right_boundary_ts, tot_df_boundary_value_map = result
                min_window_length = (
                    min(settings_valid_from.min_window_length_coef, settings_valid_from.window_length_coef)
                    * app.time_resample
                )  # protection from 'min_window_length_coef' being greater than 'window_length_coef'
                if right_boundary_ts - left_boundary_ts < min_window_length:
                    add_to_alarm_payload(alarm_payload, "Min window length not met", {}, rts, "w")
                    curr_state = CurrStateTypes.UNDEFINED
                else:
                    steam_generated = 0
                    for df, weight in zip(
                        steam_tot_dfs,
                        steam_tot_weights,
                    ):
                        steam_generated += (
                            tot_df_boundary_value_map[df.name]["right_val"]
                            - tot_df_boundary_value_map[df.name]["left_val"]
                        ) * weight

                    if steam_generated < settings_valid_from.min_steam_gen_value:
                        add_to_alarm_payload(alarm_payload, "No steam was generated over the period", {}, rts, "i")
                        curr_state = CurrStateTypes.UNDEFINED
                    else:
                        # calculate amount of blowdown water
                        bdn_water_drained = 0
                        # use only readings within the defined boundaries
                        for bdn_water_tot_df in bdn_water_tot_dfs:
                            bdn_water_dfrs = []
                            if (
                                bdn_water_tot_df.last_reading_ts is not None
                                and left_boundary_ts <= bdn_water_tot_df.last_reading_ts
                            ):
                                # fetch existing df readings from the database
                                bdn_water_dfrs = get_df_readings(bdn_water_tot_df, left_boundary_ts, right_boundary_ts)
                                # and blend them with the new ones into the df_reading_map
                            bdn_water_dfr_val_map = {}
                            for bdn_water_dfr in [
                                *bdn_water_dfrs,
                                *derived_df_reading_map[bdn_water_tot_df.name]["new_df_readings"],
                            ]:
                                bdn_water_dfr_val_map[bdn_water_dfr.time] = {bdn_water_tot_df.name: bdn_water_dfr.value}
                            bdn_water_dfr_val_map = dict(sorted(bdn_water_dfr_val_map.items()))
                            # checking if there are many missed readings, which can affect the result
                            # create a grid and go along it counting gaps
                            left = ceil_timestamp(left_boundary_ts, bdn_water_tot_df.time_resample)
                            right = floor_timestamp(right_boundary_ts, bdn_water_tot_df.time_resample)
                            bdn_water_df_grid = create_grid(left, right, bdn_water_tot_df.time_resample)
                            num_missed_readings = 0
                            for t in bdn_water_df_grid:
                                if bdn_water_dfr_val_map.get(t) is None:
                                    num_missed_readings += 1
                            if num_missed_readings > len(bdn_water_df_grid) * 0.2:
                                add_to_alarm_payload(
                                    alarm_payload,
                                    f"Too many missed values for {bdn_water_tot_df.name}",
                                    {},
                                    rts,
                                    "w",
                                )
                                update_map["health"] = max(update_map["health"], HealthGrades.WARNING)

                            if len(bdn_water_dfr_val_map) > 1:
                                straighten_tot_readings(bdn_water_dfr_val_map, bdn_water_tot_df.name)
                                first_reading = next(iter(bdn_water_dfr_val_map.values())).get(bdn_water_tot_df.name)
                                last_reading = next(reversed(bdn_water_dfr_val_map.values())).get(bdn_water_tot_df.name)
                                bdn_water_drained += last_reading - first_reading

                        # calculate the amount of water consumed
                        water_consumed = 0
                        for df, pulse_weight in zip(water_tot_dfs, water_tot_weights):
                            water_consumed += (
                                tot_df_boundary_value_map[df.name]["right_val"]
                                - tot_df_boundary_value_map[df.name]["left_val"]
                            ) * pulse_weight

                        # calculate condensate return rate
                        crr = (steam_generated + bdn_water_drained - water_consumed) / steam_generated * 100.0
                        crr = min(100.0, crr)
                        crr = max(0.0, crr)
                        if crr_df.last_reading_ts is None or rts > crr_df.last_reading_ts:
                            crr_dfr = DfReading(time=rts, value=crr, datafeed=crr_df, restored=False)
                            derived_df_reading_map[crr_df.name]["new_df_readings"].append(crr_dfr)
                        if crr < settings_valid_from.crr_warning_threshold:
                            curr_state = CurrStateTypes.WARNING
                            add_to_alarm_payload(
                                alarm_payload, "Condensate return rate is below threshold", {}, rts, "w"
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

        updated_state = {
            "st_automata_int_state": st_automata.get_internal_state_as_dict(),
            "all_occs": all_occs,
        }

        update_map["state"] = updated_state

    return derived_df_reading_map, update_map

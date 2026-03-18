import logging
import random
import time

from app_functions.helpers.utils.app_func_utils import get_df_maps_from_app
from common.constants import CURR_STATE_FIELD_NAME, STATUS_FIELD_NAME, CurrStateTypes, settings
from classes.application import Application
from classes.dfreading import DfReading

from app_functions.helpers.classes.app_func_settings_bundle import AppFuncSettingsBundle
from utils.alarm_utils import add_to_alarm_payload
from .schemas import AppFuncSettingsModel as AfsModel

from common.complex_types import DerivedDfReadingMap, UpdateMap
from utils.ts_utils import create_dt_from_ts_ms, create_now_ts_ms, floor_timestamp

logger = logging.getLogger("#fdg_VER1_1_0_0")


def function(app: Application, derived_df_reading_map: DerivedDfReadingMap, update_map: UpdateMap) -> None:
    """
    Used as a generator of different status and current state values for testing the update algorithms.
    Also, sometimes can generate exceptions to test the exception handling in the wrapper.
    """
    logger.info("App function starts executing...")

    # get datafeeds
    [_, derived_df_map] = get_df_maps_from_app(app).maps

    status_df = derived_df_map[STATUS_FIELD_NAME]
    curr_state_df = derived_df_map[CURR_STATE_FIELD_NAME]

    for df in derived_df_map.values():
        derived_df_reading_map[df.name] = {"df": df, "new_df_readings": []}

    # prepare other variables
    alarm_payload = update_map.get("alarm_payload")
    if alarm_payload is None:
        alarm_payload = {}
        update_map["alarm_payload"] = alarm_payload

    end_rts = floor_timestamp(create_now_ts_ms(), app.time_resample)
    if end_rts == app.cursor_ts:
        # it means that the function is invoked too often, more often than time_resample
        # it is necessary to skip the invocation, otherwise new df_readings with already
        # existing ts will be created, which will lead to an integrity error
        logger.debug("Function is invoked too often, skipping...")
        return

    settings_bundle = AppFuncSettingsBundle[AfsModel](app.settings, AfsModel)

    num_df_to_process = 2  # status_df + curr_state_df
    max_num_dfreadings_per_one_df_to_process = int(settings.NUM_MAX_DFREADINGS_TO_PROCESS / num_df_to_process)
    max_num_dfreadings_per_one_df_to_process = max(
        2, max_num_dfreadings_per_one_df_to_process
    )  # protection against 0 and 1
    end_rts_by_max_num_df_readings = app.cursor_ts + app.time_resample * max_num_dfreadings_per_one_df_to_process
    is_catching_up = end_rts > end_rts_by_max_num_df_readings
    update_map["is_catching_up"] = is_catching_up
    end_rts = min(end_rts, end_rts_by_max_num_df_readings)

    rts = app.cursor_ts + app.time_resample
    while rts <= end_rts:
        one_step_alarm_payload = {rts: {}}

        app_settings = settings_bundle.get_settings(rts)
        prob_exception = app_settings.prob_exception

        logger.debug(f"---> Generating for {create_dt_from_ts_ms(rts)} - {rts}")

        # imitation of doing something useful that leads to the generation of current state and status values
        curr_state = random.randint(0, 3)
        status = random.randint(0, 3)
        logger.debug(f"Generated values - curr_state: {curr_state}, status: {status}")

        if status == CurrStateTypes.ERROR:
            add_to_alarm_payload(one_step_alarm_payload, "Status is ERROR", None, rts, "e")
        if status == CurrStateTypes.WARNING:
            add_to_alarm_payload(one_step_alarm_payload, "Status is WARNING", None, rts, "w")

        if curr_state == CurrStateTypes.ERROR:
            add_to_alarm_payload(one_step_alarm_payload, "Current state is ERROR", None, rts, "e")
        if curr_state == CurrStateTypes.WARNING:
            add_to_alarm_payload(one_step_alarm_payload, "Current state is WARNING", None, rts, "w")

        # generate an exception at the end of calculations to check
        # how the 'excep_health' mechanism works; also to check that
        # the current "one step" alarm payload doesn't get into the
        # exported 'update_map"
        var = None
        if random.random() < prob_exception:
            logger.debug("An exception is generated for testing purposes...")
            var = 1 / 0  # generate an exception

        # update at the end of the cycle
        if curr_state is not None:
            dfr = DfReading(time=rts, value=curr_state, datafeed=curr_state_df, restored=False)
            derived_df_reading_map[CURR_STATE_FIELD_NAME]["new_df_readings"].append(dfr)
        if status is not None:
            dfr = DfReading(time=rts, value=status, datafeed=status_df, restored=False)
            derived_df_reading_map[STATUS_FIELD_NAME]["new_df_readings"].append(dfr)

        update_map["cursor_ts"] = rts
        # update_map["health"] = HealthGrades(random.randint(0, 3))

        for t, p in one_step_alarm_payload.items():
            if alarm_payload.get(t) is None:
                alarm_payload[t] = p
            else:
                alarm_payload[t].update(p)

        rts += app.time_resample

    # imitate synchronous delay
    time.sleep(random.randrange(1, 4))

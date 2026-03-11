import logging
import traceback
import json
from collections.abc import Iterable
from typing import Literal

from classes.application import Application
from classes.dfreading import DfReading
from common.constants import HealthGrades, STATUS_FIELD_NAME, CURR_STATE_FIELD_NAME, IntegrityError
from common.complex_types import AppFunction, DerivedDfReadingMap, UpdateMap
from services.dfr_creator import DfrCreator
from utils.ts_utils import create_now_ts_ms
from utils.sequence_utils import find_instance_with_max_attr
from utils.alarm_utils import update_alarm_map
from utils.update_utils import set_attr_if_cond
from services.alarm_log import add_to_alarm_log
from services.app_log import add_to_app_log

logger = logging.getLogger("#appf_exec")


class AppFuncExecutor:
    def __init__(self, app: Application, app_func: AppFunction):
        self.app = app
        self.app_func = app_func
        self.update_map: UpdateMap = {
            "health": HealthGrades.OK,
            "alarm_payload": {},
            "is_catching_up": False,
            "cursor_ts": app.cursor_ts,
        }
        self.derived_df_reading_map: DerivedDfReadingMap = {}
        self.excep_health = HealthGrades.UNDEFINED
        self.health_from_app = HealthGrades.UNDEFINED
        self.cs_health = HealthGrades.UNDEFINED  # health based on the cursor timestamp

    def execute(self):

        # At first, all df readings are to be prepared
        # If there are too many df readings, the function 'prepare_df_readings'
        # will prepare them in batches
        if self.app.is_enabled:
            is_at_least_one_df_catching_up = self.create_df_readings()
            if is_at_least_one_df_catching_up:
                self.update_map["is_catching_up"] = True
                self.update_catching_up()
                self.app.save(update_fields=self.app.update_fields)
                logger.debug("App is catching up with df readings")
                logger.debug("--------------------END--------------------")  # NOTE: --> remove in 'monapps'
                return

        # when all df readings are prepared it is possible to execute the app function
        self.run_app_func()

    def create_df_readings(self):
        is_at_least_one_df_catching_up = False
        native_df_qs = self.app.get_native_df_qs()

        for nat_df in native_df_qs:
            try:
                creator = DfrCreator(self.app, nat_df)
                creator.execute()
                if creator.check_catching_up():
                    is_at_least_one_df_catching_up = True
            except Exception as e:
                # extract the file and the line from "traceback" to add to the message
                tb_list = traceback.extract_tb(e.__traceback__)
                original_frame = tb_list[-1]
                file = original_frame.filename
                line = original_frame.lineno
                s = f"Error while creating dfrs for {nat_df.pk} {nat_df.name}, file: {file}, line: {line}"
                add_to_alarm_log("ERROR", s, instance=self.app)
                logger.error(s)

        return is_at_least_one_df_catching_up

    # the call of this function is to be wrapped in transaction.atomic in Django
    def run_app_func(self):
        # In Django app, there will be
        # self.app = Application.objects.select_for_update().get(pk=self.app.pk)
        # self.parent = Asset.objects.select_for_update().get(pk=self.app.parent.pk)
        # self.task = PeriodicTask.objects.select_for_update().get(pk=self.task.pk)
        # and locking all datafeed objects related to the app with select_for_update() as well
        if self.app.is_enabled:
            self.run_exec_routine()

            try:
                self.save_derived_readings()
            except IntegrityError:
                s = "An attempt to rewrite existing df readings detected"
                add_to_alarm_log("ERROR", s, instance=self.app)
                logger.error(s)
                self.excep_health = HealthGrades.ERROR
                self.update_map["is_catching_up"] = False
            else:
                self.update_catching_up()
                self.update_cursor_pos()
                self.update_alarms()
            self.update_state()

        self.run_post_exec_routine()
        logger.debug("--------------------END--------------------")  # NOTE: --> remove in the 'monapps'

    def run_exec_routine(self):
        logger.debug("Starting app function")
        try:
            if isinstance(
                self.app.state, str
            ):  # NOTE: --> added just to check if the state is serializable, remove in the 'monapps'
                self.app.state = json.loads(
                    self.app.state
                )  # NOTE: --> added just to check if the state is serializable, remove in the 'monapps'

            self.app_func(self.app, self.derived_df_reading_map, self.update_map)
        except Exception as e:
            self.excep_health = HealthGrades.ERROR
            self.update_map["is_catching_up"] = False
            tb_list = traceback.extract_tb(e.__traceback__)
            original_frame = tb_list[-1]
            file = original_frame.filename
            line = original_frame.lineno
            add_to_alarm_log("ERROR", f"Error while executing app function, {e}", instance=self.app)
            logger.error(f"Error happened while executing app function, {e}, file: {file}, line: {line}")
        else:
            logger.debug("App function executed")

    # the call of this function is to be wrapped in transaction.atomic in Django
    def save_derived_readings(self):
        # Even if 'app_func' raised an exception, there may be some readings in
        # 'derived_df_reading_map' created before the exception. Try to save them

        for df_row in self.derived_df_reading_map.values():
            df = df_row["df"]
            new_df_readings = df_row["new_df_readings"]
            latest_dfr = find_instance_with_max_attr(new_df_readings)
            if latest_dfr is not None:  # the same as 'if len(new_df_readings) > 0'
                DfReading.objects.bulk_create(new_df_readings)
                logger.debug(f"New {len(new_df_readings)} df readings for '{df.name}' were saved")
                self.update_datafeed(df, latest_dfr)
                if df.name == STATUS_FIELD_NAME:
                    self.assign_new_cs_st_value(latest_dfr, "status")
                if df.name == CURR_STATE_FIELD_NAME:
                    self.assign_new_cs_st_value(latest_dfr, "curr_state")

    def update_datafeed(self, df, latest_dfr):
        max_rts = latest_dfr.time
        if set_attr_if_cond(max_rts, ">", df, "last_reading_ts"):
            df.save(update_fields=df.update_fields)
            # logger.debug(f"Datafeed '{df.name}' was updated")

    def assign_new_cs_st_value(self, latest_dfr, name: Literal["status", "curr_state"]):

        # when catching up, do not update status or curr_state, leave them frozen
        # it will help to avoid hitting parent assets too often
        if self.update_map.get("is_catching_up"):
            return

        if not set_attr_if_cond(latest_dfr.time, ">", self.app, f"last_{name}_update_ts"):
            return
        if not set_attr_if_cond(latest_dfr.value, "!=", self.app, name):
            return
        full_name = CURR_STATE_FIELD_NAME if name == "curr_state" else STATUS_FIELD_NAME
        add_to_alarm_log("INFO", f"{full_name} changed", instance=self.app)
        logger.debug(f"{full_name} changed -> : {latest_dfr.value}")

    def update_catching_up(self):
        if (is_catching_up := self.update_map.get("is_catching_up")) is None:
            return

        if not set_attr_if_cond(is_catching_up, "!=", self.app, "is_catching_up"):
            return

        if is_catching_up:
            # in the Django app there will be
            # self.task.interval = self.app.catch_up_interval
            # self.task.save()
            s = "Catching up started"
            add_to_alarm_log("INFO", s, instance=self.app)
            logger.debug(s)
        elif not is_catching_up:
            # in the Django app there will be
            # self.task.interval = self.app.invoc_interval
            # self.task.save()
            s = "Catching up finished"
            add_to_alarm_log("INFO", s, instance=self.app)
            logger.debug(s)

    def update_cursor_pos(self):
        if (ts := self.update_map.get("cursor_ts")) is None:
            return
        cursor_ts = ts
        if set_attr_if_cond(cursor_ts, ">", self.app, "cursor_ts"):
            logger.debug(f"Cursor position was updated -> {cursor_ts}")

    def update_alarms(self):
        if (alarm_payload := self.update_map.get("alarm_payload")) is None:
            return
        for ts, row in alarm_payload.items():
            error_dict = row.get("e")
            upd_error_map, _ = update_alarm_map(self.app, error_dict, ts, "errors", add_to_log=add_to_app_log)
            set_attr_if_cond(upd_error_map, "!=", self.app, "errors")

            warning_dict = row.get("w")
            upd_warning_map, _ = update_alarm_map(self.app, warning_dict, ts, "warnings", add_to_log=add_to_app_log)
            set_attr_if_cond(upd_warning_map, "!=", self.app, "warnings")

            app_infos_for_ts = row.get("i")
            if app_infos_for_ts is not None and isinstance(app_infos_for_ts, Iterable):
                for info_str in app_infos_for_ts:
                    add_to_app_log("INFO", info_str, ts=ts, instance=self.app)

    def update_state(self):
        if (state := self.update_map.get("state")) is None:
            return
        set_attr_if_cond(state, "!=", self.app, "state")

        self.app.state = json.dumps(
            state
        )  # NOTE: --> added just to check if the state is serializable, remove in the 'monapps'

    def run_post_exec_routine(self):
        logger.debug("Update other parameters")
        self.update_staleness("status")
        self.update_staleness("curr_state")
        self.update_health()

        self.app.save(update_fields=self.app.update_fields)

    def update_staleness(self, name: Literal["status", "curr_state"]):

        # when catching up, do not update status or curr_state, leave them frozen
        # it will help to avoid hitting parent assets too often
        if self.update_map.get("is_catching_up"):
            return

        full_name = CURR_STATE_FIELD_NAME if name == "curr_state" else STATUS_FIELD_NAME
        has = filter(lambda df: df.name == full_name, self.app.datafeeds.all())
        if not has:
            return
        last_update_ts = getattr(self.app, f"last_{name}_update_ts")
        time_stale = getattr(self.app, f"time_{name}_stale")
        now_ts = create_now_ts_ms()
        if last_update_ts is not None:
            is_stale = now_ts - last_update_ts > time_stale
        else:
            is_stale = now_ts - self.app.created_ts > time_stale

        if set_attr_if_cond(is_stale, "!=", self.app, f"is_{name}_stale"):
            if is_stale:
                s = f"{full_name} is stale"
                add_to_alarm_log("INFO", s, instance=self.app)
                logger.debug(s)
            else:
                s = f"{full_name} is not stale"
                add_to_alarm_log("INFO", s, instance=self.app)
                logger.debug(s)

    def eval_health_from_app(self):
        if (h := self.update_map.get("health")) is not None:
            # HealthGrades.OK is not used for this type of health
            self.health_from_app = h if h != HealthGrades.OK else HealthGrades.UNDEFINED

    def eval_cs_health(self):
        # health based on the cursor timestamp
        now_ts = create_now_ts_ms()
        if self.app.is_enabled:
            if now_ts - self.app.cursor_ts > self.app.time_health_error:
                self.cs_health = HealthGrades.ERROR
            else:
                self.cs_health = HealthGrades.OK

    def update_health(self):

        # when catching up, do not update health
        if self.update_map.get("is_catching_up"):
            return

        self.eval_health_from_app()
        self.eval_cs_health()

        health = max(self.cs_health, self.health_from_app, self.excep_health)

        if set_attr_if_cond(health, "!=", self.app, "health"):
            s = f"Health changed -> {health}"
            add_to_alarm_log("INFO", s, instance=self.app)
            logger.debug(s)

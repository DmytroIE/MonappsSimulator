import logging

from pydantic import BaseModel
from typing import TypeVar, Type, Generic

from classes.application import Application
from classes.datafeed import Datafeed
from classes.dfreading import DfReading
from common.complex_types import DerivedDfReadingMap, UpdateMap
from utils.app_func_utils import get_df_maps_from_app, get_end_rts
from app_functions.helpers.utils.df_utils import get_df_value_map, get_last_df_reading
from utils.ts_utils import create_grid
from app_functions.helpers.classes.app_func_settings_bundle import AppFuncSettingsBundle
from app_functions.helpers.utils.evaluate_formula import evaluate_formula

T = TypeVar("T", bound=BaseModel)


class AppFunction(Generic[T]):
    """
    A helper class to execute app functions. It is designed to be inherited by the actual app function implementation,
    which should override the necessary methods to implement the desired logic such as:
    - preparing custom variables before getting the 'df_value_map' (override '_prepare_before_getting_df_value_map')
    - preparing custom variables before the main loop (override '_prepare_custom_variables')
    - preparing custom variables at the beginning of each cycle (override '_prepare_cycle_variables')
    - executing the main logic while iterating over the grid (override '_calculate_within_cycle')
    - updating any additional outputs at the end of each cycle (override '_update_additional_outputs')

    The main purpose of this class is to provide a structured way to execute app functions,
    with a clear separation of different steps of the execution process and utility methods to handle
    common tasks such as getting datafeed values, preparing variables, and updating outputs.
    """

    def __init__(self, settings_model: Type[T]):
        self.settings_model: Type[T] = settings_model

    def __call__(
        self,
        app: Application,
        derived_df_reading_map: DerivedDfReadingMap,
        update_map: UpdateMap,
        logger: logging.Logger,
    ) -> None:
        self.app = app
        self.logger = logger
        self.derived_df_reading_map = derived_df_reading_map
        self.update_map = update_map
        self._get_df_maps()
        self._get_catching_up_and_end_rts()
        if self.end_rts <= self.start_rts:  # not all datafeed have readings with ts > cursor_ts
            self.logger.debug("Not all datafeed have readings with ts > cursor_ts. Exiting...")
            return
        self.settings_bundle: AppFuncSettingsBundle[T] = AppFuncSettingsBundle(self.app.settings, self.settings_model)
        # For most cases getting data one "time_resample" before the 'start_rts' is enough
        # to get 'previous value' for datafeeds with formulas. If needed, these values
        # can be altered in 'prepare_custom_variables' method.
        self.value_map_start_rts = self.start_rts - self.app.time_resample
        self.value_map_end_rts = self.end_rts
        self._prepare_before_getting_df_value_map()
        self.df_value_map = get_df_value_map(self.df_map.values(), self.value_map_start_rts, self.value_map_end_rts)
        self._prepare_service_variables()
        self._prepare_custom_variables()
        for self.rts in self.grid:
            self.one_step_alarm_payload = {self.rts: {}}
            self.app_settings_valid_from: T = self.settings_bundle.get_settings(self.rts)
            self._prepare_cycle_variables()
            self._calc_values_for_dfs_with_formulas()
            self._calculate_within_cycle()
            self._update_outputs()
            self._update_additional_outputs()

    def _get_df_maps(self):
        self.df_map = get_df_maps_from_app(self.app)
        [self.native_df_map, self.derived_df_map] = self.df_map.maps

        for df in self.derived_df_map.values():
            self.derived_df_reading_map[df.name] = {"df": df, "new_df_readings": []}

    def _get_catching_up_and_end_rts(self):
        # get end time
        self.start_rts = self.app.cursor_ts
        self.end_rts, self.is_catching_up = get_end_rts(
            self.native_df_map.values(), self.app.time_resample, self.start_rts, len(self.derived_df_map)
        )

    def _prepare_service_variables(self):
        self.alarm_payload = self.update_map.get("alarm_payload")

        # prepare a map for datafeeds with formulas
        self.df_with_formula_map = {}
        for df in self.derived_df_map.values():
            if "formula" not in df.formula:
                continue

            self.df_with_formula_map[df.name] = {"df": df, "last_value": None}
            # to get the last value, it is necessary to look first into the df_value_map
            if df.last_reading_ts is not None and df.last_reading_ts in self.df_value_map:
                row = self.df_value_map[df.last_reading_ts]
                if df.name in row:
                    self.df_with_formula_map[df.name]["last_value"] = row[df.name]
            else:
                last_dfr = get_last_df_reading(df)
                if last_dfr is not None:
                    self.df_with_formula_map[df.name]["last_value"] = last_dfr.value
                else:
                    # NOTE: it is arguable if the fallback should be 0
                    # but since the "last_value" is mostly used by totalizers, having no last value will just
                    # start the totalizer from 0 as expected
                    self.df_with_formula_map[df.name]["last_value"] = 0

        # creating the grid
        self.grid = create_grid(self.start_rts + self.app.time_resample, self.end_rts, self.app.time_resample)

    def _calc_values_for_dfs_with_formulas(self):
        for df_with_formula_row in self.df_with_formula_map.values():
            df: Datafeed = df_with_formula_row["df"]
            last_value = df_with_formula_row["last_value"]
            evaluate_formula(
                df,
                self.df_value_map,
                self.app_settings_valid_from.model_dump(),
                self.rts - self.app.time_resample,
                self.rts,
                last_value,
            )

    def _update_outputs(self):
        # sort the df_value_map by timestamp to make sure the readings are created in the right order
        self.df_value_map = dict(sorted(self.df_value_map.items()))
        for ts, row in self.df_value_map.items():
            if self.rts - self.app.time_resample < ts:
                if ts > self.rts:  # it shouldn't happen if all the calculations within a bin were done properly
                    break
                for df_name, value in row.items():
                    if df_name in self.derived_df_map:
                        df = self.derived_df_map[df_name]
                        dfr = DfReading(time=ts, value=value, datafeed=df)
                        self.derived_df_reading_map[df_name]["new_df_readings"].append(dfr)
                        if df_name in self.df_with_formula_map:
                            self.df_with_formula_map[df_name]["last_value"] = value

        # update app output
        self.update_map["cursor_ts"] = self.rts
        self.update_map["is_catching_up"] = self.is_catching_up

        for t, p in self.one_step_alarm_payload.items():
            if self.alarm_payload.get(t) is None:
                self.alarm_payload[t] = p
            else:
                self.alarm_payload[t].update(p)

    def _prepare_before_getting_df_value_map(self):
        """
        This method can be used to prepare custom variables before getting the 'df_value_map'.
        The default values for 'value_map_start_rts' and 'value_map_end_rts' are already set by this point
        (these values work for most cases). Override this method if you need to alter these values or set up
        any other variables before getting the 'df_value_map'."""
        pass

    def _prepare_custom_variables(self):
        """
        This method can be used to prepare custom variables before getting to the main cycle.
        The default implementation does nothing, but it can be overriden to set up any necessary
        variables or perform any necessary calculations before the main loop starts."""
        pass

    def _prepare_cycle_variables(self):
        """
        This method can be used to prepare custom variables at the beginning of each cycle.
        The default implementation does nothing, but it can be overridden to set up any necessary
        variables or perform any necessary calculations at the beginning of each cycle."""
        pass

    def _calculate_within_cycle(self):
        """
        This function should be overriden tocontain the logic that is exectuted while iterating over the grid.
        All new values for derived datafeeds created here should be stored in the 'df_value_map'
        under the corresponding timestamp and will be converted to 'DfReading' objects and added to the
        'derived_df_reading_map' at the end of each iteration. Unless needed, no exceptions should be
        supressed in this function, as it is important not to save new df readings and change 'cursor_ts'
        if something goes wrong during the calculations.
        """
        pass

    def _update_additional_outputs(self):
        """
        This method can be used to update any additional outputs (e.g. alarms) within the bin.
        The default implementation does nothing, but it can be overridden"""
        pass

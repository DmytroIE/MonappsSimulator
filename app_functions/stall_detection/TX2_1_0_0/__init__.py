__version__ = "TX2_1_0_0"

from .main import function
from .schemas import AppFuncSettingsModel, df_schema

package = {
    "function": function,
    "version": "TX2_1_0_0",
    "description": "Stall detection by means of two temperature sensors placed around the steam part of a heat exchanger",
    "df_schema": df_schema,
    "settings_jsonschema": AppFuncSettingsModel.model_json_schema(),
}

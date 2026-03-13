__version__ = "VER1_1_0_0"

from .main import function
from .schemas import AppFuncSettingsModel, df_schema

package = {
    "function": function,
    "version": "VER1_1_0_0",
    "description": "Fake data generation every 30 seconds based on predefined probabilities for testing purposes",
    "df_schema": df_schema,
    "settings_jsonschema": AppFuncSettingsModel.model_json_schema(),
}

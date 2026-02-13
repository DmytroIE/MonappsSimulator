__version__ = "SMW_TOT_1_0_0"

from .main import function
from .schemas import AppFuncSettingsModel, df_schema

package = {
    "function": function,
    "version": "SMW_TOT_1_0_0",
    "description": "Condensate return rate based on totalizer readings of steam and make-up water flowmeters",
    "df_schema": df_schema,
    "settings_jsonschema": AppFuncSettingsModel.model_json_schema(),
}

from pydantic import BaseModel, ConfigDict, Field
from app_functions.helpers.utils.constants import DEFAULT_TOT_RESET_VALUE

df_schema = {}


class AppFuncSettingsModel(BaseModel):

    model_config = ConfigDict(title="'Monitoring VER1 1.0.0' app function settings", extra="allow")

    int_tot_reset_value: float = Field(
        title="Totalizer reset value",
        default=DEFAULT_TOT_RESET_VALUE,
        gt=0.0,
        description="Reset value for internaly calculated totalizer readings",
    )

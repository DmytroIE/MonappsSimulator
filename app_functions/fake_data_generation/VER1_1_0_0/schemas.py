from pydantic import BaseModel, Field, ConfigDict

from common.constants import CURR_STATE_FIELD_NAME, STATUS_FIELD_NAME, DataAggTypes, VariableTypes

from .defaults import (
    default_prob_exeption,
)

df_schema = {
    CURR_STATE_FIELD_NAME: {"var_type": VariableTypes.NOMINAL, "agg_type": DataAggTypes.LAST},
    STATUS_FIELD_NAME: {"var_type": VariableTypes.NOMINAL, "agg_type": DataAggTypes.LAST},
}


class AppFuncSettingsModel(BaseModel):

    model_config = ConfigDict(title="'Fake data generation 1.0.0' app function settings", extra="allow")

    prob_exception: float = Field(
        title="Exception probability",
        default=default_prob_exeption,
        ge=0.0,
        le=1.0,
        description="Probability of generating an exception during fake data generation",
    )

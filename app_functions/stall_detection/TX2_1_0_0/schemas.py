from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

from common.constants import VariableTypes, DataAggTypes, STATUS_FIELD_NAME, CURR_STATE_FIELD_NAME

from app_functions.helpers.automatas.curr_state_type1 import (
    InternalState as CsInternalState,
)
from app_functions.helpers.automatas.status_type1 import InternalState as StInternalState, CondInitDict

from .defaults import (
    default_delta_temp,
    default_temp_in_threshold,
    default_cs_delay_trans_counts,
    default_temp_diff_error_threshold,
    default_undef_cid,
    default_ok_from_warn_cid,
    default_warn_cid,
    default_ok_from_undef_cid,
)

df_schema = {
    "Temp in": {"var_type": VariableTypes.CONTINUOUS, "agg_type": DataAggTypes.AVG},
    "Temp out": {"var_type": VariableTypes.CONTINUOUS, "agg_type": DataAggTypes.AVG},
    CURR_STATE_FIELD_NAME: {"var_type": VariableTypes.NOMINAL, "agg_type": DataAggTypes.LAST},
    STATUS_FIELD_NAME: {"var_type": VariableTypes.NOMINAL, "agg_type": DataAggTypes.LAST},
}


class AppFuncSettingsModel(BaseModel):

    model_config = ConfigDict(title="'Stall detection TX2 1.0.0' app function settings", extra="allow")

    delta_temp: float = Field(
        title="Delta T",
        default=default_delta_temp,
        gt=0.0,
        description="Temperature difference between inlet and outlet considered a stall condition",
    )
    temp_in_threshold: float = Field(
        title="ON/OFF threshold",
        default=default_temp_in_threshold,
        description="Inlet temperature ON/OFF threshold",
    )
    temp_diff_error_threshold: float = Field(
        title="T error threshold",
        default=default_temp_diff_error_threshold,
        gt=0.0,
        description="Difference between outlet and inlet temperature considered an error",
    )
    cs_delay_trans_counts: int = Field(
        title="CS delay trans counts",
        default=default_cs_delay_trans_counts,
        ge=0,
        description="""Delay between the occurrence of an event and the transition to \
a new current state expressed in numbers of the application 'time_resample'""",
    )
    undef_cid: CondInitDict = Field(
        default=default_undef_cid,
        title="""Condition for switching to UNDEFINED status""",
    )
    ok_from_warn_cid: CondInitDict = Field(
        default=default_ok_from_warn_cid,
        title="""Condition for switching from WARN to OK status""",
    )
    warn_cid: CondInitDict = Field(
        default=default_warn_cid,
        title="""Condition for switching to WARN status""",
    )
    ok_from_undef_cid: CondInitDict = Field(
        default=default_ok_from_undef_cid,
        title="""Condition for switching from UNDEFINED to OK status""",
    )


class AppState(BaseModel):
    all_occs: Optional[list] = None
    cs_automata_int_state: Optional[CsInternalState] = None
    st_automata_int_state: Optional[StInternalState] = None

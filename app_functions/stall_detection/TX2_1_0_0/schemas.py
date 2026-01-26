from pydantic import BaseModel
from typing import Optional, ClassVar

from common.constants import STATUS_FIELD_NAME, CURR_STATE_FIELD_NAME

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
    "Temp in": {"derived": False, "data_type": "Temperature"},
    "Temp out": {"derived": False, "data_type": "Temperature"},
    CURR_STATE_FIELD_NAME: {"derived": True, "data_type": CURR_STATE_FIELD_NAME},
    STATUS_FIELD_NAME: {"derived": True, "data_type": STATUS_FIELD_NAME},
}


class AppFuncSettingsModel(BaseModel):

    changeable_fields: ClassVar[set[str]] = {
        "delta_temp",
        "temp_in_threshold",
        "temp_diff_error_threshold",
    }

    delta_temp: float = default_delta_temp
    temp_in_threshold: float = default_temp_in_threshold
    temp_diff_error_threshold: float = default_temp_diff_error_threshold
    cs_delay_trans_counts: int = default_cs_delay_trans_counts
    undef_cid: CondInitDict = default_undef_cid
    ok_from_warn_cid: CondInitDict = default_ok_from_warn_cid
    warn_cid: CondInitDict = default_warn_cid
    ok_from_undef_cid: CondInitDict = default_ok_from_undef_cid


class AppState(BaseModel):
    all_occs: Optional[list] = None
    cs_automata_int_state: Optional[CsInternalState] = None
    st_automata_int_state: Optional[StInternalState] = None

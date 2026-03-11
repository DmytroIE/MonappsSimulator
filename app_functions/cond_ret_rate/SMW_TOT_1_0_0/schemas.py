from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app_functions.helpers.utils.constants import DEFAULT_TOT_RESET_VALUE
from common.constants import CURR_STATE_FIELD_NAME, STATUS_FIELD_NAME

from app_functions.helpers.automatas.status_type1 import InternalState as StInternalState, CondInitDict

from .defaults import (
    default_crr_warning_threshold,
    default_window_length_coef,
    default_min_window_length_coef,
    default_min_steam_gen_value,
    default_undef_cid,
    default_ok_from_warn_cid,
    default_warn_cid,
    default_ok_from_undef_cid,
)

df_schema = {
    "Condensate return rate": {"derived": True, "data_type": "Percentage"},
    CURR_STATE_FIELD_NAME: {"derived": True, "data_type": CURR_STATE_FIELD_NAME},
    STATUS_FIELD_NAME: {"derived": True, "data_type": STATUS_FIELD_NAME},
}


class AppFuncSettingsModel(BaseModel):

    model_config = ConfigDict(title="'Condensate return rate SMW_TOT 1.0.0' app function settings", extra="allow")

    crr_warning_threshold: float = Field(
        title="CRR warning threshold",
        default=default_crr_warning_threshold,
        ge=0.0,
        le=100.0,
        description="Threshold for the condensate return rate in percentage below which the current state will be WARN",
    )
    window_length_coef: float = Field(
        title="Window length coefficient",
        default=default_window_length_coef,
        ge=1.0,
        description="Window size experssed in fractions of the application 'time_resample'",
    )
    min_window_length_coef: float = Field(
        title="Min window length coefficient",
        default=default_min_window_length_coef,
        ge=0.5,
        description="Fraction of the window length that should have ovelapping totalizer readings",
    )
    min_steam_gen_value: float = Field(
        title="Min steam gen value",
        default=default_min_steam_gen_value,
        gt=0.0,
        description="""Minimal value of total steam in kg generated
        over the window period that allows to calculate the CRR""",
    )
    int_tot_reset_value: float = Field(
        title="Totalizer reset value",
        default=DEFAULT_TOT_RESET_VALUE,
        gt=0.0,
        description="Reset value for internaly calculated totalizer readings",
    )
    overlap_margin: int = Field(
        title="Overlap margin in ms",
        default=0,
        ge=0,
        description="Margin in ms for considering totalizer readings as overlapping",
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
        json_schema_extra={"changeable": False},
        title="""Condition for switching to WARN status""",
    )
    ok_from_undef_cid: CondInitDict = Field(
        default=default_ok_from_undef_cid,
        title="""Condition for switching from UNDEFINED to OK status""",
    )


class AppState(BaseModel):
    all_occs: Optional[list] = None
    st_automata_int_state: Optional[StInternalState] = None
    pass

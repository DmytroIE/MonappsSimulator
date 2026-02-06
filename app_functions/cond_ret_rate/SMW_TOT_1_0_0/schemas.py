from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

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
    "[Steam total <int>]": {"derived": False, "data_type": "Mass"},
    "[BdnValve <int> state]": {"derived": False, "data_type": "Binary state"},
    "Water total": {"derived": False, "data_type": "Mass"},
    "Temp out": {"derived": True, "data_type": "Temperature"},
    "Condensate return rate": {"derived": True, "data_type": "Percentage"},
    CURR_STATE_FIELD_NAME: {"derived": True, "data_type": CURR_STATE_FIELD_NAME},
    STATUS_FIELD_NAME: {"derived": True, "data_type": STATUS_FIELD_NAME},
}


class AppFuncSettingsModel(BaseModel):

    model_config = ConfigDict(title="'Condensate return rate SMW_TOT 1.0.0' app function settings")

    crr_warning_threshold: float = default_crr_warning_threshold
    window_length_coef: float = Field(
        title="Window length coefficient",
        default=default_window_length_coef,
        changeable=True,
        description="Window size experssed in fractions of the application 'time_resample'",
    )
    min_window_length_coef: float = Field(
        title="Min window length coefficient",
        default=default_min_window_length_coef,
        changeable=True,
        description="Fraction of the window length that should have ovelapping totalizer readings",
    )
    min_steam_gen_value: float = Field(
        title="Min steam gen value",
        default=default_min_steam_gen_value,
        changeable=True,
        description="""Minimal value of total steam in kg generated
        over the window period that allows to calculate the CRR""",
    )
    bvalve_kvs: list[float] = Field(
        title="Bvalve kvs",
        default_factory=list,
        changeable=True,
        description="List of Bvalve kvs",
    )
    undef_cid: CondInitDict = Field(
        default=default_undef_cid, changeable=False, title="""Condition for switching to UNDEFINED status"""
    )
    ok_from_warn_cid: CondInitDict = Field(
        default=default_ok_from_warn_cid, changeable=False, title="""Condition for switching from WARN to OK status"""
    )
    warn_cid: CondInitDict = Field(
        default=default_warn_cid, changeable=False, title="""Condition for switching to WARN status"""
    )
    ok_from_undef_cid: CondInitDict = Field(
        default=default_ok_from_undef_cid,
        changeable=False,
        title="""Condition for switching from UNDEFINED to OK status""",
    )


class AppState(BaseModel):
    all_occs: Optional[list] = None
    st_automata_int_state: Optional[StInternalState] = None
    pass

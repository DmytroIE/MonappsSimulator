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
    "[Steam total <str>]": {"derived": False, "data_type": "Mass total"},
    "[Water total <str>]": {"derived": False, "data_type": "Mass total"},
    "[Bdn valve state <str>]": {"derived": False, "data_type": "Binary state"},
    "[Bdn temp <str>]": {"derived": False, "data_type": "Temperature"},
    "[Bdn water total <str>]": {"derived": True, "data_type": "Mass total"},
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
        ge=1.0,
        json_schema_extra={"changeable": True},
        description="Window size experssed in fractions of the application 'time_resample'",
    )
    min_window_length_coef: float = Field(
        title="Min window length coefficient",
        default=default_min_window_length_coef,
        ge=0.5,
        json_schema_extra={"changeable": True},
        description="Fraction of the window length that should have ovelapping totalizer readings",
    )
    min_steam_gen_value: float = Field(
        title="Min steam gen value",
        default=default_min_steam_gen_value,
        gt=0.0,
        json_schema_extra={"changeable": True},
        description="""Minimal value of total steam in kg generated
        over the window period that allows to calculate the CRR""",
    )
    bdn_water_tot_reset_value: float = Field(
        title="Bdn water tot reset value",
        default=100000.0,
        gt=0.0,
        json_schema_extra={"changeable": True},
        description="Blowdown water totalizer reset value",
    )
    bdn_valve_kvs: dict[str, float] = Field(
        title="Bdn valve kvs",
        default_factory=dict,
        json_schema_extra={"changeable": True},
        description="Blowdown valve kv values",
    )
    bdn_temp_subst_values: dict[str, float] = Field(
        title="Bdn temp subst values",
        default_factory=dict,
        json_schema_extra={"changeable": True},
        description="Blowdown temperature substituted values",
    )
    steam_tot_weights: dict[str, float] = Field(
        title="Steam totalizer weights",
        default_factory=dict,
        json_schema_extra={"changeable": True},
        description="Pulse weights for steam totalizers",
    )
    water_tot_weights: dict[str, float] = Field(
        title="Water totalizer weights",
        default_factory=dict,
        json_schema_extra={"changeable": True},
        description="Pulse weights for water totalizers",
    )
    undef_cid: CondInitDict = Field(
        default=default_undef_cid,
        json_schema_extra={"changeable": False},
        title="""Condition for switching to UNDEFINED status""",
    )
    ok_from_warn_cid: CondInitDict = Field(
        default=default_ok_from_warn_cid,
        json_schema_extra={"changeable": False},
        title="""Condition for switching from WARN to OK status""",
    )
    warn_cid: CondInitDict = Field(
        default=default_warn_cid,
        json_schema_extra={"changeable": False},
        title="""Condition for switching to WARN status""",
    )
    ok_from_undef_cid: CondInitDict = Field(
        default=default_ok_from_undef_cid,
        json_schema_extra={"changeable": False},
        title="""Condition for switching from UNDEFINED to OK status""",
    )


class AppState(BaseModel):
    all_occs: Optional[list] = None
    st_automata_int_state: Optional[StInternalState] = None
    pass

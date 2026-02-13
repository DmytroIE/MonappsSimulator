from classes.application import Application, AppType
from classes.datastream import Datastream
from classes.datafeed import Datafeed
from common.constants import STATUS_FIELD_NAME, CURR_STATE_FIELD_NAME


from test_apps.ready_to_use_items import (
    datatype_temp,
    datatype_mass_total,
    degC_meas_unit,
    kg_meas_unit,
    percent_meas_unit,
    datatype_percentage,
    datatype_binary_state,
    curr_state_datatype,
    status_datatype,
)

# --------------------------------------

ds_bdn_temp_1 = Datastream(
    name="Temperature",
    data_type=datatype_temp,
    meas_unit=degC_meas_unit,
    is_rbe=False,
    max_rate_of_change=0.5,
    max_plausible_value=250.0,
    min_plausible_value=-50.0,
    time_change=240000,
)
ds_bdn_temp_1.save()

ds_steam_tot_1 = Datastream(
    name="Steam total",
    data_type=datatype_mass_total,
    meas_unit=kg_meas_unit,
    is_rbe=False,
    max_plausible_value=4294967296,  # 4 bytes
    min_plausible_value=0,
    time_change=180000,
)
ds_steam_tot_1.save()

ds_water_tot_1 = Datastream(
    name="Water total",
    data_type=datatype_mass_total,
    meas_unit=kg_meas_unit,
    is_rbe=False,
    max_plausible_value=4294967296,  # 4 bytes
    min_plausible_value=0,
    time_change=180000,
)
ds_water_tot_1.save()

ds_bdn_vlv_1_state = Datastream(
    name="Digital input",
    data_type=datatype_binary_state,
    meas_unit=None,
    is_rbe=True,
)
ds_bdn_vlv_1_state.save()


app_type = AppType(
    name="Condensate return rate",
    func_name="cond_ret_rate",
)
app_type.save()

app_settings = {
    "crr_warning_threshold": 75.0,
    "window_length_coef": 1.5,
    "min_window_length_coef": 0.8,
    "min_steam_gen_value": 8,
    "bdn_water_tot_reset_value": 4.5,
    "bdn_valve_kvs": {"Boiler 1": 0.002},
    "steam_tot_weights": {"Workshop 1": 1.0},
    "water_tot_weights": {"Boilerhouse": 1.0},
    "undef_cid": {
        "total_occs": 5,
        "ok_cond": "==",
        "num_of_ok_occs": 0,
        "warn_cond": "==",
        "num_of_warn_occs": 0,
        "undef_cond": ">=",
        "num_of_undef_occs": 0,
    },
    "ok_from_warn_cid": {
        "total_occs": 4,
        "ok_cond": ">=",
        "num_of_ok_occs": 3,
        "warn_cond": "==",
        "num_of_warn_occs": 0,
        "undef_cond": ">=",
        "num_of_undef_occs": 0,
    },
    "warn_cid": {
        "total_occs": 3,
        "ok_cond": ">=",
        "num_of_ok_occs": 0,
        "warn_cond": ">=",
        "num_of_warn_occs": 2,
        "undef_cond": ">=",
        "num_of_undef_occs": 0,
    },
    "ok_from_undef_cid": {
        "total_occs": 1,
        "ok_cond": ">=",
        "num_of_ok_occs": 1,
        "warn_cond": "==",
        "num_of_warn_occs": 0,
        "undef_cond": ">=",
        "num_of_undef_occs": 0,
    },
}

app = Application(
    type=app_type,
    app_settings=app_settings,
    time_resample=600000,
    func_version="SMW_TOT 1.0.0",
    cursor_ts=1766239200000,
)
app.save()

df_steam_tot_1 = Datafeed(
    name="Steam total Workshop 1",
    parent=app,
    datastream=ds_steam_tot_1,
    data_type=datatype_mass_total,
    meas_unit=kg_meas_unit,
    is_rest_on=True,
    time_resample=60000,
)
df_steam_tot_1.save()

df_water_tot_1 = Datafeed(
    name="Water total Boilerhouse",
    parent=app,
    datastream=ds_water_tot_1,
    data_type=datatype_mass_total,
    meas_unit=kg_meas_unit,
    is_rest_on=True,
    time_resample=60000,
)
df_water_tot_1.save()

df_bdn_vlv_1_state = Datafeed(
    name="Bdn valve state Boiler 1",
    parent=app,
    datastream=ds_bdn_vlv_1_state,
    data_type=datatype_binary_state,
    meas_unit=None,
    is_rest_on=True,
    time_resample=60000,
)
df_bdn_vlv_1_state.save()

df_bdn_temp_1 = Datafeed(
    name="Bdn temp Boiler 1",
    parent=app,
    datastream=ds_bdn_temp_1,
    data_type=datatype_temp,
    meas_unit=degC_meas_unit,
    is_rest_on=True,
    time_resample=60000,
)
df_bdn_temp_1.save()

df_bdn_water_mass_1 = Datafeed(
    name="Bdn water total Boiler 1",
    parent=app,
    datastream=None,
    data_type=datatype_mass_total,
    meas_unit=kg_meas_unit,
    time_resample=60000,
)
df_bdn_water_mass_1.save()

df_cond_ret_rate = Datafeed(
    name="Cond return rate",
    parent=app,
    datastream=None,
    data_type=datatype_percentage,
    meas_unit=percent_meas_unit,
)
df_cond_ret_rate.save()

df_curr_state = Datafeed(
    name=CURR_STATE_FIELD_NAME,
    parent=app,
    datastream=None,
    data_type=curr_state_datatype,
    meas_unit=None,
)
df_curr_state.save()

df_status = Datafeed(
    name=STATUS_FIELD_NAME,
    parent=app,
    datastream=None,
    data_type=status_datatype,
    meas_unit=None,
)
df_status.save()

graph_settings = {
    "y_min": 0,
    "y_max": 250,
    "num_grid_counts": 12,
    "time_unit": "1 min",
}

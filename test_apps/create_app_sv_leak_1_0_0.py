from classes.application import Application, AppType
from classes.datastream import Datastream
from classes.datafeed import Datafeed
from common.constants import STATUS_FIELD_NAME, CURR_STATE_FIELD_NAME


from test_apps.ready_to_use_items import datatype_temp, degC_meas_unit, curr_state_datatype, status_datatype

# --------------------------------------

ds_temp_1 = Datastream(
    name="Temperature 1",
    data_type=datatype_temp,
    meas_unit=degC_meas_unit,
    is_rbe=False,
    is_totalizer=False,
    max_rate_of_change=0.1,
    max_plausible_value=250.0,
    min_plausible_value=-50.0,
    time_change=240000,
)
ds_temp_1.save()

ds_temp_2 = Datastream(
    name="Temperature 2",
    data_type=datatype_temp,
    meas_unit=degC_meas_unit,
    is_rbe=False,
    is_totalizer=False,
    max_rate_of_change=0.1,
    max_plausible_value=250.0,
    min_plausible_value=-50.0,
    time_change=240000,
)
ds_temp_2.save()

app_type = AppType(
    name="SV leak detection",
    func_name="sv_leak_detection_by_two_temps",
)
app_type.save()

app_settings = {
    "temp_out_threshold": 70.0,
    "temp_in_threshold": 100.0,
    "cs_trans_counts": 3,
    "undef_cond": {
        "total_occs": 6,
        "ok_cond": "==",
        "num_of_ok_occs": 0,
        "warn_cond": "==",
        "num_of_warn_occs": 0,
        "undef_cond": ">=",
        "num_of_undef_occs": 6,
    },
    "ok_from_warn_cond": {
        "total_occs": 6,
        "num_of_undef_occs": 0,
        "undef_cond": ">=",
        "num_of_ok_occs": 3,
        "ok_cond": ">=",
        "num_of_warn_occs": 0,
        "warn_cond": "==",
    },
    "warn_cond": {
        "total_occs": 5,
        "ok_cond": ">=",
        "num_of_ok_occs": 0,
        "warn_cond": ">=",
        "num_of_warn_occs": 3,
        "undef_cond": ">=",
        "num_of_undef_occs": 0,
    },
    "ok_from_undef_cond": {
        "total_occs": 4,
        "ok_cond": ">=",
        "num_of_ok_occs": 2,
        "warn_cond": "==",
        "num_of_warn_occs": 0,
        "undef_cond": ">=",
        "num_of_undef_occs": 0,
    },
}

app = Application(
    type=app_type,
    app_settings=app_settings,
    time_resample=60000,
    func_version="1.0.0",
    cursor_ts=1742479200000,
)
app.save()

df_temp_inlet = Datafeed(
    name="Temp in",
    parent=app,
    datastream=ds_temp_1,
    data_type=datatype_temp,
    meas_unit=degC_meas_unit,
    is_rest_on=True,
)
df_temp_inlet.save()

df_temp_outlet = Datafeed(
    name="Temp out",
    parent=app,
    datastream=ds_temp_2,
    data_type=datatype_temp,
    meas_unit=degC_meas_unit,
    is_rest_on=True,
)
df_temp_outlet.save()

df_curr_state = Datafeed(
    name=CURR_STATE_FIELD_NAME, parent=app, datastream=None, data_type=curr_state_datatype, meas_unit=None
)
df_curr_state.save()

df_status = Datafeed(name=STATUS_FIELD_NAME, parent=app, datastream=None, data_type=status_datatype, meas_unit=None)
df_status.save()

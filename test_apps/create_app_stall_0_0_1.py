from classes.application import Application, AppType
from classes.datastream import Datastream
from classes.datafeed import Datafeed
from common.constants import CURR_STATE_FIELD_NAME


from test_apps.ready_to_use_items import datatype_temp, degC_meas_unit, curr_state_datatype


ds_temp_1 = Datastream(
    name="Temperature 1",
    data_type=datatype_temp,
    meas_unit=degC_meas_unit,
    is_rbe=False,
    is_totalizer=False,
    max_rate_of_change=0.5,
    max_plausible_value=150.0,
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
    max_rate_of_change=0.3,
    max_plausible_value=150.0,
    min_plausible_value=-50.0,
    time_change=240000,
)
ds_temp_2.save()

app_type = AppType(
    name="Stall detection",
    func_name="stall_detection_by_two_temps",
)
app_type.save()

app = Application(
    type=app_type,
    app_settings={"delta_t_in": 10.0, "delta_t_out": 5.0, "t_delay_ms": 300000},
    time_resample=60000,
    func_version="0.0.1",
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
    name=CURR_STATE_FIELD_NAME,
    parent=app, datastream=None,
    data_type=curr_state_datatype,
    meas_unit=None,
)
df_curr_state.save()

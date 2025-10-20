from classes.application import Application, AppType
from classes.datastream import Datastream
from classes.datafeed import Datafeed
from common.constants import AugmentationPolicy
from utils.ts_utils import get_floored_now_ts
from test_apps.ready_to_use_items import (
    datatype_temp,
    degC_meas_unit,
    datatype_clicks,
    datatype_clicks_total,
    datatype_work_state,
)


ds_clicks_1 = Datastream(
    name="Clicks 1",
    data_type=datatype_clicks,
    meas_unit=None,
    is_rbe=True,
    max_plausible_value=1,
    min_plausible_value=0,
    till_now_margin=60000,
)
ds_clicks_1.save()

ds_clicks_tot_1 = Datastream(
    name="Clicks total 1",
    data_type=datatype_clicks_total,
    meas_unit=None,
    is_rbe=False,
    max_plausible_value=1000000000,
    min_plausible_value=0,
    time_change=240000,  # to test the restoration algorithm
)
ds_clicks_tot_1.save()

ds_pump_state_1 = Datastream(
    name="Pump state 1",
    data_type=datatype_work_state,
    meas_unit=None,
    is_rbe=True,
    max_plausible_value=1,
    min_plausible_value=0,
    till_now_margin=60000,
)
ds_pump_state_1.save()

ds_temp_1 = Datastream(
    name="Temperature 1",
    data_type=datatype_temp,
    meas_unit=degC_meas_unit,
    is_rbe=False,
    max_rate_of_change=0.5,
    max_plausible_value=150.0,
    min_plausible_value=-50.0,
    time_change=240000,
)
ds_temp_1.save()

app_type = AppType(
    name="Monitoring",
    func_name="monitoring",
)
app_type.save()

time_resample = 60000
app = Application(
    type=app_type,
    app_settings={},
    time_resample=time_resample,
    func_version="1.0.0",
    cursor_ts=get_floored_now_ts(time_resample),
)
app.save()

df_clicks = Datafeed(
    name="Clicks",
    parent=app,
    datastream=ds_clicks_1,
    data_type=datatype_clicks,
    meas_unit=None,
    is_aug_on=True,
    aug_policy=AugmentationPolicy.TILL_NOW,
)
df_clicks.save()

df_clicks_total = Datafeed(
    name="Clicks total",
    parent=app,
    datastream=ds_clicks_tot_1,
    data_type=datatype_clicks_total,
    meas_unit=None,
    is_rest_on=True,
)
df_clicks_total.save()

df_pump_state = Datafeed(
    name="Pump state",
    parent=app,
    datastream=ds_pump_state_1,
    data_type=datatype_work_state,
    meas_unit=None,
    is_aug_on=True,
    aug_policy=AugmentationPolicy.TILL_NOW,
)
df_pump_state.save()

df_temp = Datafeed(
    name="Temperature",
    parent=app,
    datastream=ds_temp_1,
    data_type=datatype_temp,
    meas_unit=degC_meas_unit,
    is_rest_on=True,
)
df_temp.save()

from classes.application import Application, AppType
from classes.datafeed import Datafeed
from common.constants import STATUS_FIELD_NAME, CURR_STATE_FIELD_NAME
from utils.ts_utils import get_floored_now_ts

from test_apps.ready_to_use_items import curr_state_datatype, status_datatype

# --------------------------------------


app_type = AppType(
    name="Fake data generator",
    func_name="fake_data_generator",
)
app_type.save()

app_settings = {
    "prob_exeption": 0.2,
    "prob_calc_omitted": 0.2,
    "prob_error": 0.2,
    "prob_warning": 0.5,
}

time_resample = 30000
app = Application(
    type=app_type,
    app_settings=app_settings,
    time_resample=time_resample,
    func_version="1.0.0",
    time_status_stale=240000,
    time_curr_state_stale=120000,
    time_health_error=120000,
    cursor_ts=get_floored_now_ts(time_resample),
)
app.save()

df_curr_state = Datafeed(
    name=CURR_STATE_FIELD_NAME,
    parent=app, datastream=None,
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

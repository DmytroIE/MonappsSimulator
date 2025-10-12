from classes.datatype import DataType, MeasUnit
from common.constants import (
    DataAggrTypes,
    VariableTypes,
    StatusTypes,
    CurrStateTypes,
    CURR_STATE_FIELD_NAME,
    STATUS_FIELD_NAME,
)

datatype_temp = DataType("Temperature", agg_type=DataAggrTypes.AVG, var_type=VariableTypes.CONTINUOUS)
datatype_temp.save()
datatype_clicks = DataType("Clicks", agg_type=DataAggrTypes.SUM, var_type=VariableTypes.DISCRETE)
datatype_clicks.save()
datatype_work_state = DataType(
    "Work state",
    agg_type=DataAggrTypes.LAST,
    var_type=VariableTypes.NOMINAL,
    category_map={
        0: "OFF",
        1: "ON",
    },
)
datatype_work_state.save()

degC_meas_unit = MeasUnit("Degree Celsius", "*C", datatype_temp)
degC_meas_unit.save()

status_datatype = DataType(
    STATUS_FIELD_NAME,
    agg_type=DataAggrTypes.LAST,
    var_type=VariableTypes.DISCRETE,
    category_map={
        StatusTypes.UNDEFINED: "Undefined",
        StatusTypes.OK: "OK",
        StatusTypes.WARNING: "Warning",
        StatusTypes.ERROR: "Error",
    },
)

curr_state_datatype = DataType(
    CURR_STATE_FIELD_NAME,
    agg_type=DataAggrTypes.LAST,
    var_type=VariableTypes.DISCRETE,
    category_map={
        CurrStateTypes.UNDEFINED: "Undefined",
        CurrStateTypes.OK: "OK",
        CurrStateTypes.WARNING: "Warning",
        CurrStateTypes.ERROR: "Error",
    },
)

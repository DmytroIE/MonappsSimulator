from classes.datatype import DataType, MeasUnit
from common.constants import (
    DataAggTypes,
    VariableTypes,
    StatusTypes,
    CurrStateTypes,
    CURR_STATE_FIELD_NAME,
    STATUS_FIELD_NAME,
)

datatype_temp = DataType("Temperature", agg_type=DataAggTypes.AVG, var_type=VariableTypes.CONTINUOUS)
datatype_temp.save()
datatype_clicks = DataType("Clicks", agg_type=DataAggTypes.SUM, var_type=VariableTypes.DISCRETE)
datatype_clicks.save()
datatype_clicks_total = DataType(
    "Clicks total", agg_type=DataAggTypes.SUM, var_type=VariableTypes.DISCRETE, is_totalizer=True
)
datatype_clicks_total.save()
datatype_work_state = DataType(
    "Work state",
    agg_type=DataAggTypes.LAST,
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
    agg_type=DataAggTypes.LAST,
    var_type=VariableTypes.DISCRETE,
    category_map={
        StatusTypes.UNDEFINED: "Undefined",
        StatusTypes.OK: "OK",
        StatusTypes.WARNING: "Warning",
        StatusTypes.ERROR: "Error",
    },
)
status_datatype.save()

curr_state_datatype = DataType(
    CURR_STATE_FIELD_NAME,
    agg_type=DataAggTypes.LAST,
    var_type=VariableTypes.DISCRETE,
    category_map={
        CurrStateTypes.UNDEFINED: "Undefined",
        CurrStateTypes.OK: "OK",
        CurrStateTypes.WARNING: "Warning",
        CurrStateTypes.ERROR: "Error",
    },
)
curr_state_datatype.save()

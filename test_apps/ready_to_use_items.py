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
datatype_binary_state = DataType(
    "Binary state",
    agg_type=DataAggTypes.LAST,
    var_type=VariableTypes.NOMINAL,
    category_map={
        0: "OFF",
        1: "ON",
    },
)
datatype_binary_state.save()

degC_meas_unit = MeasUnit("Degree Celsius", "*C", [datatype_temp])
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

datatype_mass = DataType("Mass", agg_type=DataAggTypes.SUM, var_type=VariableTypes.CONTINUOUS, is_totalizer=False)
datatype_mass.save()

datatype_mass_total = DataType(
    "Mass total", agg_type=DataAggTypes.SUM, var_type=VariableTypes.CONTINUOUS, is_totalizer=True
)
datatype_mass_total.save()

kg_meas_unit = MeasUnit(
    "Kilogram", "kg", [datatype_mass, datatype_mass_total]
)  # imitation of 'many to many' relationship
kg_meas_unit.save()

datatype_percentage = DataType(
    "Percentage", agg_type=DataAggTypes.AVG, var_type=VariableTypes.CONTINUOUS, is_totalizer=False
)
datatype_percentage.save()

percent_meas_unit = MeasUnit(
    "Percent", "%", [datatype_percentage]
)  # imitation of 'many to many' relationship
percent_meas_unit.save()

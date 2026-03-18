from typing import NotRequired, TypedDict, Literal, Any, Callable
from classes.application import Application
from classes.dfreading import DfReading
from classes.datafeed import Datafeed
from common.constants import HealthGrades


type DfReadingMap = dict[int, dict[int, DfReading]]
type DfValueMap = dict[int, dict[str, int | float]]
type IndDfReadingMap = dict[int, DfReading]

type AlarmPayloadDictForTs = dict[str, Any]  # can be {"CPU Error": {"st": "in"}} or {"CPU Error": {} - can be anything}
type ReevalFields = Literal["status", "curr_state", "health"]


class AlarmRecord(TypedDict):
    persist: bool
    st: Literal["in", "out"]
    lastTransTs: int
    lastInPayloadTs: int


class AlarmMap(TypedDict):  # is stored inside an app, a datastream or a device
    errors: dict[str, AlarmRecord]
    warnings: dict[str, AlarmRecord]


class UpdateMap(TypedDict):
    cursor_ts: int
    is_catching_up: bool
    health: HealthGrades
    alarm_payload: dict
    state: NotRequired[dict]


class DerivedDfReadingRow(TypedDict):
    df: Datafeed
    new_df_readings: list[DfReading]


type DerivedDfReadingMap = dict[str, DerivedDfReadingRow]

type AppFunction = Callable[[Application, DerivedDfReadingMap, UpdateMap], None]


class AppFuncBundle(TypedDict):
    function: AppFunction
    version: str
    description: str
    df_schema: dict[
        str, dict[str, Any]
    ]  # df_name -> {"data_type": DataType, "agg_type": DataAggTypes, "is_totalizer": bool (only for sum agg type)}
    settings_jsonschema: dict

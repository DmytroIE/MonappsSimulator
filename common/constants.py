from enum import IntEnum
from datetime import datetime, timezone
from typing import NamedTuple


STATUS_FIELD_NAME = "Status"
CURR_STATE_FIELD_NAME = "Current state"


class StatusTypes(IntEnum):
    UNDEFINED = 0
    OK = 1
    WARNING = 2
    ERROR = 3


class CurrStateTypes(IntEnum):
    UNDEFINED = 0
    OK = 1
    WARNING = 2
    ERROR = 3


class HealthGrades(IntEnum):
    UNDEFINED = 0
    OK = 1
    WARNING = 2
    ERROR = 3


# https://inforiver.com/insights/continuous-discrete-categorical-axis-difference/
class VariableTypes(IntEnum):
    CONTINUOUS = 0
    DISCRETE = 1
    NOMINAL = 3  # categorical
    ORDINAL = 4  # categorical


class DataAggrTypes(IntEnum):
    AVG = 0  # not available for categorical and discrete data
    SUM = 1  # not available for categorical data
    LAST = 2  # can be used for cat. data that represents a certain state
    MAX = 3  # not available for categorical data
    MIN = 4  # not available for categorical data
    MODE = 5  # for categorical data only


class NotToUseDfrTypes(IntEnum):
    SPLINE_NOT_TO_USE = 1
    UNCLOSED = 2
    SPLINE_UNCLOSED = 3


class AugmentationPolicy(IntEnum):
    TILL_LAST_DF_READING = 1
    TILL_NOW = 2


NO_ATTR = "No Attr"


class DjangoAppSettings(NamedTuple):  # mocking django 'settings' object
    NUM_MAX_DFREADINGS_TO_PROCESS: int
    NUM_MAX_DSREADINGS_TO_PROCESS: int
    MIN_TIME_RESOL_MS: int
    MIN_TIME_APP_FUNC_INVOC_MS: int
    MAX_TS_MS: int


# MAX_TS_MS = 32503679999999, to be used as something similar to Infinity for timestamps
MAX_DT = datetime(2999, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)
settings = DjangoAppSettings(
    NUM_MAX_DFREADINGS_TO_PROCESS=8,  # deliberately set so low to see how catching up works
    NUM_MAX_DSREADINGS_TO_PROCESS=6,  # deliberately set so low to see how catching up works
    MIN_TIME_RESOL_MS=1000,
    MIN_TIME_APP_FUNC_INVOC_MS=60000,
    MAX_TS_MS=int(MAX_DT.timestamp() * 1000),
)


class AllowedIntervalsMs(IntEnum):
    ONE_SEC = 1000
    FIVE_SECS = 5000
    TEN_SECS = 10000
    HALF_MIN = 30000
    MIN = 60000
    FIVE_MIN = 300000
    TEN_MIN = 600000
    HALF_HOUR = 1800000
    HOUR = 3600000
    DAY = 86400000


DEFAULT_TIME_RESAMPLE = AllowedIntervalsMs.MIN
DEFAULT_TIME_STATUS_STALE = AllowedIntervalsMs.DAY * 15
DEFAULT_TIME_CURR_STATE_STALE = AllowedIntervalsMs.TEN_MIN
DEFAULT_TIME_APP_HEALTH_ERROR = AllowedIntervalsMs.TEN_MIN


class IntegrityError(Exception):
    pass

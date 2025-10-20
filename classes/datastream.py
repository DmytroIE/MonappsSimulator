from typing import Self
from classes.datatype import DataType, MeasUnit
from classes.object_manager import ObjectManager
from common.constants import VariableTypes
from utils.ts_utils import create_now_ts_ms


class Datastream:
    objects = ObjectManager["Datastream"]()
    id_counter = 0

    def __init__(
        self: Self,
        name: str,
        data_type: DataType,
        meas_unit: MeasUnit | None = None,
        is_rbe: bool = False,
        max_rate_of_change: float = 1.0,
        max_plausible_value: float = 1000000.0,
        min_plausible_value: float = -1000000.0,
        time_change: int | None = None,
        till_now_margin: int = 0,
    ) -> None:

        self.name = name
        self.data_type = data_type
        self.meas_unit = meas_unit
        self.is_rbe = is_rbe
        # NOTE: till_now_margin is applicable only for rbe datastreams
        self.till_now_margin = till_now_margin

        self.time_change = time_change

        self.max_rate_of_change = max_rate_of_change  # units per second, can't be <= 0
        self.max_plausible_value = max_plausible_value  # should be > min_plausible_value
        self.min_plausible_value = min_plausible_value  # should be < max_plausible_value

        self.ts_to_start_with = 0
        self.last_reading_ts: int | None = None
        self.created_ts = create_now_ts_ms()

        Datastream.id_counter += 1
        self.id = Datastream.id_counter
        self.pk = self.id
        self.update_fields = set()

    @property
    def is_value_interger(self) -> bool:
        return self.data_type.var_type != VariableTypes.CONTINUOUS

    def __repr__(self) -> str:
        return f"Datastream {self.pk} {self.name}"

    def save(self, update_fields=None) -> None:
        Datastream.objects.add_item(self)
        self.update_fields = set()

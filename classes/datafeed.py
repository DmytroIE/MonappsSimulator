from typing import Any, Self
from classes.application import Application
from classes.datastream import Datastream
from classes.datatype import DataType, MeasUnit
from common.constants import VariableTypes, AugmentationPolicy
from classes.object_manager import ObjectManager


class Datafeed:
    objects = ObjectManager["Datafeed"]()
    id_counter = 0

    def __init__(
        self: Self,
        name: str,
        parent: Application,
        datastream: Datastream | None,
        data_type: DataType,
        meas_unit: MeasUnit | None = None,
        is_rest_on: bool = True,
        is_aug_on: bool = True,
        aug_policy: AugmentationPolicy = AugmentationPolicy.TILL_LAST_DF_READING,
        time_resample: int | None = None,
        formula: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.data_type = data_type
        self.meas_unit = meas_unit

        self.is_rest_on = is_rest_on
        self.is_aug_on = is_aug_on
        self.aug_policy = aug_policy
        self.ts_to_start_with = 0
        self.last_reading_ts: int | None = None

        self.parent = parent
        self.datastream = datastream

        if time_resample is not None:
            # datafeeds can have 'time_resample' smaller than the app 'time_resample',
            # but it should be a divisor of the app 'time_resample'
            modulo = parent.time_resample % time_resample
            if modulo > 0:
                raise ValueError("App time resample should be a multiple of the df time resample")
        self.db_time_resample = time_resample
        if datastream is None:
            # only derived dfs can have formula
            self.formula = formula if formula is not None else {}
        else:
            self.formula = {}

        Datafeed.id_counter += 1
        self.id = Datafeed.id_counter
        self.pk = self.id
        self.update_fields = set()

        self.parent.datafeeds.add_item(self)  # imitation of the backward relation

    def __repr__(self) -> str:
        return f"Datafeed {self.pk} {self.name}"

    @property
    def is_value_interger(self) -> bool:
        return self.data_type.var_type != VariableTypes.CONTINUOUS

    @property
    def time_resample(self) -> int:
        if self.db_time_resample is None:
            return self.parent.time_resample
        return self.db_time_resample

    def save(self, update_fields=None) -> None:
        Datafeed.objects.add_item(self)
        self.update_fields = set()

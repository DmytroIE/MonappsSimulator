from typing import Self
from classes.application import Application
from classes.datastream import Datastream
from classes.datatype import DataType, MeasUnit
from common.constants import VariableTypes, AugmentationPolicy
from classes.object_manager import ObjectManager
from utils.ts_utils import create_now_ts_ms


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
        return self.parent.time_resample

    def save(self, update_fields=None) -> None:
        Datafeed.objects.add_item(self)
        self.update_fields = set()

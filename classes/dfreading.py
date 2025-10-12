from datetime import datetime, timezone
from classes.object_manager import ObjectManager
from classes.datafeed import Datafeed
from common.constants import NotToUseDfrTypes


class DfReading:
    objects = ObjectManager["DfReading"]()

    def __init__(self, time: int, value: float | int, datafeed: Datafeed, restored: bool = False) -> None:

        self.datafeed = datafeed
        self.pk = (time, datafeed.id)

        self.time = time
        self.db_value = float(value)
        self.restored = restored
        self.not_to_use: None | NotToUseDfrTypes = None

    @property
    def value(self) -> float | int:
        if self.datafeed.is_value_interger:
            return int(self.db_value)
        else:
            return self.db_value

    @value.setter
    def value(self, value: float | int) -> None:
        if self.datafeed.is_value_interger:
            self.db_value = round(value, 0)
        else:
            self.db_value = value

    def __repr__(self) -> str:
        dt = datetime.fromtimestamp(self.time / 1000, tz=timezone.utc)
        if self.datafeed.is_value_interger:
            return f"<DFR df:{self.datafeed.pk} ts:{dt} val: {self.value} {'R' if self.restored else ''} {self.not_to_use.value if self.not_to_use is not None else ''}>"
        else:
            return f"<DFR df:{self.datafeed.pk} ts:{dt} val: {self.value:.3f} {'R' if self.restored else ''} {self.not_to_use.value if self.not_to_use is not None else ''}>"

    def save(self, update_fields=None) -> None:
        DfReading.objects.add_item(self)

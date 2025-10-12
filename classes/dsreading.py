from datetime import datetime, timezone
from classes.object_manager import ObjectManager
from classes.datastream import Datastream


class AnyDsReading:
    def __init__(self, time: int, value: float, datastream: Datastream) -> None:
        self.pk = (time, datastream.id)
        self.time = time
        self.db_value = float(value)
        self.datastream = datastream
        self.short_name = ""

    @property
    def value(self) -> float | int:
        if self.datastream.is_value_interger:
            return int(self.db_value)
        else:
            return self.db_value

    @value.setter
    def value(self, value: float | int) -> None:
        if self.datastream.is_value_interger:
            self.db_value = round(value, 0)
        else:
            self.db_value = value

    def __repr__(self):
        dt = datetime.fromtimestamp(self.time / 1000, tz=timezone.utc)
        if self.datastream.is_value_interger:
            return f"{self.short_name} ds:{self.datastream.pk} ts:{dt} val: {self.value}"
        else:
            return f"{self.short_name} ds:{self.datastream.pk} ts:{dt} val: {self.value:.3f}"


class AnyNoDataMarker:

    def __init__(self, time: int, datastream: Datastream) -> None:
        self.pk = (time, datastream.id)
        self.time = time
        self.datastream = datastream
        self.short_name = ""

    def __repr__(self):
        dt = datetime.fromtimestamp(self.time / 1000, tz=timezone.utc)
        return f"{self.short_name} ds:{self.datastream.pk} ts:{dt}"


class DsReading(AnyDsReading):
    objects = ObjectManager["DsReading"]()

    short_name = "DSR"

    def save(self, update_fields=None) -> None:
        DsReading.objects.add_item(self)


class UnusedDsReading(AnyDsReading):
    objects = ObjectManager["UnusedDsReading"]()

    short_name = "Unused DSR"

    def save(self, update_fields=None) -> None:
        UnusedDsReading.objects.add_item(self)


class InvalidDsReading(AnyDsReading):
    objects = ObjectManager["InvalidDsReading"]()

    short_name = "Invalid DSR"

    def save(self, update_fields=None) -> None:
        InvalidDsReading.objects.add_item(self)


class NonRocDsReading(AnyDsReading):
    objects = ObjectManager["NonRocDsReading"]()

    short_name = "Non-ROC DSR"

    def save(self, update_fields=None) -> None:
        NonRocDsReading.objects.add_item(self)


class NoDataMarker(AnyNoDataMarker):
    objects = ObjectManager["NoDataMarker"]()

    short_name = "NDM"

    def save(self, update_fields=None) -> None:
        NoDataMarker.objects.add_item(self)


class UnusedNoDataMarker(AnyNoDataMarker):
    objects = ObjectManager["UnusedNoDataMarker"]()

    short_name = "Unused NDM"

    def save(self, update_fields=None) -> None:
        UnusedNoDataMarker.objects.add_item(self)

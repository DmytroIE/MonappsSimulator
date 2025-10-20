from typing import Dict
from classes.object_manager import ObjectManager
from common.constants import VariableTypes, DataAggrTypes


class DataType:
    objects = ObjectManager["DataType"]()
    id_counter = 0

    def __init__(
        self,
        name: str,
        agg_type: DataAggrTypes = DataAggrTypes.AVG,
        var_type: VariableTypes = VariableTypes.CONTINUOUS,
        category_map: Dict[int, str] = {},
        is_totalizer: bool = False,
    ) -> None:

        self.name = name
        self.agg_type = agg_type
        self.var_type = var_type
        self.category_map = category_map

        # NOTE: works only with agg_type = SUM
        self.is_totalizer = is_totalizer

        DataType.id_counter += 1
        self.id = DataType.id_counter
        self.pk = self.id

    def __repr__(self) -> str:
        return f"Datatype {self.name}"

    def save(self, update_fields=None) -> None:
        DataType.objects.add_item(self)


class MeasUnit:
    objects = ObjectManager["MeasUnit"]()
    id_counter = 0

    def __init__(self, name: str, symbol: str, data_type: DataType, k=1.0, b=0.0) -> None:

        self.name = name
        self.symbol = symbol
        self.data_type = data_type
        self.k = k
        self.b = b

        MeasUnit.id_counter += 1
        self.id = MeasUnit.id_counter
        self.pk = self.id

    def __repr__(self) -> str:
        return f"MeasUnit {self.name}"

    def to_base_unit(self, value):
        return self.k * value + self.b

    def save(self, update_fields=None) -> None:
        MeasUnit.objects.add_item(self)

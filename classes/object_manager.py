# Emulation of Django's object manager
from datetime import datetime
from typing import Dict, List, Generic, TypeVar, Self
from common.constants import IntegrityError

T = TypeVar("T")

filter_op_map = {
    "gte": ">=",
    "lte": "<=",
    "gt": ">",
    "lt": "<",
}


def parse_filter_condition(filter_condition, filter_value) -> str:
    arr = filter_condition.split("__")
    new_arr = []
    for i, s in enumerate(arr):
        if i == len(arr) - 1:
            if s in filter_op_map:
                new_arr.append(filter_op_map[s])
            elif s == "isnull":
                if filter_value:
                    new_arr.append(" is None ")
                else:
                    new_arr.append(" is not None ")
                return "".join(new_arr)
            else:
                new_arr.append(f".{s}==")
        else:
            new_arr.append(f".{s}")
    new_line = "".join(new_arr)

    if isinstance(filter_value, datetime):
        new_line += f"{filter_value.timestamp()}"
    else:
        new_line += str(filter_value)
    return new_line


class QuerySet(Generic[T]):
    def __init__(self, object_manager: "ObjectManager[T]", items: List[T] | None = None) -> None:
        self._om = object_manager
        self._items: List[T] = items or []
        self._counter = 0

    def filter(self, **kwargs) -> "QuerySet[T]":
        cond_arr = []
        for k, v in kwargs.items():
            cond_arr.append(f"item{parse_filter_condition(k, v)}")
        full_cond_str = " and ".join(cond_arr)

        new_items = []
        full_cond_eval_str = f"""
for item in self._items:
    if {full_cond_str}:
        new_items.append(item)
        """

        exec(full_cond_eval_str)
        # self._items = new_items

        # return self
        return QuerySet(self._om, new_items)

    def order_by(self, field) -> "QuerySet[T]":
        rev = False
        if field[0] == "-":
            field = field[1:]
            rev = True
        new_items = sorted(self._items, key=lambda x: getattr(x, field), reverse=rev)
        return QuerySet(self._om, new_items)

    def first(self) -> T | None:
        try:
            return self._items[0]
        except IndexError:
            return None

    def last(self) -> T | None:
        try:
            return self._items[-1]
        except IndexError:
            return None

    def count(self) -> int:
        return len(self._items)

    def delete(self) -> None:
        for item in self._items:
            self._om.delete_item(item)

    def __iter__(self) -> Self:
        self._counter = 0
        return self

    def __next__(self) -> T:
        if self._counter < len(self._items):
            self._counter += 1
            return self._items[self._counter - 1]
        raise StopIteration

    def __getitem__(self, i) -> "List[T]":
        return self._items[i]
        # return self._items.__getitem__(i)

    def __repr__(self) -> str:
        return "\n".join([x.__str__() for x in self._items])


class ObjectManager(Generic[T]):
    def __init__(self, items: Dict[str, T] | None = None) -> None:
        self._items: Dict[str, T] = items or {}

    def add_item(self, item) -> None:
        self._items[item.pk] = item  # We don't interact with a real db

    def delete_item(self, item) -> None:
        del self._items[item.pk]

    def all(self) -> QuerySet[T]:
        return QuerySet[T](self, list(self._items.values()))

    def __call__(self) -> QuerySet[T]:
        return self.all()

    def filter(self, **kwargs) -> QuerySet[T]:
        return self.all().filter(**kwargs)

    def order_by(self, field) -> QuerySet[T]:
        return self.all().order_by(field)

    def count(self) -> int:
        return self.all().count()

    # https://docs.djangoproject.com/en/5.1/ref/models/querysets/#bulk-create
    def bulk_create(
        self,
        objs,
        batch_size=None,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None,
    ) -> None:
        for obj in objs:
            if obj.pk in self._items and not update_conflicts:
                raise IntegrityError(f"Object with pk {obj.pk} already exists")
        for obj in objs:  # add objects only if no integrity errors were raised
            self._items[obj.pk] = obj

    def bulk_update(self, objs, fields) -> None:
        # for simplicity this method is implemented for ObjectManager, not for Queryset
        pass
        # nothing to do here, the object will already have some fields changed,
        # we don't really interact with a database, so nothing else to do

from pydantic import BaseModel, ValidationError
from typing import ClassVar, TypeVar, Type

T = TypeVar("T", bound=BaseModel)


class AppFuncSettingsBundle[T]:
    def __init__(self, settings_dict: dict, settings_model: Type[T]) -> None:

        initial_settings: T = settings_model(**settings_dict)
        self._storage: dict[int, T] = {0: initial_settings}

        changes = settings_dict.get("changes", {})
        if len(changes) == 0 or not isinstance(changes, dict):
            return

        if not hasattr(settings_model, "changeable_fields"):
            return

        changeable_fields = settings_model.changeable_fields

        ranked_changed_settings = {}
        for key, ch_dict in changes.items():
            try:
                ts = int(key)  # if 'key' is coerceable to 'int', then it is a timestamp
                if isinstance(ch_dict, dict):
                    ranked_changed_settings[ts] = {k: v for k, v in ch_dict.items() if k in changeable_fields}
            except ValueError:
                pass  # other values will be ignored

        ranked_changed_settings = dict(sorted(ranked_changed_settings.items()))

        updated = initial_settings
        for ts, d in ranked_changed_settings.items():
            try:
                updated = settings_model.model_validate(updated.__dict__ | d)
            except ValidationError:
                # print(f"Invalid settings: {d}")
                pass
            else:
                updated = updated.model_copy(update=d)
                self._storage[ts] = updated

    def get_settings(self, ts: int = 0) -> T:
        settings = self._storage[0]
        if ts > 0:
            for t, s in self._storage.items():
                if t <= ts:
                    settings = s
                else:
                    break
        return settings


if __name__ == "__main__":

    class AfsModel(BaseModel):
        changeable_fields: ClassVar[list[str]] = ["a"]

        a: int
        b: int
        c: int

    ob = AppFuncSettingsBundle(
        {
            "a": 1,
            "b": 2,
            "c": 3,
            "changes": {
                "2234": {"a": 4, "b": 5, "c": 6},
                "aaa": {"bbb": "ccc"},
                "1456": {"a": 25, "c": "fff"},
                "3333": {"a": "g"},
            },
        },
        AfsModel,
    )
    print(ob)
    print(ob.get_settings())
    print(ob.get_settings(1000))
    print(ob.get_settings(2000))
    print(ob.get_settings(3000))

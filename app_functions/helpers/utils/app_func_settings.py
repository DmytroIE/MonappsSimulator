from typing import Self


class AppFuncSettings:
    def __init__(self, squahed_settings: dict[int, dict]):
        sorted_dict = dict(sorted(squahed_settings.items()))
        prev_ts = None
        for ts, settings in sorted_dict.items():
            if prev_ts is not None:
                sorted_dict[ts] = {**sorted_dict[prev_ts], **settings}
            prev_ts = ts
        self.__sorted_dict = sorted_dict

    def get_settings_valid_from(self: Self, valid_from_ts: int) -> dict | None:
        # find the max timestamp among all keys smaller than valid_from_ts
        try:
            ts = max(k for k in self.__sorted_dict.keys() if k <= valid_from_ts)
            return self.__sorted_dict[ts]
        except (ValueError, TypeError):
            return None

    def __repr__(self) -> str:
        return f"AppFuncSettings({self.__sorted_dict})"

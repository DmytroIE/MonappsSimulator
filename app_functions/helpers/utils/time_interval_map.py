class TimeIntervalMap:
    """
    A map of time intervals. The key is the start of the interval (timestamp expressed in ms)
    and the value is the end of the interval. Looks like
    {1741111111111: 1742222222222, 1743333333333: 1744444444444, ...}"""

    def __init__(self, init_map: dict[int, int] | None = None) -> None:
        if init_map is not None:
            self.map = TimeIntervalMap.condition_map(init_map)
        else:
            self.map: dict[int, int] = {}

    def __str__(self) -> str:
        s = "Time Interval Map: ["
        for start_ts, end_ts in self.map.items():
            s += f"({start_ts}:{end_ts}),"
        s += "]"
        return s

    @staticmethod
    def condition_map(map: dict[int, int]) -> dict[int, int]:
        if len(map) == 0:
            return {}

        map_inter = {}
        for start_ts, end_ts in map.items():
            if start_ts > end_ts:  # if start_ts > end_ts within the same interval, just omit
                start_ts, end_ts = end_ts, start_ts
            map_inter[start_ts] = end_ts

        map_inter = dict(sorted(map_inter.items()))

        prev_int_start_ts = 0
        prev_int_end_ts = 0
        new_map = {}
        for idx, (int_start_ts, int_end_ts) in enumerate(map_inter.items()):
            if int_start_ts > int_end_ts:  # if start_ts > end_ts within the same interval, just omit
                continue
            # if there are overlapping intevals, then "glue" them together
            if idx > 0:  # at least two items
                if prev_int_end_ts >= int_start_ts:  # if end_ts of the previous interval >= start_ts of the current
                    prev_int_end_ts = max(prev_int_end_ts, int_end_ts)
                    new_map[prev_int_start_ts] = prev_int_end_ts
                    continue
            new_map[int_start_ts] = int_end_ts
            prev_int_start_ts = int_start_ts
            prev_int_end_ts = int_end_ts

        return new_map

    def get_info_for_interval(self, ts1: int, ts2: int) -> tuple[int, int]:
        start_ts = min(ts1, ts2)
        end_ts = max(ts1, ts2)
        total_duration = 0
        num_of_occurrences = 0
        for int_start_ts, int_end_ts in self.map.items():
            if int_start_ts > end_ts or int_end_ts < start_ts:
                continue
            if int_start_ts < start_ts:
                int_start_ts = start_ts
            if int_end_ts > end_ts:
                int_end_ts = end_ts
            total_duration += int_end_ts - int_start_ts
            num_of_occurrences += 1
        return total_duration, num_of_occurrences

    def delete_old_intervals(self, end_ts: int) -> None:
        new_map = {}
        for int_start_ts, int_end_ts in self.map.items():
            if int_end_ts < end_ts:  # the unclosed interval is not deleted in any case
                continue
            new_map[int_start_ts] = int_end_ts
        self.map = new_map

    def add_interval(self, ts1: int, ts2: int) -> None:
        start_ts = min(ts1, ts2)
        end_ts = max(ts1, ts2)
        if start_ts in self.map:
            new_map = {**self.map}
            new_map[start_ts] = max(self.map[start_ts], end_ts)  # if start_ts is already in the map, update end_ts
        else:
            new_map = {**self.map, start_ts: end_ts}
        self.map = TimeIntervalMap.condition_map(new_map)

    def get_last_end_ts(self) -> int | None:
        if len(self.map) == 0:
            return None
        return max(self.map.values())


if __name__ == "__main__":
    test_maps: list[dict[int, int] | None] = [None for _ in range(6)]
    test_maps[0] = {123456: 234567}
    test_maps[1] = {123456: 234567, 234000: 345678}  # a wrong map, intervals overlap
    test_maps[2] = {234567: 123456}  # a wrong map - the start is greater than the end
    test_maps[3] = {123456: 234566, 234567: 345677, 345678: 456788, 456789: 567890}
    test_maps[4] = {123456: 234567, 234567: 345678}  # a wrong map, intervals overlap
    test_maps[5] = {123456: 234567, 345678: 567890, 234000: 345677}  # a wrong map, intervals overlap

    for test_map in test_maps:
        print(TimeIntervalMap(test_map))

    print("---Adding an overlapping interval---")
    test_map = TimeIntervalMap(test_maps[5])
    print("Initial map")
    print(test_map)
    test_map.add_interval(345677, 456788)
    print("After adding 345677:456788")
    print(test_map)

    print("---Adding an interval within an existing interval---")
    test_map = TimeIntervalMap(test_maps[3])
    print("Initial map")
    print(test_map)
    test_map.add_interval(234567, 234568)
    print("After adding 234567:234568")
    print(test_map)

    print("---Adding an overlapping interval---")
    test_map = TimeIntervalMap(test_maps[3])
    print("Initial map")
    print(test_map)
    test_map.add_interval(234566, 234568)
    print("After adding 234566:234568")
    print(test_map)

    print("---Deleting old intervals---")
    test_map = TimeIntervalMap(test_maps[3])
    print("Initial map")
    print(test_map)
    test_map.delete_old_intervals(345800)
    print("After deleting old intervals with end_ts < 345800")
    print(test_map)

    print("---Getting info for an interval---")
    test_map = TimeIntervalMap(test_maps[3])
    print("Initial map")
    print(test_map)
    print("test_map.get_info_for_interval(234500, 345678) = ", test_map.get_info_for_interval(234500, 345679))

    print("---Getting info for an interval---")
    test_map = TimeIntervalMap({180000: 100000, 150000: 200000, 300000: 400000, 600000: 500000, 700000: 800000})
    print("Initial map")
    print(test_map)
    print("test_map.get_info_for_interval(150000, 500000) = ", test_map.get_info_for_interval(500000, 150000))

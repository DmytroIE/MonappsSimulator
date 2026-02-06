from classes.datafeed import Datafeed
from common.complex_types import DfValueMap


def straighten_tot_readings(ordered_value_map: DfValueMap, df_name: str) -> None:

    if len(ordered_value_map) == 0:
        return

    base = 0
    prev_value = None

    for ts, line in ordered_value_map.items():
        value = line.get(df_name)
        if value is None:
            continue

        if value < 0:
            value = 0  # fool protection from negative values

        if prev_value is None:
            prev_value = value

        if prev_value > value:  # it means that the totalizer was reset between tho timestamps
            base = base + prev_value

        ordered_value_map[ts][df_name] = base + value
        prev_value = value


def get_boundaries_of_overlapping_tot_readings(df_value_map: DfValueMap, tot_dfs: list[Datafeed], margin_ms: int = 0):
    tot_df_boundary_value_map = {df.name: {"left_val": 0, "right_val": 0} for df in tot_dfs}
    tot_df_names = set(tot_df_boundary_value_map.keys())

    timestamps = list(df_value_map.keys())
    if len(timestamps) == 0:
        return None

    left_boundary_ts = None
    right_boundary_ts = None
    for idx, ts in enumerate(timestamps):
        # finding the left values
        lines_whithin_pos_margin = []
        t = ts
        i = idx
        while t <= ts + margin_ms:
            lines_whithin_pos_margin.append(df_value_map[t])
            i += 1
            if i == len(timestamps):
                break
            t = timestamps[i]
        # go backwards and merge lines
        resulting_left_line = {}
        for line in reversed(lines_whithin_pos_margin):
            resulting_left_line.update(line)

        # checking if all tot df names in the resulting line
        resulting_left_line_tot_df_names = set(resulting_left_line.keys())
        if len(tot_df_names - resulting_left_line_tot_df_names) == 0:
            left_boundary_ts = ts
            for df_name in tot_df_names:
                tot_df_boundary_value_map[df_name]["left_val"] = resulting_left_line[df_name]
            break

    # finding the right values
    timestamps = list(reversed(timestamps))
    for idx, ts in enumerate(timestamps):
        lines_whithin_neg_margin = []
        t = ts
        i = idx
        while t >= ts - margin_ms:
            lines_whithin_neg_margin.append(df_value_map[t])
            i += 1
            if i == len(timestamps):
                break
            t = timestamps[i]
        # go backwards and merge lines
        resulting_right_line = {}
        for line in reversed(lines_whithin_neg_margin):
            resulting_right_line.update(line)

        # checking if all tot df names in the resulting line
        resulting_right_line_tot_df_names = set(resulting_right_line.keys())
        if len(tot_df_names - resulting_right_line_tot_df_names) == 0:
            right_boundary_ts = ts
            for df_name in tot_df_names:
                tot_df_boundary_value_map[df_name]["right_val"] = resulting_right_line[df_name]
            break

    if left_boundary_ts is None or right_boundary_ts is None:
        return None

    return left_boundary_ts, right_boundary_ts, tot_df_boundary_value_map

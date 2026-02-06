from classes.datafeed import Datafeed


def get_datafeeds_of_series(df_map: dict[str, Datafeed], series_name: str) -> list[Datafeed]:
    dfs: list[Datafeed] = []

    while True:
        df = df_map.get(series_name.format(len(dfs) + 1))
        if df is None:
            break
        dfs.append(df)

    return dfs

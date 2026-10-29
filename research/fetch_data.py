"""Download history for strategy research into data/ (run on GitHub Actions; Yahoo is free)."""
from pathlib import Path

import pandas as pd

from agent import config as C
from agent import data

OUT = Path(__file__).resolve().parent.parent / "data"


def save(frames, name):
    rows = [df.assign(symbol=s) for s, df in frames.items()]
    pd.concat(rows).rename_axis("ts").to_csv(OUT / f"{name}.csv.gz", compression="gzip")
    print(name, len(frames), "symbols", sum(len(r) for r in rows), "rows")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    syms = list(C.UNIVERSE) + [C.INDEX]
    save(data.intraday(syms, interval="5m", period="60d"), "bars_5m")
    save(data.intraday(syms, interval="15m", period="60d"), "bars_15m")
    save(data.intraday(syms, interval="60m", period="730d"), "bars_60m")
    save(data.daily(syms + list(C.GLOBAL_CUES) + [C.INDIA_VIX], period="10y"), "bars_1d")

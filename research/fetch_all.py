"""Download history for EVERY NSE equity (series EQ) for research. Runs on GitHub Actions.

Writes data/nse_equity_list.csv, data/daily_all_*.csv.gz (10y daily) and
data/m5_liquid_*.csv.gz (60d 5-min bars for the more liquid names).
"""
import io
import time
from pathlib import Path

import pandas as pd
import requests

from agent import data

OUT = Path(__file__).resolve().parent.parent / "data"
NSE_LIST = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
      "Accept": "text/csv,*/*", "Referer": "https://www.nseindia.com/"}


def nse_list():
    r = requests.get(NSE_LIST, headers=UA, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = df.columns.str.strip()
    df = df[df["SERIES"].str.strip() == "EQ"]
    return df


def batched(tickers, n, **kw):
    out = {}
    for i in range(0, len(tickers), n):
        part = tickers[i:i + n]
        out.update(data._split(data._download(part, **kw), part))
        print(f"{kw.get('interval')}: {min(i + n, len(tickers))}/{len(tickers)} fetched, have {len(out)}", flush=True)
        time.sleep(2)
    return out


def save(frames, name, per_file):
    syms = sorted(frames)
    for k in range(0, len(syms), per_file):
        rows = [frames[s].round(2).assign(symbol=s) for s in syms[k:k + per_file]]
        pd.concat(rows).rename_axis("ts").to_csv(OUT / f"{name}_{k // per_file:02d}.csv.gz", compression="gzip")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    lst = nse_list()
    lst.to_csv(OUT / "nse_equity_list.csv", index=False)
    tickers = [s.strip() + ".NS" for s in lst["SYMBOL"]]
    print("NSE EQ symbols:", len(tickers))
    daily = batched(tickers + ["^NSEI"], 100, interval="1d", period="10y")
    save(daily, "daily_all", 300)
    # 5-min history only exists for 60 days; fetch it for names trading >= Rs 10 crore/day
    adv = {s: (df["close"] * df["volume"]).tail(20).mean() for s, df in daily.items()}
    liquid = sorted(s for s, v in adv.items() if v >= 1e8) + ["^NSEI"]
    print("liquid (>= Rs 10cr/day):", len(liquid))
    m5 = batched(liquid, 50, interval="5m", period="60d")
    save(m5, "m5_liquid", 200)

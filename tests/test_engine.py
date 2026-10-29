"""Mechanics tests on synthetic data (no internet). They prove the plumbing works,
not that the strategy makes money - that is what the backtest is for."""
from datetime import date, datetime

import numpy as np
import pandas as pd

from agent import config as C
from agent.backtest import simulate_day
from agent.broker import charges
from agent.engine import Engine, new_day

DAY = date(2026, 10, 27)


def bars(path, start="09:15"):
    idx = pd.date_range(f"{DAY} {start}", periods=len(path), freq="5min", tz=C.IST)
    c = np.array(path, float)
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) + 0.3, "low": np.minimum(o, c) - 0.3,
                         "close": c, "volume": 1000.0}, index=idx)


def daily(close):
    idx = pd.date_range("2026-10-20", periods=5, freq="D", tz=C.IST).normalize()
    return pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1e6}, index=idx)


def run(stock_path, index_path, prev=1000.0, index_prev=20000.0):
    return simulate_day(DAY, 100_000, {"AAA.NS": bars(stock_path)}, bars(index_path),
                        {"AAA.NS": daily(prev), C.INDEX: daily(index_prev)})


WEAK_INDEX = [19950 + i for i in range(75)]        # NIFTY opens -0.25%
STRONG_INDEX = [20100 + i for i in range(75)]      # NIFTY opens +0.5%


def test_charges_reasonable():
    # Rs 1 lakh round trip intraday costs ~Rs 82 at Zerodha (40 brokerage + 25 STT + fees + GST)
    assert 80 < charges(100_000, 100_000) < 85


def test_gap_up_on_weak_market_is_shorted_and_fades():
    path = [1020 - 0.2 * i for i in range(75)]      # opens +2%, drifts down all day
    eng = run(path, WEAK_INDEX)
    assert len(eng.closed) == 1
    t = eng.closed[0]
    assert t["side"] == "SHORT" and t["exit_reason"].startswith("square-off")
    assert t["qty"] * t["entry"] <= 100_000 * C.MAX_POSITION_X * 1.01
    assert 0 < t["net"] < t["gross"]


def test_stop_loss_caps_the_loss():
    path = [1020 + 0.5 * i for i in range(75)]      # gap keeps running up
    t = run(path, WEAK_INDEX).closed[0]
    assert t["exit_reason"] == "stop-loss"
    assert -0.0115 * t["qty"] * t["entry"] - t["charges"] < t["net"] < 0


def test_no_trade_when_market_opens_up():
    eng = run([1020 - 0.2 * i for i in range(75)], STRONG_INDEX)
    assert not eng.closed and eng.day["halt_reason"].startswith("no setup")


def test_no_trade_on_small_gap():
    eng = run([1005 - 0.2 * i for i in range(75)], WEAK_INDEX)
    assert not eng.closed


def test_daily_loss_limit_and_square_off():
    ctx = {"prev_close": {}}
    eng = Engine(100_000, new_day(DAY, ctx))
    eng.day["entered"] = True
    eng.broker.open("AAA.NS", -1, 1000, 1000, 2000, 0, datetime(2026, 10, 27, 10, tzinfo=C.IST), "t",
                    "2026-10-27T10:00:00+05:30")
    b = bars([1008], start="10:05")
    eng.step(datetime(2026, 10, 27, 10, 10, tzinfo=C.IST), {"AAA.NS": b}, {"AAA.NS": 1008.0}, {}, None)
    assert eng.day["halted"] and not eng.broker.positions  # -8000 beyond the 7000 backstop
    eng2 = Engine(100_000, new_day(DAY, ctx))
    eng2.day["entered"] = True
    eng2.broker.open("AAA.NS", -1, 10, 1000, 1100, 0, datetime(2026, 10, 27, 10, tzinfo=C.IST), "t",
                     "2026-10-27T10:00:00+05:30")
    eng2.step(datetime(2026, 10, 27, 15, 10, tzinfo=C.IST), {"AAA.NS": b}, {"AAA.NS": 997.0}, {}, None)
    assert eng2.closed[0]["exit_reason"].startswith("square-off")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("PASS", name)

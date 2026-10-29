"""Mechanics tests on synthetic data (no internet). They prove the plumbing works,
not that the strategy makes money - that is what the backtest is for."""
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from agent import config as C
from agent.backtest import simulate_day
from agent.broker import charges
from agent.engine import Engine, new_day

DAY = date(2026, 10, 27)


def bars(path, vols, start="09:15"):
    idx = pd.date_range(f"{DAY} {start}", periods=len(path), freq="5min", tz=C.IST)
    c = np.array(path, float)
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) + 0.3, "low": np.minimum(o, c) - 0.3,
                         "close": c, "volume": vols}, index=idx)


def daily(atr=20.0, n=30):
    idx = pd.date_range(DAY - timedelta(days=n), periods=n, freq="D", tz=C.IST).normalize()
    c = np.full(n, 1000.0)
    return pd.DataFrame({"open": c, "high": c + atr / 2, "low": c - atr / 2, "close": c, "volume": 1e6}, index=idx)


def flat_index(n):
    return bars([20000 + 2 * i for i in range(n)], [0] * n)


def test_charges_reasonable():
    # Rs 1 lakh round trip intraday costs ~Rs 82 at Zerodha (40 brokerage + 25 STT + fees + GST)
    assert 80 < charges(100_000, 100_000) < 85


def test_breakout_long_hits_target():
    # flat opening range ~1000, breakout on volume at bar 4, then steady rally
    path = [1000, 1001, 1000, 1004] + [1004 + 3 * i for i in range(1, 71)]
    vols = [1000, 1000, 1000, 5000] + [1500] * 70
    eng = simulate_day(DAY, 100_000, {"AAA.NS": bars(path, vols)}, flat_index(74),
                       {"AAA.NS": daily()}, {})
    assert eng.closed, "expected a trade"
    t = eng.closed[0]
    assert t["side"] == "LONG" and t["exit_reason"] in ("target", "profit lock")
    assert t["net"] > 0 and t["net"] < t["gross"]


def test_stop_loss_limits_damage():
    path = [1000, 1001, 1000, 1004] + [1004 - 2 * i for i in range(1, 71)]
    vols = [1000, 1000, 1000, 5000] + [1500] * 70
    eng = simulate_day(DAY, 100_000, {"AAA.NS": bars(path, vols)}, flat_index(74),
                       {"AAA.NS": daily()}, {})
    t = eng.closed[0]
    assert t["exit_reason"] == "stop"
    assert t["net"] > -C.RISK_PER_TRADE * 100_000 * 1.5  # loss ~ planned risk + costs/slippage


def test_no_trade_without_volume():
    path = [1000, 1001, 1000, 1004] + [1004 + 3 * i for i in range(1, 71)]
    eng = simulate_day(DAY, 100_000, {"AAA.NS": bars(path, [1000] * 74)}, flat_index(74),
                       {"AAA.NS": daily()}, {})
    assert not eng.closed


def test_daily_loss_limit_and_square_off():
    eng = Engine(100_000, new_day(DAY, {"atr": {}}))
    eng.broker.open("AAA.NS", 1, 1000, 1000, 900, 1200, datetime(2026, 10, 27, 10, tzinfo=C.IST), "t",
                    "2026-10-27T10:00:00+05:30")
    b = bars([997], [100], start="10:05")
    eng.step(datetime(2026, 10, 27, 10, 10, tzinfo=C.IST), {"AAA.NS": b}, {}, {"AAA.NS": 997.0}, None)
    assert eng.day["halted"] and not eng.broker.positions  # -3000 > 2500 limit
    eng2 = Engine(100_000, new_day(DAY, {"atr": {}}))
    eng2.broker.open("AAA.NS", -1, 10, 1000, 1100, 900, datetime(2026, 10, 27, 10, tzinfo=C.IST), "t",
                     "2026-10-27T10:00:00+05:30")
    eng2.step(datetime(2026, 10, 27, 15, 10, tzinfo=C.IST), {"AAA.NS": b}, {}, {"AAA.NS": 997.0}, None)
    assert eng2.closed[0]["exit_reason"].startswith("square-off")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("PASS", name)

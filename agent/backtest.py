"""Backtests for the Gap Fade strategy.

    python -m agent.backtest           # writes BACKTEST.md

Part A replays the exact live engine over the last ~60 days of 5-minute data
(entry at the 09:20 price, stop-loss checked bar by bar, square-off 15:10).
Part B applies the same rules to 10 years of daily data (entry at the open, exit at
the official close, 1% stop checked against the day's high) for a long-run view.
Both deduct full charges and slippage.
"""
import logging
import math
from datetime import timedelta

import numpy as np
import pandas as pd

from . import config as C
from . import data
from .broker import charges
from .engine import Engine, new_day
from .store import ROOT
from .strategy import pick, prev_close, today_only

log = logging.getLogger("backtest")


def simulate_day(day, equity, bars, index5, dly):
    """Replay one day of 5-min bars through the live engine."""
    pc = {s: v for s, df in dly.items() if (v := prev_close(df, day))}
    eng = Engine(equity, new_day(day, {"prev_close": pc}))
    opens = {s: float(df["open"].iloc[0]) for s, df in bars.items() if df.index[0].time() == C.MARKET_OPEN}
    index_open = float(index5["open"].iloc[0])
    for t in index5.index:
        upto = {s: df.loc[:t] for s, df in bars.items()}
        upto = {s: df for s, df in upto.items() if len(df)}
        quotes = {}
        for s, df in bars.items():
            nxt = df[df.index > t]
            quotes[s] = float(nxt["open"].iloc[0]) if len(nxt) else float(df["close"].loc[:t].iloc[-1])
        eng.step(t + timedelta(minutes=5), upto, quotes, opens, index_open)
        if eng.day["halted"] and not eng.broker.positions:
            break
    if eng.broker.positions:
        eng.flatten(index5.index[-1], {s: float(df["close"].iloc[-1]) for s, df in bars.items()}, "end of data")
    return eng


def replay_60d(intr, dly):
    idx = intr[C.INDEX]
    equity, rows, trades = C.STARTING_CAPITAL, [], []
    for day in sorted(set(idx.index.date)):
        bars = {s: today_only(df, day) for s, df in intr.items() if s != C.INDEX}
        bars = {s: df for s, df in bars.items() if len(df) > 10}
        idx5 = today_only(idx, day)
        if len(idx5) < 20 or not bars:
            continue
        eng = simulate_day(day, equity, bars, idx5, dly)
        equity += eng.day["realized"]
        rows.append({"date": day, "trades": eng.day["n_trades"], "net": eng.day["realized"],
                     "equity": equity, "note": eng.day["halt_reason"]})
        trades += [{"date": day, **t} for t in eng.closed]
    return pd.DataFrame(rows), pd.DataFrame(trades)


def daily_10y(dly):
    """Same rules on daily bars, fixed Rs 1 lakh base (no compounding)."""
    syms = [s for s in C.UNIVERSE if s in dly]
    o = pd.DataFrame({s: dly[s]["open"] for s in syms})
    h = pd.DataFrame({s: dly[s]["high"] for s in syms})
    c = pd.DataFrame({s: dly[s]["close"] for s in syms})
    pc = c.shift(1)
    ni = dly[C.INDEX]
    n_gap = (ni["open"] / ni["close"].shift(1) - 1).reindex(o.index)
    rows = []
    for dt in o.index[1:]:
        opens = o.loc[dt].dropna().to_dict()
        cands = pick(opens, pc.loc[dt].dropna().to_dict(), None if np.isnan(n_gap.get(dt, np.nan)) else n_gap[dt])
        pnl = 0.0
        if cands:
            notional = min(C.STARTING_CAPITAL * C.LEVERAGE / len(cands), C.STARTING_CAPITAL * C.MAX_POSITION_X)
            for s, _ in cands:
                entry = o.at[dt, s] * (1 - C.SLIPPAGE_PCT)
                qty = math.floor(notional / entry)
                stop = o.at[dt, s] * (1 + C.STOP_PCT)
                ex = (stop if h.at[dt, s] >= stop else c.at[dt, s]) * (1 + C.SLIPPAGE_PCT)
                pnl += (entry - ex) * qty - charges(ex * qty, entry * qty)
        rows.append({"date": dt.date(), "net": pnl, "trades": len(cands)})
    return pd.DataFrame(rows).set_index("date")


def summarize(net, trades_per_day):
    act = net[trades_per_day > 0]
    eq = C.STARTING_CAPITAL + net.cumsum()
    return {"days": len(net), "total": net.sum(), "per_day": net.mean(),
            "active_share": len(act) / max(len(net), 1), "per_active": act.mean() if len(act) else 0,
            "win_days": (act > 0).mean() if len(act) else 0, "hit_target": int((net >= C.DAILY_TARGET).sum()),
            "best": net.max(), "worst": net.min(), "max_dd": (eq.cummax() - eq).max()}


def table(rows):
    keys = [("days", "Trading days", "{:.0f}"), ("total", "Total net P&L", "Rs {:,.0f}"),
            ("per_day", "Average per trading day", "Rs {:,.0f}"), ("active_share", "Days with a setup", "{:.0%}"),
            ("per_active", "Average on days it traded", "Rs {:,.0f}"), ("win_days", "Winning days (when traded)", "{:.0%}"),
            ("hit_target", f"Days >= Rs {C.DAILY_TARGET:,}", "{}"), ("best", "Best day", "Rs {:,.0f}"),
            ("worst", "Worst day", "Rs {:,.0f}"), ("max_dd", "Max drawdown", "Rs {:,.0f}")]
    head = "| Metric | " + " | ".join(rows) + " |\n|---|" + "---|" * len(rows) + "\n"
    return head + "\n".join(f"| {lab} | " + " | ".join(fmt.format(r[k]) for r in rows.values()) + " |"
                            for k, lab, fmt in keys)


def run():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    syms = list(C.UNIVERSE) + [C.INDEX]
    log.info("downloading data...")
    intr = data.intraday(syms, interval="5m", period="60d")
    dly = data.daily(syms, period="10y")
    a_days, a_trades = replay_60d(intr, dly)
    b = daily_10y(dly)
    cut = pd.Timestamp("2024-01-01").date()
    tr, te = b[b.index < cut], b[b.index >= cut]
    years = b.groupby(pd.to_datetime(b.index).year)
    lines = [
        "# Backtest: Gap Fade strategy", "",
        f"Rules: on days NIFTY opens <= {C.INDEX_GAP_MAX:+.1%} vs yesterday, short up to {C.MAX_POSITIONS} stocks that opened "
        f">= {C.GAP_MIN:.2%} above yesterday's close (biggest gaps first), {C.LEVERAGE:.0f}x intraday leverage on "
        f"Rs {C.STARTING_CAPITAL:,}, {C.STOP_PCT:.0%} stop-loss, square-off 15:10. Full charges + 0.03% slippage per fill.", "",
        "## Long-run check (daily data, fixed Rs 1 lakh base)", "",
        "Rules were chosen using 2016-2023 only. 2024-2026 is the out-of-sample check.", "",
        table({"2016-2023 (chosen on)": summarize(tr.net, tr.trades), "2024-2026 (unseen)": summarize(te.net, te.trades)}), "",
        "| Year | Net P&L | Days traded | Winning days |", "|---|---|---|---|",
    ]
    for y, g in years:
        act = g[g.trades > 0]
        lines.append(f"| {y} | Rs {g.net.sum():,.0f} | {len(act)} | {(act.net > 0).mean() if len(act) else 0:.0%} |")
    lines += ["", "## Last ~60 days, replayed through the live engine (5-min bars)", ""]
    if len(a_days):
        lines += [table({"Last 60 days": summarize(a_days.net, a_days.trades)}), "",
                  "| Date | Trades | Net | Equity | Note |", "|---|---|---|---|---|"]
        lines += [f"| {r.date} | {r.trades} | {r.net:,.0f} | {r.equity:,.0f} | {r.note} |" for r in a_days.itertuples()]
    lines += ["", "_Past results do not guarantee future results. Paper trading only._"]
    (ROOT / "BACKTEST.md").write_text("\n".join(lines) + "\n")
    if len(a_trades):
        a_trades.to_csv(ROOT / "state" / "backtest_trades.csv", index=False)
    print("\n".join(lines[:30]))


if __name__ == "__main__":
    run()

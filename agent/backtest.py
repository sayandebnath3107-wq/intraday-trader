"""Replay the exact same engine over the last ~60 days of real 5-minute NSE data.

    python -m agent.backtest           # writes BACKTEST.md

Limits: Yahoo only keeps ~60 days of 5-min history, historical headlines are not
available (news score = 0), and fills are simulated at the next bar's open + slippage.
"""
import logging
from datetime import timedelta

import pandas as pd

from . import config as C
from . import data, news
from .engine import Engine, new_day
from .store import ROOT
from .strategy import prior_atr, today_only

log = logging.getLogger("backtest")


def simulate_day(day, equity, bars, index5, dly, cues):
    ctx = {"atr": {s: v for s in bars if s in dly and (v := prior_atr(dly[s], day))},
           "global_score": news.global_cues(cues, before_date=day)[0],
           "vix": news.india_vix(cues, before_date=day), "market_news_score": 0.0, "stock_news": {}}
    eng = Engine(equity, new_day(day, ctx))
    times = index5.index
    for i, t in enumerate(times):
        upto = {s: df.loc[:t] for s, df in bars.items()}
        upto = {s: df for s, df in upto.items() if len(df)}
        quotes = {}
        for s, df in bars.items():
            nxt = df[df.index > t]
            quotes[s] = float(nxt["open"].iloc[0]) if len(nxt) else float(df["close"].loc[:t].iloc[-1])
        eng.step(t + timedelta(minutes=5), upto, upto, quotes, index5.loc[:t])
        if eng.day["halted"] and not eng.broker.positions:
            break
    if eng.broker.positions:
        eng.flatten(times[-1], {s: float(df["close"].iloc[-1]) for s, df in bars.items()}, "end of data")
        eng.day["halt_reason"] = eng.day["halt_reason"] or "end of data"
    return eng


def run():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    syms = list(C.UNIVERSE)
    log.info("downloading 5-min data (this takes a minute)...")
    intr = data.intraday(syms + [C.INDEX], interval="5m", period="60d")
    dly = data.daily(syms, period="1y")
    cues = data.daily(list(C.GLOBAL_CUES) + [C.INDIA_VIX], period="1y")
    idx = intr.pop(C.INDEX)
    days = sorted(set(idx.index.date))
    equity, rows, trades = C.STARTING_CAPITAL, [], []
    for day in days:
        bars = {s: today_only(df, day) for s, df in intr.items()}
        bars = {s: df for s, df in bars.items() if len(df) > 10}
        idx5 = today_only(idx, day)
        if len(idx5) < 20 or not bars:
            continue
        eng = simulate_day(day, equity, bars, idx5, dly, cues)
        pnl = eng.day["realized"]
        equity += pnl
        rows.append({"date": day, "trades": eng.day["n_trades"], "net": pnl, "equity": equity,
                     "note": eng.day["halt_reason"]})
        trades += [{"date": day, **t} for t in eng.closed]
        log.info("%s trades=%d net=%+.0f equity=%.0f", day, eng.day["n_trades"], pnl, equity)
    write(rows, trades)


def write(rows, trades):
    df = pd.DataFrame(rows)
    tr = pd.DataFrame(trades)
    n = len(df)
    eq = df["equity"] if n else pd.Series([C.STARTING_CAPITAL])
    dd = (eq.cummax() - eq).max()
    lines = [
        "# Backtest (last ~60 trading days, real NSE 5-min data)", "",
        "Same engine as live. News score is 0 (no historical headlines). Fills = next bar open +/- 0.03% slippage, "
        "full Zerodha-style charges deducted.", "",
        "| Metric | Value |", "|---|---|",
        f"| Days | {n} |",
        f"| Total net P&L | Rs {df['net'].sum() if n else 0:,.0f} |",
        f"| Average per day | Rs {df['net'].mean() if n else 0:,.0f} |",
        f"| Days >= Rs {C.DAILY_TARGET:,} | {int((df['net'] >= C.DAILY_TARGET).sum()) if n else 0} |",
        f"| Profitable days | {int((df['net'] > 0).sum()) if n else 0} |",
        f"| Losing days | {int((df['net'] < 0).sum()) if n else 0} |",
        f"| Best / worst day | Rs {df['net'].max() if n else 0:,.0f} / Rs {df['net'].min() if n else 0:,.0f} |",
        f"| Max drawdown | Rs {dd:,.0f} |",
        f"| Trades / win rate | {len(tr)} / {100 * (tr['net'] > 0).mean() if len(tr) else 0:.0f}% |",
        f"| Total charges paid | Rs {tr['charges'].sum() if len(tr) else 0:,.0f} |",
        "", "| Date | Trades | Net | Equity | Note |", "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['date']} | {r['trades']} | {r['net']:,.0f} | {r['equity']:,.0f} | {r['note']} |")
    (ROOT / "BACKTEST.md").write_text("\n".join(lines) + "\n")
    if len(tr):
        tr.to_csv(ROOT / "state" / "backtest_trades.csv", index=False)
    print("\n".join(lines[:16]))


if __name__ == "__main__":
    run()

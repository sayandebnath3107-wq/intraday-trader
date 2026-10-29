"""Live paper-trading loop. GitHub Actions starts this every market day; it runs on its own.

    python -m agent.main            # trade today (exits quickly on weekends/holidays)
"""
import logging
import time as _time
from datetime import datetime, timedelta

import pandas as pd

from . import config as C
from . import data, news, notify, store
from .engine import Engine, new_day
from .strategy import prior_atr, today_only

log = logging.getLogger("agent")


def at(day, t):
    return datetime.combine(day, t, tzinfo=C.IST)


def prepare_day(today):
    log.info("pre-market prep for %s", today)
    dly = data.daily(list(C.UNIVERSE), period="6mo")
    atrs = {s: v for s, df in dly.items() if (v := prior_atr(df, today))}
    try:
        ctx = news.premarket_context(today)
    except Exception as e:
        log.warning("news/global prep failed: %s", e)
        ctx = {"global_score": 0.0, "market_news_score": 0.0, "stock_news": {}, "vix": None}
    ctx["atr"] = {s: round(v, 2) for s, v in atrs.items()}
    log.info("global=%s vix=%s news=%s atr for %d stocks", ctx["global_score"], ctx["vix"],
             ctx["market_news_score"], len(atrs))
    return ctx


def snapshot(today, upto):
    """Fetch 1-min bars and build what the engine needs, as of time `upto`."""
    frames = data.intraday(list(C.UNIVERSE) + [C.INDEX], interval="1m", period="1d")
    frames = {s: df[df.index <= upto] for s, df in frames.items()}
    frames = {s: today_only(df, today) for s, df in frames.items()}
    frames = {s: df for s, df in frames.items() if len(df)}
    idx = frames.pop(C.INDEX, None)
    fine = {s: data.completed(df, upto, 1) for s, df in frames.items()}
    bars5 = {s: data.completed(data.resample_5m(df), upto, 5) for s, df in frames.items()}
    quotes = {s: float(df["close"].iloc[-1]) for s, df in frames.items()}
    idx5 = data.completed(data.resample_5m(idx), upto, 5) if idx is not None else None
    return idx, fine, bars5, quotes, idx5


def finalize(state, eng):
    d = eng.day
    state["equity"] = round(state["equity"] + d["realized"], 2)
    state["days_done"] += 1
    d["finalized"] = True
    store.log_day({"date": d["date"], "trades": d["n_trades"], "net_pnl": d["realized"],
                   "equity": state["equity"], "hit_target": d["realized"] >= C.DAILY_TARGET,
                   "halt_reason": d["halt_reason"]})
    store.save(state)
    store.write_report(state)
    store.commit(f"day {state['days_done']}: {d['date']} net {d['realized']:+.0f}")
    notify.send(f"Day {state['days_done']} done: Rs {d['realized']:+,.0f}",
                f"Trades {d['n_trades']} | equity Rs {state['equity']:,.0f} | {d['halt_reason']}",
                priority="high")
    log.info("day finalized: net %.2f equity %.2f", d["realized"], state["equity"])


def recover_stale(state):
    """A previous day never finished (runner died). Close its positions at that day's 15:10 price."""
    d = state["day"]
    day = datetime.fromisoformat(d["date"]).date()
    eng = Engine(state["equity"], d, on_event=lambda k, t: k == "close" and store.log_trade(d["date"], t))
    syms = list(eng.broker.positions)
    marks = {}
    if syms:
        bars = data.intraday(syms, interval="5m", period="5d")
        for s, df in bars.items():
            df = df[(df.index.date == day) & (df.index < at(day, C.SQUARE_OFF))]
            if len(df):
                marks[s] = float(df["close"].iloc[-1])
    eng.flatten(at(day, C.SQUARE_OFF), marks, "recovered after restart")
    d["halt_reason"] = d["halt_reason"] or "recovered after restart"
    finalize(state, eng)


def run():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    started = datetime.now(C.IST)
    deadline = started + timedelta(minutes=C.MAX_RUNTIME_MINUTES)
    today = started.date()
    state = store.load()

    if state["day"] and not state["day"]["finalized"] and state["day"]["date"] != today.isoformat():
        recover_stale(state)
    if state["days_done"] >= C.MAX_TRADING_DAYS:
        log.info("%d-day run complete. See REPORT.md.", C.MAX_TRADING_DAYS)
        return
    if today.weekday() >= 5 or state.get("holiday") == today.isoformat():
        log.info("weekend/holiday")
        return
    if state["day"] and state["day"]["date"] == today.isoformat() and state["day"]["finalized"]:
        log.info("today already finished")
        return
    if started >= at(today, C.MARKET_CLOSE) and not (state["day"] and state["day"]["date"] == today.isoformat()):
        log.info("market closed and nothing open for today")
        return

    if not state["day"] or state["day"]["date"] != today.isoformat():
        state["day"] = new_day(today, prepare_day(today))
        store.save(state)
    day = state["day"]
    dirty = []

    def on_event(kind, payload):
        dirty.append(kind)
        if kind == "open":
            notify.send(f"{'BUY' if payload['side'] > 0 else 'SELL'} {payload['symbol']} x{payload['qty']}",
                        f"@ {payload['entry']} stop {payload['stop']} target {payload['target']}")
        elif kind == "close":
            store.log_trade(day["date"], payload)
            notify.send(f"Closed {payload['symbol']}: Rs {payload['net']:+,.0f}",
                        f"{payload['exit_reason']} | day P&L Rs {day['realized']:+,.0f}")
        elif kind in ("halt", "target"):
            notify.send(f"Agent: {kind}", str(payload))

    eng = Engine(state["equity"], day, on_event)
    last_commit = _time.time()

    while True:
        now = datetime.now(C.IST)
        if now >= deadline:
            log.info("runtime limit reached; next scheduled run will resume")
            store.save(state)
            store.commit(f"{day['date']} checkpoint")
            return
        if now < at(today, C.MARKET_OPEN) + timedelta(minutes=1):
            _time.sleep(min(60, (at(today, C.MARKET_OPEN) + timedelta(minutes=1) - now).total_seconds() + 1))
            continue

        upto = min(now, at(today, C.SQUARE_OFF))
        idx, fine, bars5, quotes, idx5 = snapshot(today, pd.Timestamp(upto))
        if idx is None or not fine:
            if now > at(today, C.MARKET_OPEN) + timedelta(minutes=25):
                if not eng.broker.positions and not day["n_trades"]:
                    log.info("no market data today -> exchange holiday; not counted")
                    state["day"], state["holiday"] = None, today.isoformat()
                    store.save(state)
                    store.commit(f"{today} holiday")
                    return
            log.warning("no data yet, retrying")
            _time.sleep(C.POLL_SECONDS)
            continue

        eng.step(upto, fine, bars5, quotes, idx5)
        if dirty or _time.time() - last_commit > 900:
            store.save(state)
            store.commit(f"{day['date']} {','.join(dirty) or 'checkpoint'} pnl {day['realized']:+.0f}")
            dirty.clear()
            last_commit = _time.time()

        if day["halted"] and not eng.broker.positions:
            finalize(state, eng)
            return
        nxt = (now + timedelta(minutes=1)).replace(second=15, microsecond=0)
        _time.sleep(max(5, (nxt - datetime.now(C.IST)).total_seconds()))


if __name__ == "__main__":
    run()

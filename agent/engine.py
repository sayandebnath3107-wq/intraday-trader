"""The trading brain for one day. Same code runs live (paper) and in the backtest.

`day` is a plain dict so it can be saved to JSON and resumed if the run restarts.
"""
import math

import pandas as pd

from . import config as C
from .broker import PaperBroker
from .strategy import pick


def new_day(date, ctx):
    return {"date": date.isoformat(), "realized": 0.0, "peak": 0.0, "entered": False,
            "halted": False, "halt_reason": "", "traded": [], "n_trades": 0, "positions": {},
            "ctx": ctx, "finalized": False}


class Engine:
    def __init__(self, equity, day, on_event=lambda kind, data: None):
        self.equity = equity                 # equity at the start of the day
        self.day = day
        self.broker = PaperBroker(day["positions"])
        self.on_event = on_event
        self.closed = []

    # ---- helpers -------------------------------------------------------------
    def _close(self, sym, price, now, reason):
        t = self.broker.close(sym, price, now, reason)
        self.day["realized"] = round(self.day["realized"] + t["net"], 2)
        self.closed.append(t)
        self.on_event("close", t)

    def flatten(self, now, marks, reason):
        for sym in list(self.broker.positions):
            self._close(sym, marks.get(sym, self.broker.positions[sym]["entry"]), now, reason)

    def _halt(self, reason):
        if not self.day["halted"]:
            self.day["halted"], self.day["halt_reason"] = True, reason
            self.on_event("halt", {"reason": reason, "pnl": self.day["realized"]})

    def pnl(self, marks):
        return self.day["realized"] + self.broker.unrealized(marks)

    # ---- stop-loss checks: walk new bars in order ------------------------------
    def _manage(self, fine, now):
        for sym, p in list(self.broker.positions.items()):
            df = fine.get(sym)
            if df is None:
                continue
            for ts, bar in df[df.index > pd.Timestamp(p["checked_until"])].iterrows():
                side = p["side"]
                if (bar["low"] <= p["stop"]) if side > 0 else (bar["high"] >= p["stop"]):
                    px = min(p["stop"], bar["open"]) if side > 0 else max(p["stop"], bar["open"])
                    self._close(sym, px, now, "stop-loss")
                    break
                p["best"] = max(p["best"], bar["high"]) if side > 0 else min(p["best"], bar["low"])
                p["checked_until"] = ts.isoformat()

    # ---- one tick --------------------------------------------------------------
    def step(self, now, fine, quotes, opens, index_open):
        """fine: {sym: today's COMPLETED bars}; quotes: {sym: price we could trade at now};
        opens: {sym: today's 09:15 opening price}; index_open: NIFTY's opening price."""
        d = self.day
        self._manage(fine, now)
        marks = {s: quotes[s] for s in quotes}
        pnl = self.pnl(marks)
        d["peak"] = round(max(d["peak"], pnl), 2)

        if now.time() >= C.SQUARE_OFF:
            self.flatten(now, marks, "square-off 15:10")
            self._halt("end of day")
            return
        if pnl <= -C.MAX_DAILY_LOSS:
            self.flatten(now, marks, "daily loss limit")
            self._halt(f"daily loss limit hit ({pnl:.0f})")
            return
        if d["halted"] and not self.broker.positions:
            return
        if d["entered"] or now.time() < C.ENTRY_START:
            if d["entered"] and not self.broker.positions and not d["halted"]:
                self._halt("all positions stopped out" if d["n_trades"] else "no setup today")
            return
        if now.time() > C.ENTRY_END:
            d["entered"] = True
            self._halt("entry window missed")
            return

        # ---- the one entry decision of the day -----------------------------------
        ctx = d["ctx"]
        pc = ctx["prev_close"]
        if index_open is None or not pc.get(C.INDEX):
            return  # wait for NIFTY's first bar
        index_gap = index_open / pc[C.INDEX] - 1
        d["index_gap"] = round(index_gap, 5)
        cands = pick(opens, pc, index_gap)
        d["entered"] = True
        if not cands:
            why = (f"NIFTY opened {index_gap:+.2%} (needs <= {C.INDEX_GAP_MAX:+.2%})"
                   if index_gap > C.INDEX_GAP_MAX else f"no stock gapped up > {C.GAP_MIN:.2%}")
            self._halt(f"no setup today: {why}")
            return
        notional = min(self.equity * C.LEVERAGE / len(cands), self.equity * C.MAX_POSITION_X)
        for sym, gap in cands:
            price = quotes.get(sym)
            if not price or price <= pc[sym]:  # gap already fully filled before we could enter
                continue
            qty = math.floor(notional / price)
            if qty < 1:
                continue
            last_bar = fine[sym].index[-1].isoformat() if len(fine.get(sym, [])) else now.isoformat()
            pos = self.broker.open(sym, -1, qty, price, price * (1 + C.STOP_PCT), 0.0, now,
                                   f"gap {gap:+.2%}, NIFTY gap {index_gap:+.2%}", last_bar)
            d["traded"].append(sym)
            d["n_trades"] += 1
            self.on_event("open", {"symbol": sym, **pos})
        if not self.broker.positions:
            self._halt("no setup today: gaps filled before entry")

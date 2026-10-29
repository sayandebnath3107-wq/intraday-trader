"""The trading brain for one day. Same code runs live (paper) and in the backtest.

`day` is a plain dict so it can be saved to JSON and resumed if the run restarts.
"""
import math

import pandas as pd

from . import config as C
from .broker import PaperBroker
from .strategy import market_bias, scan


def new_day(date, ctx):
    return {"date": date.isoformat(), "realized": 0.0, "peak": 0.0, "target_hit": False,
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

    # ---- position management: walk new bars in order -------------------------
    def _manage(self, fine, now):
        for sym, p in list(self.broker.positions.items()):
            df = fine.get(sym)
            if df is None:
                continue
            new = df[df.index > pd.Timestamp(p["checked_until"])]
            for ts, bar in new.iterrows():
                side, r = p["side"], p["risk"]
                hit_stop = bar["low"] <= p["stop"] if side > 0 else bar["high"] >= p["stop"]
                if hit_stop:  # gap through the stop fills at the open
                    px = min(p["stop"], bar["open"]) if side > 0 else max(p["stop"], bar["open"])
                    self._close(sym, px, now, "stop")
                    break
                hit_tgt = bar["high"] >= p["target"] if side > 0 else bar["low"] <= p["target"]
                if hit_tgt:
                    px = max(p["target"], bar["open"]) if side > 0 else min(p["target"], bar["open"])
                    self._close(sym, px, now, "target")
                    break
                p["best"] = max(p["best"], bar["high"]) if side > 0 else min(p["best"], bar["low"])
                gain = (p["best"] - p["entry"]) * side
                if gain >= C.TRAIL_START_R * r:            # lock breakeven (+ costs)
                    be = p["entry"] + side * 0.1 * r
                    p["stop"] = max(p["stop"], be) if side > 0 else min(p["stop"], be)
                if gain >= (C.TRAIL_START_R + 0.5) * r:    # trail behind the best price
                    tr = p["best"] - side * C.TRAIL_GAP_R * r
                    p["stop"] = max(p["stop"], tr) if side > 0 else min(p["stop"], tr)
                p["stop"] = round(p["stop"], 2)
                p["checked_until"] = ts.isoformat()

    # ---- one tick --------------------------------------------------------------
    def step(self, now, fine, bars5, quotes, index5):
        """fine/bars5: {sym: today's COMPLETED bars}; quotes: {sym: price we could trade at now}."""
        d = self.day
        self._manage(fine, now)
        marks = {s: quotes.get(s) or fine[s]["close"].iloc[-1] for s in fine if len(fine[s])}
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
        if pnl >= C.DAILY_TARGET and not d["target_hit"]:
            d["target_hit"] = True
            self.on_event("target", {"pnl": round(pnl, 2)})
        if d["target_hit"]:
            if pnl < C.PROFIT_LOCK_FRACTION * d["peak"] or not self.broker.positions:
                self.flatten(now, marks, "profit lock")
                self._halt(f"daily target reached, locked {self.day['realized']:.0f}")
            return
        if d["halted"]:
            return

        # ---- new entries ----------------------------------------------------------
        or_end = (pd.Timestamp.combine(now.date(), C.MARKET_OPEN) +
                  pd.Timedelta(minutes=C.OPENING_RANGE_MINUTES)).time()
        if not (or_end <= now.time() <= C.LAST_ENTRY):
            return
        ctx = d["ctx"]
        bias = market_bias(index5, ctx.get("global_score", 0), ctx.get("market_news_score", 0))
        skip = set(d["traded"]) | set(self.broker.positions)
        vix_cut = 0.5 if (ctx.get("vix") or 0) > C.HIGH_VIX else 1.0
        exposure = sum(p["entry"] * p["qty"] for p in self.broker.positions.values())
        for sig in scan(bars5, {"atr": ctx["atr"], "news": ctx.get("stock_news", {})}, bias, skip):
            if (len(self.broker.positions) >= C.MAX_OPEN_POSITIONS or d["n_trades"] >= C.MAX_TRADES_PER_DAY):
                break
            price = quotes.get(sig.symbol)
            if not price:
                continue
            dist = (price - sig.stop) * sig.side
            if dist <= 0 or (sig.target - price) * sig.side <= dist:  # moved too far, R:R now poor
                continue
            risk_amt = min(self.equity * C.RISK_PER_TRADE * vix_cut, C.MAX_DAILY_LOSS + pnl)
            qty = math.floor(risk_amt / dist)
            per_pos_cap = self.equity * C.LEVERAGE / C.MAX_OPEN_POSITIONS
            room = self.equity * C.LEVERAGE - exposure
            qty = min(qty, math.floor(per_pos_cap / price), math.floor(room / price))
            if qty < 1:
                continue
            last_bar = fine[sig.symbol].index[-1].isoformat()
            pos = self.broker.open(sig.symbol, sig.side, qty, price, sig.stop, sig.target, now,
                                   sig.reason, last_bar)
            exposure += pos["entry"] * qty
            d["traded"].append(sig.symbol)
            d["n_trades"] += 1
            self.on_event("open", {"symbol": sig.symbol, **pos})

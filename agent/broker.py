"""Paper broker: fills at market price with slippage and real Indian intraday charges.

To go live later, write a class with the same open()/close() methods that calls
a broker API (e.g. Dhan or Zerodha) instead of simulating the fill.
"""
from . import config as C


def charges(buy_value, sell_value):
    brokerage = min(C.BROKERAGE_CAP, C.BROKERAGE_PCT * buy_value) + min(C.BROKERAGE_CAP, C.BROKERAGE_PCT * sell_value)
    turnover = buy_value + sell_value
    stt = C.STT_SELL_PCT * sell_value
    exch = C.EXCHANGE_PCT * turnover
    sebi = C.SEBI_PER_CRORE * turnover / 1e7
    stamp = C.STAMP_BUY_PCT * buy_value
    gst = C.GST_PCT * (brokerage + exch + sebi)
    return round(brokerage + stt + exch + sebi + stamp + gst, 2)


class PaperBroker:
    def __init__(self, positions=None):
        self.positions = positions if positions is not None else {}  # sym -> dict (JSON-serialisable)

    @staticmethod
    def _fill(price, side_buy):
        return price * (1 + C.SLIPPAGE_PCT) if side_buy else price * (1 - C.SLIPPAGE_PCT)

    def open(self, sym, side, qty, price, stop, target, when, reason, checked_until):
        fill = self._fill(price, side_buy=side > 0)
        self.positions[sym] = {
            "side": side, "qty": int(qty), "entry": round(fill, 2), "stop": round(stop, 2),
            "target": round(target, 2), "risk": round(abs(fill - stop), 2), "best": round(fill, 2),
            "time": when.isoformat(), "reason": reason, "checked_until": checked_until,
        }
        return self.positions[sym]

    def close(self, sym, price, when, reason):
        p = self.positions.pop(sym)
        fill = self._fill(price, side_buy=p["side"] < 0)
        buy_v, sell_v = (p["entry"], fill) if p["side"] > 0 else (fill, p["entry"])
        buy_v, sell_v = buy_v * p["qty"], sell_v * p["qty"]
        gross = sell_v - buy_v
        cost = charges(buy_v, sell_v)
        return {
            "symbol": sym, "side": "LONG" if p["side"] > 0 else "SHORT", "qty": p["qty"],
            "entry_time": p["time"], "entry": p["entry"], "exit_time": when.isoformat(),
            "exit": round(fill, 2), "gross": round(gross, 2), "charges": cost,
            "net": round(gross - cost, 2), "entry_reason": p["reason"], "exit_reason": reason,
        }

    def unrealized(self, marks):
        total = 0.0
        for sym, p in self.positions.items():
            px = marks.get(sym, p["entry"])
            total += (px - p["entry"]) * p["side"] * p["qty"]
        return total

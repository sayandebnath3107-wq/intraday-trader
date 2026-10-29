"""Signal logic: Opening Range Breakout confirmed by VWAP, volume, market trend and news.

Long  when a 5-min bar closes above the 09:15-09:30 high, above VWAP, on heavy volume,
      with NIFTY/global cues not bearish and no bad news on the stock.
Short is the mirror image.
"""
from dataclasses import dataclass

import pandas as pd

from . import config as C
from .data import vwap


@dataclass
class Signal:
    symbol: str
    side: int          # +1 long, -1 short
    price: float       # signal bar close
    stop: float
    target: float
    score: float
    reason: str


def market_bias(index5, global_score, news_score):
    """-1..1: how bullish the broad market is right now."""
    intraday = 0.0
    if index5 is not None and len(index5) >= 2:
        last = index5["close"].iloc[-1]
        day_open = index5["open"].iloc[0]
        vw = vwap(index5).iloc[-1]
        intraday = max(-1.0, min(1.0, ((last / day_open - 1) + (last / vw - 1)) / 0.004))
    return round(0.6 * intraday + 0.25 * global_score + 0.15 * news_score, 3)


def scan(bars5, ctx, bias, skip=()):
    """bars5: {sym: today's completed 5-min bars}. ctx: {sym: {"atr":..}, "news": {...}}."""
    n_or = C.OPENING_RANGE_MINUTES // 5
    out = []
    for sym, df in bars5.items():
        if sym in skip or sym not in ctx["atr"] or len(df) < n_or + 1:
            continue
        atr = ctx["atr"][sym]
        orng = df.iloc[:n_or]
        or_hi, or_lo = orng["high"].max(), orng["low"].min()
        if atr <= 0 or (or_hi - or_lo) > C.MAX_OR_WIDTH_ATR * atr:
            continue
        rest = df.iloc[n_or:]
        last = rest.iloc[-1]
        recent = rest["close"].iloc[-3:-1]  # the bars just before the signal bar
        avg_vol = df["volume"].iloc[:-1].mean()
        rel_vol = last["volume"] / avg_vol if avg_vol > 0 else 0.0
        vw = vwap(df).iloc[-1]
        news = ctx["news"].get(sym, 0.0)
        c = last["close"]

        for side in (1, -1):
            level = or_hi if side > 0 else or_lo
            broke = (c - level) * side > 0
            fresh = len(recent) == 0 or ((recent - level) * side <= 0).any()
            not_chased = abs(c - level) <= C.MAX_EXTENSION_ATR * atr
            with_vwap = (c - vw) * side > 0
            mkt_ok = bias * side >= -0.2
            news_ok = news * side >= -0.3
            if not (broke and fresh and not_chased and with_vwap and mkt_ok and news_ok
                    and rel_vol >= C.MIN_REL_VOLUME):
                continue
            far = (or_lo if side > 0 else or_hi)
            dist = min(abs(c - far), C.STOP_ATR_MULT * atr)
            dist = max(dist, C.MIN_STOP_PCT * c)
            stop = c - side * dist
            target = c + side * C.REWARD_RISK * dist
            score = min(rel_vol, 4) / 4 + abs(c - level) / atr + 0.5 * bias * side + 0.3 * news * side
            reason = (f"ORB {'up' if side > 0 else 'down'} lvl={level:.2f} relvol={rel_vol:.1f} "
                      f"vwap={vw:.2f} bias={bias:+.2f} news={news:+.2f}")
            out.append(Signal(sym, side, float(c), float(stop), float(target), round(float(score), 3), reason))
    return sorted(out, key=lambda s: s.score, reverse=True)


def today_only(df, day):
    return df[df.index.date == day]


def prior_atr(daily_df, day):
    from .data import atr
    d = daily_df[daily_df.index.date < day]
    if len(d) < 15:
        return None
    v = atr(d).iloc[-1]
    return None if pd.isna(v) else float(v)

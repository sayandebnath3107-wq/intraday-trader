"""Gap Fade: on a flat/weak market open, short the stocks that still gapped up.

Research (10 years of NSE daily data, chosen on 2016-2023, checked on 2024-2026):
a stock opening >= 0.75% above its previous close while NIFTY opens flat or down
gives back part of the gap by the close on average. See BACKTEST.md.
"""
from . import config as C


def pick(opens, prev_close, index_gap):
    """Return [(symbol, gap)] to short, biggest gap first. Empty if no setup today."""
    if index_gap is None or index_gap > C.INDEX_GAP_MAX:
        return []
    gaps = {s: opens[s] / prev_close[s] - 1 for s in opens if prev_close.get(s)}
    cands = sorted(((s, g) for s, g in gaps.items() if g > C.GAP_MIN), key=lambda x: -x[1])
    return cands[:C.MAX_POSITIONS]


def today_only(df, day):
    return df[df.index.date == day]


def prev_close(daily_df, day):
    d = daily_df[daily_df.index.date < day]
    return float(d["close"].iloc[-1]) if len(d) else None

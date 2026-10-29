"""Free news & global cues: RSS feeds + Yahoo indices. No API keys.

Sentiment is a simple finance word list scored on headlines. It is a filter
(avoid buying a stock with bad news, avoid shorting one with good news),
not a prediction engine.
"""
import logging
import math
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus

import requests

from . import config as C
from . import data

log = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (paper-trading-agent)"}

POSITIVE = set("""surge surges soar soars jump jumps rally rallies gain gains rise rises climb climbs record high
upgrade upgrades upgraded beat beats outperform buy bullish profit profits growth strong order orders win wins
approval approves expansion dividend bonus buyback acquire acquisition boost boosts positive upbeat recovery
inflow inflows robust raises raised target""".split())
NEGATIVE = set("""fall falls plunge plunges slump slumps drop drops crash crashes tumble tumbles decline declines
loss losses downgrade downgrades downgraded miss misses weak sell bearish fraud probe raid penalty fine ban
resign resigns default lawsuit slowdown cut cuts warning concern concerns outflow outflows selloff sell-off
pressure low lows tension war tariff tariffs recession inflation""".split())


def _headlines(url, limit=40):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        return [(i.findtext("title") or "").strip() for i in root.iter("item")][:limit]
    except Exception as e:
        log.info("feed failed %s: %s", url[:60], e)
        return []


def score_text(titles):
    pos = neg = 0
    for t in titles:
        words = re.findall(r"[a-z\-]+", t.lower())
        pos += sum(w in POSITIVE for w in words)
        neg += sum(w in NEGATIVE for w in words)
    return (pos - neg) / (pos + neg + 3)  # in (-1, 1), shrunk toward 0 when little news


def stock_news(universe=C.UNIVERSE):
    def one(item):
        sym, name = item
        titles = _headlines(C.STOCK_NEWS_URL.format(q=quote_plus(f'"{name}"')), limit=15)
        return sym, score_text(titles), titles[:3]

    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(one, universe.items()))
    return {s: sc for s, sc, _ in res}, {s: t for s, _, t in res if t}


def market_news():
    titles = []
    for u in C.MARKET_FEEDS:
        titles += _headlines(u)
    return score_text(titles), titles[:10]


def global_cues(daily_frames, before_date=None):
    """Weighted overnight move of world markets -> score in (-1, 1)."""
    total = 0.0
    detail = {}
    for t, w in C.GLOBAL_CUES.items():
        df = daily_frames.get(t)
        if df is None:
            continue
        if before_date is not None:
            df = df[df.index.date < before_date]
        if len(df) < 2:
            continue
        chg = df["close"].iloc[-1] / df["close"].iloc[-2] - 1
        detail[t] = round(chg * 100, 2)
        total += w * chg
    return math.tanh(total / 0.01), detail  # a ~1% weighted move ~ 0.76


def india_vix(daily_frames, before_date=None):
    df = daily_frames.get(C.INDIA_VIX)
    if df is None or df.empty:
        return None
    if before_date is not None:
        df = df[df.index.date < before_date]
    return float(df["close"].iloc[-1]) if len(df) else None


def premarket_context(today):
    """Everything the agent needs before the open. Each part fails soft."""
    cues = data.daily(list(C.GLOBAL_CUES) + [C.INDIA_VIX], period="1mo")
    g_score, g_detail = global_cues(cues, before_date=today)
    vix = india_vix(cues, before_date=today)
    m_score, m_titles = market_news()
    s_scores, s_titles = stock_news()
    return {"global_score": round(g_score, 3), "global_detail": g_detail, "vix": vix,
            "market_news_score": round(m_score, 3), "market_headlines": m_titles,
            "stock_news": {k: round(v, 3) for k, v in s_scores.items()}, "stock_headlines": s_titles}

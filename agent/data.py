"""Free market data from Yahoo Finance (via yfinance). No API key needed.

NSE quotes on Yahoo can lag by a minute or two; the agent's stops and
backtest costs are set with that in mind.
"""
import logging
import time as _time

import numpy as np
import pandas as pd
import yfinance as yf

from .config import IST

log = logging.getLogger(__name__)


def _download(tickers, retries=4, **kw):
    for attempt in range(retries):
        try:
            df = yf.download(tickers=list(tickers), group_by="ticker", auto_adjust=False,
                             progress=False, threads=True, prepost=False, **kw)
            if df is not None and not df.empty:
                return df
        except Exception as e:  # network hiccups, Yahoo throttling
            log.warning("download failed (%s), attempt %d", e, attempt + 1)
        _time.sleep(5 * (attempt + 1))
    return pd.DataFrame()


def _split(df, tickers):
    """Turn yfinance's multi-ticker frame into {ticker: OHLCV frame in IST}."""
    out = {}
    if df.empty:
        return out
    for t in tickers:
        try:
            sub = df[t] if isinstance(df.columns, pd.MultiIndex) else df
        except KeyError:
            continue
        sub = sub.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna(
            subset=["open", "high", "low", "close"])
        if sub.empty:
            continue
        idx = sub.index
        sub.index = idx.tz_localize("UTC").tz_convert(IST) if idx.tz is None else idx.tz_convert(IST)
        out[t] = sub.astype(float)
    return out


def intraday(tickers, interval="1m", period="1d"):
    return _split(_download(tickers, interval=interval, period=period), tickers)


def daily(tickers, period="6mo"):
    data = _split(_download(tickers, interval="1d", period=period), tickers)
    for t, df in data.items():
        df.index = df.index.normalize()
    return data


def resample_5m(df):
    """1-minute bars -> 5-minute bars aligned to 09:15."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    return df.resample("5min", origin="start_day", offset="15min").agg(agg).dropna(subset=["close"])


def completed(df, now, minutes):
    """Only bars that have fully closed by `now`."""
    return df[df.index + pd.Timedelta(minutes=minutes) <= now]


def vwap(df):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    vol = df["volume"]
    if vol.sum() <= 0:  # index has no volume
        return tp.expanding().mean()
    return (tp * vol).cumsum() / vol.cumsum().replace(0, np.nan)


def atr(daily_df, n=14):
    h, l, c = daily_df["high"], daily_df["low"], daily_df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

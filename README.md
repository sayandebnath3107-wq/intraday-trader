# Intraday Paper-Trading Agent (NSE)

An agent that trades NIFTY 50 stocks intraday with **demo money (Rs 1,00,000)**, every market day,
for 60 trading days. It runs for free on GitHub Actions. You don't need to open anything, it uses no
paid API keys, and it doesn't use any Claude/AI usage.

**Goal:** Rs 5,000/day. **Reality check:** that is 5% a day. No strategy can promise it, and most
intraday traders lose money (SEBI: ~70% of individual intraday traders lost money in FY23).
The strategy below is the only one, of about 20 tested, that made money in years it wasn't tuned on.
Over 10 years it averaged **about Rs 180-250 per trading day** on Rs 1 lakh. That is far below
Rs 5,000, and there are losing months. See `BACKTEST.md`.

## Strategy: Gap Fade
When the overall market (NIFTY) opens flat or down, but a stock still opens 0.75% or more above
yesterday's close, that stock has tended to give back part of the jump during the day. The agent:

| Time (IST) | Step |
|---|---|
| 08:50-09:15 | Pre-market: yesterday's closing prices, plus a log of world markets, India VIX and news headlines (for context only). |
| 09:16 | Checks the opening prices. If NIFTY opened flat or down, it **short-sells** up to 4 stocks that opened >= 0.75% up (biggest gaps first), splitting 5x intraday leverage (Rs 5 lakh exposure) between them. If there is no setup, it doesn't trade that day. |
| During the day | Each short has a **1% stop-loss**. It's checked every minute. |
| 15:10 | Buys back everything, writes `REPORT.md`, commits it to the repo, and sends a phone notification. |

The P&L includes real charges (brokerage, STT, exchange, SEBI, stamp duty, GST) and 0.03% slippage per fill.

### How it was chosen
- Data: 10 years of daily, 2 years of hourly and 60 days of 5-minute NSE prices, all from free Yahoo Finance.
- About 20 ideas were tested: opening-range breakout (the first version; it lost Rs 41k in 60 days), gap
  fade/follow, yesterday-reversal, buying gap-downs, NIFTY open-to-close, and first-hour momentum.
- The rules were picked using **2016-2023 only**, then checked on **2024-2026**. They were profitable
  in 10 of 11 years. 2022 was slightly negative, and the most recent 3 months were about break-even.

## Links
- `REPORT.md`: live scorecard (updated every trading day)
- `BACKTEST.md`: how the strategy did historically
- `state/trades.csv`: every paper trade
- Actions tab: watch it run, read the logs, or start it by hand

## Setup already done
- The workflows run on their own: **Intraday paper trader** (weekdays 08:50 IST, with backups through
  the day), **Backtest**, and **Fetch research data**.
- Optional phone alerts: install the **ntfy** app and subscribe to a hard-to-guess topic name. In the repo
  go to **Settings → Secrets and variables → Actions → New repository secret**, name it `NTFY_TOPIC`,
  and set its value to that topic name.

## Files
- `agent/config.py`: every number (gap size, stop, leverage, loss limit, stocks). Change things here.
- `agent/strategy.py`: entry rule. `agent/engine.py`: stop-loss, loss limit and square-off.
- `agent/main.py`: live loop. `agent/backtest.py`: historical replay of the same engine.
- `state/`: saved positions, `trades.csv`, `daily.csv`.

## Honest limits
- Yahoo's free NSE data can lag 1-2 minutes. Real fills would differ a little from paper fills.
- GitHub's scheduled starts can be late. If the agent isn't running by 10:00 IST, it skips that day
  (the day isn't counted).
- Short-selling at 5x leverage can lose Rs 5,000+ in a day, and losing streaks have reached Rs 30-40k.
- No Twitter/X: its API is paid. News headlines are logged but don't drive trades, because they
  showed no measurable edge in testing.
- Going live with real money needs a broker API (e.g. Dhan, Zerodha Kite) and SEBI's retail algo rules.
  Only consider it if the 60-day paper record is clearly positive.

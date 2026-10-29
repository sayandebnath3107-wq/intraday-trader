# Intraday Paper-Trading Agent (NSE)

An agent that trades NIFTY 50 stocks intraday with **demo money (Rs 1,00,000)**, every market day,
for 60 trading days. It runs for free on GitHub Actions. You don't need to open anything, it uses no
paid API keys, and it doesn't use any Claude/AI usage.

**Goal:** Rs 5,000/day. **Reality check:** that is 5% a day. No strategy can promise it, and most
intraday traders lose money (SEBI: ~70% of individual intraday traders lost money in FY23). This
agent chases the goal with strict risk control and records every rupee honestly. After 60 days you
will know from evidence, not hope, whether it deserves real money.

## What it does each day (all automatic)
| Time (IST) | Step |
|---|---|
| 09:05 | Pre-market: overnight US/Europe/Asia moves, crude, USD/INR, India VIX, market headlines (ET, Moneycontrol, Mint, Google News) and per-stock headlines. Headlines are scored for sentiment. |
| 09:15-09:30 | Records each stock's opening range. |
| 09:30-14:30 | Scans 42 stocks every minute. **Buys** when a 5-min bar breaks above the opening range, above VWAP, on high volume, with the market not bearish and no bad news. **Short-sells** the mirror case. |
| Live | Every trade gets a stop-loss and a 2x target. The stop moves to breakeven at +1R, then trails behind the best price. |
| Day rules | Reaches **Rs 5,000** → no new trades, and profits are locked (exit if P&L falls below 80% of the day's peak). Loses **Rs 2,500** → everything is closed and trading stops for the day. Max 4 open positions, 6 trades/day, 5x intraday leverage. High VIX → half size. |
| 15:10 | Squares off everything, writes `REPORT.md`, commits to the repo, and sends a phone notification. |

The P&L includes real charges (brokerage, STT, exchange, SEBI, stamp duty, GST) and slippage.

## Setup (10 minutes, one time)
1. Create a free account at github.com, then a **new public repository** (public = unlimited free
   Actions minutes; a private repo only gets 2,000 free minutes/month and this needs ~8,000).
2. Upload this whole folder to it (including the hidden `.github` folder).
3. Repo → **Settings → Actions → General → Workflow permissions → Read and write** → Save.
4. Optional phone alerts: install the **ntfy** app, subscribe to a hard-to-guess topic name
   (e.g. `sayan-trader-8f3k2`). In the repo go to **Settings → Secrets and variables → Actions → New secret**:
   name `NTFY_TOPIC`, value = that topic name.
5. **Actions** tab → enable workflows → run **"Backtest (last 60 days)"** once. It writes
   `BACKTEST.md`, showing how this exact strategy did on the last ~60 days of real data.
6. That's it. "Intraday paper trader" now starts by itself every weekday at 09:05 IST. Watch `REPORT.md`.

## Files
- `agent/config.py`: every number (target, loss limit, risk, leverage, stocks). Change things here.
- `agent/strategy.py`: entry rules. `agent/engine.py`: risk and exit management.
- `agent/main.py`: live loop. `agent/backtest.py`: historical replay of the same engine.
- `state/`: saved positions, `trades.csv`, `daily.csv`. `REPORT.md`: running scorecard.

## Honest limits
- Yahoo's free NSE data can lag 1-2 minutes. Real fills would differ a little from paper fills.
- GitHub's scheduled starts can be late by several minutes. Backup starts every 30 minutes resume
  from saved state, so a late start costs some opportunity but not the day.
- No Twitter/X: its API is paid. News comes from free RSS headlines.
- Going live with real money needs a broker API (e.g. Dhan, Zerodha Kite) and SEBI's retail algo rules.
  Only consider it if the 60-day paper record is clearly positive.

"""All tunable settings live here. Change numbers here, not in the logic."""
from datetime import time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# ---- Money & goal -----------------------------------------------------------
STARTING_CAPITAL = 100_000          # demo money (Rs)
DAILY_TARGET = 5_000                # the goal we measure against (not a cap: winners run to the close)
MAX_DAILY_LOSS = 7_000              # backstop only; the 1% stops normally cap a day near -Rs 5,500
MAX_TRADING_DAYS = 60               # paper-trading run length

# ---- Strategy: "Gap Fade" ----------------------------------------------------
# On days NIFTY opens flat/down, stocks that still open >= 0.75% above yesterday's close
# tend to give back part of that gap during the day. Short them, buy back at 15:10.
# 10-year research (2016-2026): see BACKTEST.md.
GAP_MIN = 0.0075                    # stock open vs previous close
INDEX_GAP_MAX = 0.0                 # NIFTY open vs previous close must be <= this
MAX_POSITIONS = 4                   # biggest gaps first
LEVERAGE = 5.0                      # intraday (MIS) margin: ~20% => 5x exposure
MAX_POSITION_X = 2.5                # one stock never gets more than 2.5x equity notional
STOP_PCT = 0.01                     # stop-loss 1% above the short entry

# ---- Session timing (IST) ---------------------------------------------------
MARKET_OPEN = time(9, 15)
ENTRY_START = time(9, 16)
ENTRY_END = time(10, 0)             # if the run starts later than this, the day is skipped
SQUARE_OFF = time(15, 10)           # brokers auto-square MIS ~15:20; we exit earlier
MARKET_CLOSE = time(15, 30)
POLL_SECONDS = 60
MAX_RUNTIME_MINUTES = 340           # GitHub job limit is 360; exit cleanly before it

# ---- Costs (Zerodha-style intraday equity) ----------------------------------
BROKERAGE_PCT = 0.0003
BROKERAGE_CAP = 20.0
STT_SELL_PCT = 0.00025
EXCHANGE_PCT = 0.0000297
SEBI_PER_CRORE = 10.0
STAMP_BUY_PCT = 0.00003
GST_PCT = 0.18
SLIPPAGE_PCT = 0.0003               # assume we lose 0.03% on every fill

# ---- Universe: liquid NIFTY 50 stocks (Yahoo tickers) -----------------------
UNIVERSE = {
    "RELIANCE.NS": "Reliance Industries", "HDFCBANK.NS": "HDFC Bank", "ICICIBANK.NS": "ICICI Bank",
    "INFY.NS": "Infosys", "TCS.NS": "TCS", "SBIN.NS": "SBI", "AXISBANK.NS": "Axis Bank",
    "KOTAKBANK.NS": "Kotak Mahindra Bank", "LT.NS": "Larsen & Toubro", "ITC.NS": "ITC",
    "BHARTIARTL.NS": "Bharti Airtel", "HINDUNILVR.NS": "Hindustan Unilever", "BAJFINANCE.NS": "Bajaj Finance",
    "MARUTI.NS": "Maruti Suzuki", "SUNPHARMA.NS": "Sun Pharma", "TITAN.NS": "Titan",
    "ULTRACEMCO.NS": "UltraTech Cement", "ASIANPAINT.NS": "Asian Paints", "HCLTECH.NS": "HCL Technologies",
    "WIPRO.NS": "Wipro", "TECHM.NS": "Tech Mahindra", "NTPC.NS": "NTPC", "POWERGRID.NS": "Power Grid",
    "ONGC.NS": "ONGC", "COALINDIA.NS": "Coal India", "TATASTEEL.NS": "Tata Steel", "JSWSTEEL.NS": "JSW Steel",
    "HINDALCO.NS": "Hindalco", "ADANIENT.NS": "Adani Enterprises", "ADANIPORTS.NS": "Adani Ports",
    "M&M.NS": "Mahindra & Mahindra", "BAJAJFINSV.NS": "Bajaj Finserv", "INDUSINDBK.NS": "IndusInd Bank",
    "DRREDDY.NS": "Dr Reddy's", "CIPLA.NS": "Cipla", "EICHERMOT.NS": "Eicher Motors",
    "HEROMOTOCO.NS": "Hero MotoCorp", "BPCL.NS": "BPCL", "GRASIM.NS": "Grasim", "NESTLEIND.NS": "Nestle India",
    "TRENT.NS": "Trent", "BEL.NS": "Bharat Electronics",
}
INDEX = "^NSEI"
INDIA_VIX = "^INDIAVIX"
# Global cues: ticker -> weight (negative = bad for India when it rises)
GLOBAL_CUES = {"^GSPC": 1.0, "^IXIC": 0.7, "^N225": 0.5, "^HSI": 0.5, "^FTSE": 0.4,
               "CL=F": -0.5, "USDINR=X": -0.8}

# ---- News (free RSS, no keys) -----------------------------------------------
MARKET_FEEDS = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://www.livemint.com/rss/markets",
    "https://news.google.com/rss/search?q=sensex+nifty+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=RBI+OR+%22FII+selling%22+OR+%22FII+buying%22+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
]
STOCK_NEWS_URL = "https://news.google.com/rss/search?q={q}+share+when:1d&hl=en-IN&gl=IN&ceid=IN:en"

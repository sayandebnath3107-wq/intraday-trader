"""All tunable settings live here. Change numbers here, not in the logic."""
from datetime import time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# ---- Money & goal -----------------------------------------------------------
STARTING_CAPITAL = 100_000          # demo money (Rs)
DAILY_TARGET = 5_000                # once day P&L reaches this, stop new entries and lock profit
PROFIT_LOCK_FRACTION = 0.8          # after target, exit everything if P&L falls below 80% of the day's peak
MAX_DAILY_LOSS = 2_500              # hard stop for the day (Rs). Protects the capital.
MAX_TRADING_DAYS = 60               # paper-trading run length

# ---- Risk & sizing ----------------------------------------------------------
LEVERAGE = 5.0                      # intraday (MIS) margin: ~20% => 5x exposure
RISK_PER_TRADE = 0.012              # risk 1.2% of equity between entry and stop
MAX_OPEN_POSITIONS = 4
MAX_TRADES_PER_DAY = 6
HIGH_VIX = 22.0                     # India VIX above this => half position size

# ---- Session timing (IST) ---------------------------------------------------
MARKET_OPEN = time(9, 15)
OPENING_RANGE_MINUTES = 15          # 09:15-09:30 opening range
LAST_ENTRY = time(14, 30)
SQUARE_OFF = time(15, 10)           # brokers auto-square MIS ~15:20; we exit earlier
MARKET_CLOSE = time(15, 30)
POLL_SECONDS = 60
MAX_RUNTIME_MINUTES = 340           # GitHub job limit is 360; exit cleanly before it

# ---- Strategy (Opening Range Breakout + VWAP + volume + market/news filters) --
MIN_REL_VOLUME = 1.3                # breakout bar volume vs average bar volume so far today
MAX_OR_WIDTH_ATR = 0.9              # skip if opening range too wide (stop would be too far)
STOP_ATR_MULT = 0.6
MIN_STOP_PCT = 0.0035               # stop at least 0.35% away (avoid noise stop-outs)
REWARD_RISK = 2.0
TRAIL_START_R = 1.0                 # at +1R move stop to breakeven
TRAIL_GAP_R = 1.0                   # beyond +1.5R trail 1R behind the best price
MAX_EXTENSION_ATR = 0.5             # don't chase: price must be within 0.5 ATR of the breakout level

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

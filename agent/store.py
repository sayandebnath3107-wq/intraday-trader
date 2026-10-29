"""Saves everything into the repo (state/ folder + REPORT.md) and commits it,
so progress survives between GitHub Actions runs and you can read it on GitHub."""
import csv
import json
import logging
import os
import subprocess
from pathlib import Path

from . import config as C

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "state.json"
TRADES = ROOT / "state" / "trades.csv"
DAILY = ROOT / "state" / "daily.csv"
REPORT = ROOT / "REPORT.md"

TRADE_FIELDS = ["date", "symbol", "side", "qty", "entry_time", "entry", "exit_time", "exit", "gross",
                "charges", "net", "entry_reason", "exit_reason"]
DAILY_FIELDS = ["date", "trades", "net_pnl", "equity", "hit_target", "halt_reason"]


def load():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"equity": C.STARTING_CAPITAL, "days_done": 0, "day": None}


def save(state):
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1, default=str))


def _append(path, fields, row):
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def log_trade(date, t):
    _append(TRADES, TRADE_FIELDS, {"date": date, **t})


def log_day(row):
    _append(DAILY, DAILY_FIELDS, row)


def _read(path):
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def write_report(state):
    days = _read(DAILY)
    trades = _read(TRADES)
    pnl = [float(d["net_pnl"]) for d in days]
    total = sum(pnl)
    hits = sum(p >= C.DAILY_TARGET for p in pnl)
    peak, dd, eq = C.STARTING_CAPITAL, 0.0, C.STARTING_CAPITAL
    for p in pnl:
        eq += p
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    lines = [
        "# Paper-trading report", "",
        f"Starting capital: Rs {C.STARTING_CAPITAL:,.0f} | Goal: Rs {C.DAILY_TARGET:,.0f}/day for {C.MAX_TRADING_DAYS} days", "",
        "| Metric | Value |", "|---|---|",
        f"| Trading days done | {len(days)} / {C.MAX_TRADING_DAYS} |",
        f"| Current equity | Rs {state['equity']:,.0f} |",
        f"| Total net P&L (after all charges) | Rs {total:,.0f} |",
        f"| Average per day | Rs {total / len(days) if days else 0:,.0f} |",
        f"| Days that reached Rs {C.DAILY_TARGET:,} | {hits} |",
        f"| Losing days | {sum(p < 0 for p in pnl)} |",
        f"| Worst day | Rs {min(pnl) if pnl else 0:,.0f} |",
        f"| Max drawdown | Rs {dd:,.0f} |",
        f"| Total trades | {len(trades)} |",
        f"| Win rate | {100 * sum(float(t['net']) > 0 for t in trades) / len(trades) if trades else 0:.0f}% |",
        "", "## Daily results", "", "| Date | Trades | Net P&L | Equity | Note |", "|---|---|---|---|---|",
    ]
    for d in reversed(days):
        lines.append(f"| {d['date']} | {d['trades']} | {float(d['net_pnl']):,.0f} | {float(d['equity']):,.0f} | {d['halt_reason']} |")
    lines += ["", "## Last 20 trades", "", "| Date | Stock | Side | Qty | Entry | Exit | Net | Why exit |",
              "|---|---|---|---|---|---|---|---|"]
    for t in reversed(trades[-20:]):
        lines.append(f"| {t['date']} | {t['symbol']} | {t['side']} | {t['qty']} | {t['entry']} | {t['exit']} | "
                     f"{float(t['net']):,.0f} | {t['exit_reason']} |")
    lines += ["", "_Paper trading with simulated fills on free, slightly delayed data. Not investment advice._"]
    REPORT.write_text("\n".join(lines) + "\n")


def commit(message):
    """Commit and push state when running inside GitHub Actions."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    try:
        run = lambda *a: subprocess.run(a, cwd=ROOT, check=True, capture_output=True, text=True)
        run("git", "add", "state", "REPORT.md")
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
            return
        run("git", "-c", "user.name=trading-agent", "-c", "user.email=agent@users.noreply.github.com",
            "commit", "-m", message)
        for _ in range(3):
            if subprocess.run(["git", "pull", "--rebase", "-X", "theirs", "-q"], cwd=ROOT).returncode == 0 and \
               subprocess.run(["git", "push", "-q"], cwd=ROOT).returncode == 0:
                return
        log.warning("push failed; will retry on next save")
    except subprocess.CalledProcessError as e:
        log.warning("commit failed: %s", e.stderr)

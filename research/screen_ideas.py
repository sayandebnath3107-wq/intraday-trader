"""Idea screen used to pick the strategy (run after `python -m research.fetch_data`; reads data/*.pkl
converted from data/*.csv.gz). Kept for transparency."""
import numpy as np, pandas as pd
COST = 0.0013
d = pd.read_pickle("data/bars_1d.pkl")
d = d[d.symbol.str.endswith(".NS")]
d["date"] = d.ts.dt.date
o = d.pivot(index="date", columns="symbol", values="open")
c = d.pivot(index="date", columns="symbol", values="close")
h = d.pivot(index="date", columns="symbol", values="high")
l = d.pivot(index="date", columns="symbol", values="low")
pc = c.shift(1)
gap = o / pc - 1
oc = c / o - 1                     # intraday open->close
prev_ret = c.shift(1) / c.shift(2) - 1
idx = pd.read_pickle("data/bars_1d.pkl"); idx = idx[idx.symbol == "^NSEI"]; idx["date"] = idx.ts.dt.date
ni = idx.set_index("date")
n_oc = ni.close / ni.open - 1
n_gap = ni.open / ni.close.shift(1) - 1
train = lambda s: s[s.index < pd.Timestamp("2024-01-01").date()]
test = lambda s: s[s.index >= pd.Timestamp("2024-01-01").date()]

def stats(daily, name):
    out = []
    for nm, part in (("train", train(daily)), ("test", test(daily))):
        part = part.dropna()
        part = part[part != 0] if False else part
        out.append(f"{nm}: n={len(part):4d} mean={part.mean()*1e4:6.1f}bp sharpe={part.mean()/part.std()*np.sqrt(250) if part.std()>0 else 0:5.2f} hit={(part>0).mean():.2f}")
    print(f"{name:45s} | " + " | ".join(out))

print("Baseline: average stock open->close (no cost):"); stats(oc.mean(axis=1), "long all stocks open->close, gross")
stats(-oc.mean(axis=1) - COST, "short all open->close, net")
for k in (3, 5):
    rk = gap.rank(axis=1)
    n = gap.notna().sum(axis=1)
    top = rk.gt(n - k, axis=0); bot = rk.le(k, axis=0)
    fade = (-oc[top]).mean(axis=1).fillna(0)*0.5 + (oc[bot]).mean(axis=1).fillna(0)*0.5 - COST
    stats(fade, f"gap fade top/bottom {k} (L/S), net")
    stats(-fade - 2*COST, f"gap follow top/bottom {k} (L/S), net")
    rk2 = prev_ret.rank(axis=1)
    rev = (oc[rk2.le(k, axis=0)]).mean(axis=1) * 0.5 + (-oc[rk2.gt(n - k, axis=0)]).mean(axis=1) * 0.5 - COST
    stats(rev, f"yesterday reversal {k} (L/S), net")
for thr in (0.01, 0.02):
    big_up = gap > thr; big_dn = gap < -thr
    stats((-oc[big_up]).mean(axis=1).dropna() - COST, f"short gap-ups > {thr:.0%}, net")
    stats((oc[big_dn]).mean(axis=1).dropna() - COST, f"buy gap-downs < -{thr:.0%}, net")
stats(n_oc - COST, "NIFTY long open->close, net")
stats((-n_oc)[n_gap > 0.005] - COST, "NIFTY short when gap-up >0.5%, net")
stats((n_oc)[n_gap < -0.005] - COST, "NIFTY long when gap-down >0.5%, net")

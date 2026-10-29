# Backtest: Gap Fade strategy

Rules: on days NIFTY opens <= +0.0% vs yesterday, short up to 4 stocks that opened >= 0.75% above yesterday's close (biggest gaps first), 5x intraday leverage on Rs 100,000, 1% stop-loss, square-off 15:10. Full charges + 0.03% slippage per fill.

## Long-run check (daily data, fixed Rs 1 lakh base)

Rules were chosen using 2016-2023 only. 2024-2026 is the out-of-sample check.

| Metric | 2016-2023 (chosen on) | 2024-2026 (unseen) |
|---|---|---|
| Trading days | 1771 | 699 |
| Total net P&L | Rs 437,098 | Rs 127,120 |
| Average per trading day | Rs 247 | Rs 182 |
| Days with a setup | 18% | 24% |
| Average on days it traded | Rs 1,366 | Rs 761 |
| Winning days (when traded) | 49% | 51% |
| Days >= Rs 5,000 | 70 | 31 |
| Best day | Rs 80,023 | Rs 15,463 |
| Worst day | Rs -5,654 | Rs -5,657 |
| Max drawdown | Rs 29,364 | Rs 39,719 |

| Year | Net P&L | Days traded | Winning days |
|---|---|---|---|
| 2016 | Rs 16,528 | 11 | 55% |
| 2017 | Rs 68,465 | 39 | 62% |
| 2018 | Rs 46,119 | 43 | 44% |
| 2019 | Rs 51,261 | 50 | 42% |
| 2020 | Rs 51,420 | 45 | 44% |
| 2021 | Rs 74,109 | 40 | 57% |
| 2022 | Rs -2,687 | 43 | 44% |
| 2023 | Rs 131,884 | 49 | 53% |
| 2024 | Rs 42,580 | 44 | 61% |
| 2025 | Rs 55,648 | 55 | 51% |
| 2026 | Rs 28,893 | 68 | 44% |

## Last ~60 days, replayed through the live engine (5-min bars)

| Metric | Last 60 days |
|---|---|
| Trading days | 60 |
| Total net P&L | Rs -524 |
| Average per trading day | Rs -9 |
| Days with a setup | 33% |
| Average on days it traded | Rs -26 |
| Winning days (when traded) | 45% |
| Days >= Rs 5,000 | 3 |
| Best day | Rs 7,529 |
| Worst day | Rs -4,913 |
| Max drawdown | Rs 15,644 |

| Date | Trades | Net | Equity | Note |
|---|---|---|---|---|
| 2026-08-04 | 0 | 0 | 100,000 | no setup today: no stock gapped up > 0.75% |
| 2026-08-05 | 0 | 0 | 100,000 | no setup today: NIFTY opened +0.22% (needs <= +0.00%) |
| 2026-08-06 | 0 | 0 | 100,000 | no setup today: NIFTY opened +0.03% (needs <= +0.00%) |
| 2026-08-07 | 0 | 0 | 100,000 | no setup today: no stock gapped up > 0.75% |
| 2026-08-10 | 0 | 0 | 100,000 | no setup today: NIFTY opened +0.05% (needs <= +0.00%) |
| 2026-08-11 | 2 | 6,096 | 106,096 | end of day |
| 2026-08-12 | 0 | 0 | 106,096 | no setup today: NIFTY opened +0.00% (needs <= +0.00%) |
| 2026-08-13 | 0 | 0 | 106,096 | no setup today: gaps filled before entry |
| 2026-08-14 | 0 | 0 | 106,096 | no setup today: no stock gapped up > 0.75% |
| 2026-08-17 | 0 | 0 | 106,096 | no setup today: no stock gapped up > 0.75% |
| 2026-08-18 | 0 | 0 | 106,096 | no setup today: no stock gapped up > 0.75% |
| 2026-08-19 | 0 | 0 | 106,096 | no setup today: NIFTY opened +0.03% (needs <= +0.00%) |
| 2026-08-20 | 0 | 0 | 106,096 | no setup today: NIFTY opened +0.61% (needs <= +0.00%) |
| 2026-08-21 | 0 | 0 | 106,096 | no setup today: NIFTY opened +0.21% (needs <= +0.00%) |
| 2026-08-24 | 0 | 0 | 106,096 | no setup today: NIFTY opened +0.14% (needs <= +0.00%) |
| 2026-08-25 | 1 | 1,139 | 107,235 | end of day |
| 2026-08-26 | 0 | 0 | 107,235 | no setup today: NIFTY opened +0.03% (needs <= +0.00%) |
| 2026-08-27 | 0 | 0 | 107,235 | no setup today: NIFTY opened +0.29% (needs <= +0.00%) |
| 2026-08-28 | 0 | 0 | 107,235 | no setup today: NIFTY opened +0.16% (needs <= +0.00%) |
| 2026-08-31 | 0 | 0 | 107,235 | no setup today: no stock gapped up > 0.75% |
| 2026-09-01 | 4 | 464 | 107,699 | end of day |
| 2026-09-02 | 1 | -2,997 | 104,702 | all positions stopped out |
| 2026-09-03 | 0 | 0 | 104,702 | no setup today: NIFTY opened +0.35% (needs <= +0.00%) |
| 2026-09-04 | 0 | 0 | 104,702 | no setup today: NIFTY opened +0.18% (needs <= +0.00%) |
| 2026-09-07 | 0 | 0 | 104,702 | no setup today: no stock gapped up > 0.75% |
| 2026-09-08 | 2 | -1,354 | 103,347 | end of day |
| 2026-09-09 | 1 | 3,061 | 106,408 | end of day |
| 2026-09-10 | 0 | 0 | 106,408 | no setup today: NIFTY opened +0.06% (needs <= +0.00%) |
| 2026-09-11 | 1 | 7,529 | 113,937 | end of day |
| 2026-09-15 | 0 | 0 | 113,937 | no setup today: NIFTY opened +0.76% (needs <= +0.00%) |
| 2026-09-16 | 0 | 0 | 113,937 | no setup today: NIFTY opened +0.36% (needs <= +0.00%) |
| 2026-09-17 | 1 | -1,593 | 112,345 | end of day |
| 2026-09-18 | 0 | 0 | 112,345 | no setup today: NIFTY opened +0.28% (needs <= +0.00%) |
| 2026-09-21 | 2 | -4,913 | 107,432 | end of day |
| 2026-09-22 | 0 | 0 | 107,432 | no setup today: NIFTY opened +0.17% (needs <= +0.00%) |
| 2026-09-23 | 0 | 0 | 107,432 | no setup today: NIFTY opened +0.10% (needs <= +0.00%) |
| 2026-09-24 | 0 | 0 | 107,432 | no setup today: no stock gapped up > 0.75% |
| 2026-09-25 | 0 | 0 | 107,432 | no setup today: no stock gapped up > 0.75% |
| 2026-09-28 | 1 | -2,987 | 104,445 | all positions stopped out |
| 2026-09-29 | 2 | -1,985 | 102,460 | end of day |
| 2026-09-30 | 4 | 786 | 103,245 | end of day |
| 2026-10-01 | 4 | -4,635 | 98,611 | end of day |
| 2026-10-05 | 0 | 0 | 98,611 | no setup today: NIFTY opened +0.49% (needs <= +0.00%) |
| 2026-10-06 | 0 | 0 | 98,611 | no setup today: NIFTY opened +0.21% (needs <= +0.00%) |
| 2026-10-07 | 0 | 0 | 98,611 | no setup today: no stock gapped up > 0.75% |
| 2026-10-08 | 1 | 6,392 | 105,002 | end of day |
| 2026-10-09 | 0 | 0 | 105,002 | no setup today: NIFTY opened +0.38% (needs <= +0.00%) |
| 2026-10-12 | 0 | 0 | 105,002 | no setup today: NIFTY opened +0.32% (needs <= +0.00%) |
| 2026-10-13 | 0 | 0 | 105,002 | no setup today: NIFTY opened +0.02% (needs <= +0.00%) |
| 2026-10-14 | 1 | -2,910 | 102,093 | all positions stopped out |
| 2026-10-15 | 0 | 0 | 102,093 | no setup today: NIFTY opened +0.21% (needs <= +0.00%) |
| 2026-10-16 | 0 | 0 | 102,093 | no setup today: NIFTY opened +0.25% (needs <= +0.00%) |
| 2026-10-19 | 0 | 0 | 102,093 | no setup today: NIFTY opened +0.02% (needs <= +0.00%) |
| 2026-10-21 | 0 | 0 | 102,093 | no setup today: NIFTY opened +0.56% (needs <= +0.00%) |
| 2026-10-22 | 1 | 2,116 | 104,209 | end of day |
| 2026-10-23 | 0 | 0 | 104,209 | no setup today: NIFTY opened +0.24% (needs <= +0.00%) |
| 2026-10-26 | 2 | -3,103 | 101,106 | end of day |
| 2026-10-27 | 1 | -2,813 | 98,294 | all positions stopped out |
| 2026-10-28 | 1 | 3,143 | 101,437 | end of day |
| 2026-10-29 | 4 | -1,961 | 99,476 | end of day |

_Past results do not guarantee future results. Paper trading only._

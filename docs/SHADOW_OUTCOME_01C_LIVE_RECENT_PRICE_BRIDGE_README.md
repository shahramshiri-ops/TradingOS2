# SHADOW-OUTCOME-01C — Live-Recent Price Bridge Guard

`01B` could choose stale sample/audit H1 files. This patch forces outcome to use live-recent M5 incremental sources only.

It prefers:

```text
data/live_m5/incremental/{INSTRUMENT}_M5_incremental_latest.csv
```

It rejects sample/audit/historical/factory/backtest/discovery/validation/holdout paths, resamples live M5 to H1, and writes:

```text
runtime/sig_shadow/price_bridge_h1/{INSTRUMENT}_H1.csv
```

Boundary: no signal, no PnL, no entry/stop/target, no broker/execution, no auto-learning, no rule rewrite.

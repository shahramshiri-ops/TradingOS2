# User Guide — Personal Runtime V1

Generated: `2026-05-04T10:51:03Z`  
Program: `PRV1-01 — Personal Runtime V1 Final Productization Program`

## 1. What this package is

`personal_runtime_v1` is a personal runtime observation package. Its intended flow is:

```text
run / refresh → latest state → candidate / lifecycle / outcome state → panel payload → display-ready files
```

This package is a personal display-only runtime observation surface. It is not a signal, not trading advice, not buy/sell/hold, not entry/stop/target, not an order/execution/broker path, not PnL or win/loss, not validation, not an adaptation decision, and not a production-readiness claim.

## 2. Open the package

After unzipping, open:

```text
personal_runtime_v1/
```

Main folders:

```text
config/   active V1 configuration
state/    runtime, candidate/lifecycle, and outcome state
panel/    static panel and panel payload
logs/     heartbeat and last-run status
scripts/  refresh/status/panel generation scripts
reports/  cache and run reports
proofs/   boundary and dry-run proofs
```

## 3. Refresh the runtime state

On Windows:

```bat
cd personal_runtime_v1
scriptsun_refresh.bat
```

Or with Python:

```bash
cd personal_runtime_v1
python scripts/run_refresh.py --package-root . --print-summary
python scripts/check_runtime_status.py --package-root .
```

The V1 refresh path is **cache-first / state-first**. It uses packaged state and cache files. It must not claim a new live fetch unless that is actually run locally with a properly configured environment.

## 4. Open the panel

Open this file in a browser:

```text
personal_runtime_v1/panel/index.html
```

You can also read:

```text
personal_runtime_v1/panel/panel_summary_v1.md
```

## 5. Active V1 instruments

Only these instruments are active:

- `XAUUSD`
- `EURUSD`
- `USDJPY`

`SPX` and `NQ` are out of active V1 scope and should not appear as blocked daily noise in the V1 panel.

## 6. Current runtime state in this package

- candidate count: `4`
- lifecycle count: `4`
- active tracking count: `1`
- final outcome observations: `3`

These are summary counts. If the detailed row-level candidate store is not available, the package must not fabricate it from summary counts.

## 7. What “candidate” means

In V1, a candidate is a **runtime observation lifecycle object** for review/display context.

A candidate is not:

- a trade recommendation
- buy / sell / hold
- an entry
- a stop / target
- allocation / size
- order or execution
- a validation verdict

## 8. What “lifecycle” means

Lifecycle means descriptive runtime tracking of a candidate object. It is not execution tracking and does not imply that a trade was opened, managed, closed, won, or lost.

## 9. What “outcome observation” means

Outcome observation is descriptive lifecycle observation only. It must not be interpreted as PnL, win/loss, trade result, model approval, or validation verdict.

In this package:

- final outcome recorded: `3`
- active tracking: `1`

## 10. How to read source confidence

V1 only supports:

```text
single-provider caveated context
```

That means:

- one provider only
- no second provider
- no conflict check
- no failover
- source confidence is not source truth or validation

## 11. Calendar/event status

Official calendar/event context is not in V1:

```text
calendar_event_source_not_in_v1_scope
```

The panel must not show official CPI/FOMC/NFP/central-bank classification, event blocking, or event-based candidate logic.

## 12. Daily usage

1. Open the package.
2. Run `scriptsun_refresh.bat`.
3. Run or read status via `scripts\check_runtime_status.py`.
4. Open `panel/index.html`.
5. Read latest state, candidate/lifecycle/outcome counts, and caveats only.
6. Do not derive a trade action from the panel.

## 13. Main caveats

- Local execution proof on the user's Windows environment remains separate.
- No new live fetch is claimed in this package.
- API keys must not be stored in chat outputs or artifacts.
- Cache is not source authority.
- Scheduler heartbeat is not production readiness.
- Panel payload is not an action surface.
- Row 2 retained unopened.
- Rows 6–7 deferred re-entry.
- matrix-complete ≠ matrix-open.

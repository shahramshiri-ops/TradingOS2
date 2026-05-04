# Daily Operating Loop — Personal Runtime V1

Generated: `2026-05-04T10:51:03Z`

## Operating principle

Use this package as a **display-only personal observation loop**:

```text
open package → refresh state → check heartbeat/status → open panel → read caveats → stop
```

Do not convert the panel into trade action.

## Morning / session-start loop

1. Open terminal in:

```text
personal_runtime_v1/
```

2. Run refresh:

```bat
scriptsun_refresh.bat
```

3. Check status:

```bash
python scripts/check_runtime_status.py --package-root .
```

4. Open:

```text
panel/index.html
```

5. Confirm these items:

- active instruments are only `XAUUSD`, `EURUSD`, `USDJPY`
- no broker or execution card appears
- candidate count is a count, not a recommendation
- source confidence says single-provider caveated
- calendar/event says not in V1 scope
- heartbeat/last-run status exists

## During the day

Use the panel only as a state snapshot. If the snapshot looks stale, run refresh again. If refresh remains dry-run/cache-first, do not claim that the state is a new live market update.

## End-of-day loop

1. Read `logs/last_run_status.json`.
2. Read `logs/runtime_heartbeat.json`.
3. Read `reports/cache_status.json`.
4. Keep notes outside the package if needed.
5. Do not manually edit runtime state unless a future controlled workflow defines that operation.

## Red lines

Stop using the output as V1 evidence if any of these appear:

- buy/sell/hold
- entry/stop/target
- PnL or win/loss
- broker connection
- order or execution queue
- validation verdict
- adaptation decision
- production-ready claim
- source truth claim
- official calendar/event classification

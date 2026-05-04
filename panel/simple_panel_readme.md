# Simple Panel README

Open `panel/index.html` in a browser after unzipping the package.

This static panel reads from the packaged V1 state generated during Stage 4. It is designed for personal observation only.

## What the panel shows

- Active instruments: XAUUSD, EURUSD, USDJPY
- Latest runtime counts
- Candidate / lifecycle / outcome observation summary
- Source confidence posture: single-provider caveated context
- Calendar/event status: not in V1 scope
- Last refresh and heartbeat status
- Caveats and boundary banner

## What the panel does not contain

- Broker connection
- Order path
- Execution path
- Trading instruction surface
- Position management surface
- Performance/PnL verdict
- Optimizer
- Validation/adaptation decision
- Production-readiness claim

## Refresh flow

Run from package root:

```bash
python scripts/run_refresh.py --package-root . --print-summary
```

Then open:

```text
panel/index.html
```

Current Stage 4 timestamp: `2026-05-04T10:47:46Z`

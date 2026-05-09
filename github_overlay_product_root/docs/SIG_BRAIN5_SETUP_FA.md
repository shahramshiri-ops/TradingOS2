# SIG-BRAIN5 — Upstream Live Context Builder for Brain4

Created: 2026-05-08T14:18:20Z

## What this patch does

SIG-BRAIN5 creates the missing upstream layer:

```text
recent read-only OHLC bars
        ↓
derived live context fields
        ↓
inputs/sig_brain4_live_context_latest.json
        ↓
SIG-BRAIN4 memory matcher
        ↓
mobile brain panel
```

## Run locally

```powershell
py scripts\build_sig_brain5_live_context.py
py scripts\validate_sig_brain5_context_builder.py
```

## Real input requirement

Your existing read-only runtime/fetch layer must write recent bars to:

```text
inputs\sig_brain5_raw_bars_latest.json
```

Required raw surfaces:

```text
EURUSD M15
EURUSD H1
USDJPY M15
USDJPY H1
```

Boundary: display-only; not signal; no buy/sell/hold; no entry/stop/target; no broker/execution.

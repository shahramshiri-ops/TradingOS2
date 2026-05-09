# SIG-BRAIN4 — Runtime Brain Memory Integration & Mobile Display

Created: 2026-05-08T14:11:50Z

## What this adds

This patch adds a file-first runtime brain-memory layer:

1. `data/sig_brain/brain_memory_registry_v1_0.json`
2. `scripts/build_sig_brain4_runtime_payload.py`
3. `runtime/sig_brain/sig_brain4_runtime_payload_current.json`
4. `panel/brain4/index.html`
5. `panel/brain4/assets/*`
6. `.github/workflows/sig_brain4_display_only_mobile_panel.yml`

## What it does

It matches read-only runtime context against active historical brain memories.

Current registry:

- EURUSD_NY_UP_EXTENSION_UPPER_REJECTION_FADE_DOWN_v1_0 — weakened/inactive
- EURUSD_SESSION_UPSIDE_SWEEP_REJECTION_FADE_DOWN_CAVEATED_WATCH_v1_0 — active caveated watch
- USDJPY_ALIGNMENT_ABSENT_CHOP_AVOID_SHORT_CONTEXT_CAVEATED_WATCH_v1_0 — active caveated no-trade watch

## What it does not do

It does not create buy/sell/hold, entries, stops, targets, position sizing, profitability, tradability, broker/execution, clean validation, or probability claims.

## Install

Copy `patch_root/personal_runtime_v1_latest_product/*` into your local `personal_runtime_v1_latest_product` folder.

Then run:

```powershell
py scripts\build_sig_brain4_runtime_payload.py
py scripts\validate_sig_brain4_outputs.py
```

Open:

```text
panel/brain4/index.html
```

## Important input

For real operation, replace:

```text
inputs/sig_brain4_live_context_latest.json
```

with the latest read-only context produced by your runtime. It must contain the required derived fields for each memory.

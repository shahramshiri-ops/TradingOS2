# SIG-E-SHADOW-DETECTOR1-H1-OHLC-HISTORY-HOTFIX

## Problem

After workflow chain integration, detector1 refreshed correctly and passed the regime gate, but stopped at:

`INPUT_INSUFFICIENT / not_enough_h1_rows_for_setup_trigger_window`

This means the detector saw the current SIG-E market state but did not find enough live H1 OHLC history to evaluate setup/trigger.

## Fix

This patch updates detector1 to:

1. Search multiple live-only H1/M15 OHLC candidates.
2. Prefer accumulated / resampled live stores with the most rows.
3. Never use `data/canonical`, `data/raw`, `data/features`, discovery, validation, holdout, or post-2024 research sources.
4. Add candidate diagnostics to the detector output.
5. Add explicit statuses:
   - `LIVE_H1_HISTORY_INSUFFICIENT`
   - `LIVE_M15_HISTORY_INSUFFICIENT`

## Expected next status

After this patch, detector1 should move from vague `INPUT_INSUFFICIENT` to one of:

- `LIVE_H1_HISTORY_INSUFFICIENT` if no live H1 store has enough rows.
- `SETUP_NOT_FORMED`
- `H1_TRIGGER_WAIT`
- `H1_TRIGGER_NOT_CONFIRMED`
- `M15_TRIGGER_WAIT`
- `SHADOW_MATCH_CONFIRMED`

## Boundary

No signal, no trade proposal, no entry/stop/target, no risk sizing, no broker/execution.

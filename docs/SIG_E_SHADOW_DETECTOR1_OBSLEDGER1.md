# SIG-E-SHADOW-DETECTOR1-OBSLEDGER1

## Purpose

This patch adds a live observation ledger for the first SIG-E shadow detector:

`USDJPY / London / Long / H1+M15`

The detector was already accepted as operationally ready for live shadow observation. This patch does not change detector rules. It records the detector's refresh-by-refresh behavior so several months of live operation become analytically useful.

## What it records

- Every detector refresh
- Status counts
- Near-miss statuses
- Shadow match events
- Pending H16 observation windows
- Closed H16 outcomes when live H1 data is available

## Output files

- `state/sig_e_shadow_detector_observation/usdjpy_london_long_obsledger_v1.json`
- `runtime/sig_e/shadow_detector_usdjpy_london_long_obsledger_current.json`
- `panel/brain4/sig_e_shadow_detector_obsledger_status_current.json`
- `outputs/_sig_e_shadow_detector_obsledger1/sig_e_shadow_detector_obsledger1_build_result.json`
- `outputs/_sig_e_shadow_detector_obsledger1/sig_e_shadow_detector_obsledger1_validation_result.json`

## Boundaries

This patch is observation-only. It does not authorize:

- signal
- trade proposal
- entry / stop / target
- risk sizing
- broker execution
- auto execution
- memory promotion
- rule rewrite

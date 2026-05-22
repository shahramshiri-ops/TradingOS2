# SIG-E-RUNTIME-SHADOW-DETECTOR1 — USDJPY London Long H1+M15

## Purpose

This detector observes one historically supported lane in live runtime as **shadow/research only**:

`USDJPY / London / Long / H1 range expansion lower rejection / next H1 direction confirm / M15 inside-H1 directional close confirm`

## Detector statuses

- INPUT_INSUFFICIENT
- DATA_STALE
- SESSION_NOT_MATCHED
- REGIME_NOT_MATCHED
- SETUP_NOT_FORMED
- H1_TRIGGER_WAIT
- H1_TRIGGER_NOT_CONFIRMED
- M15_TRIGGER_WAIT
- SHADOW_MATCH_CONFIRMED
- EXPIRED

## Output files

- `runtime/sig_e/shadow_detector_usdjpy_london_long_current.json`
- `panel/brain4/sig_e_shadow_detector_status_current.json`
- `state/sig_e_shadow_detector/usdjpy_london_long_state_v1.json`

## Authority boundary

This patch does not create or authorize:

- signal
- trade proposal
- entry / stop / target
- risk sizing
- broker execution
- auto execution
- memory promotion

A `SHADOW_MATCH_CONFIRMED` is only a research observation for forward evidence.

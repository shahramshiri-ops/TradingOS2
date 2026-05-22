# SIG-E-SHADOW-PORTFOLIO1

## Purpose

This patch aggregates all current SIG-E shadow detectors into a single live observation status.

It currently covers:

1. `USDJPY London Long H1+M15` — primary shadow observation
2. `USDJPY Asia Short H1+M15` — caveated observation only

## Output files

- `runtime/sig_e/shadow_portfolio_current.json`
- `panel/brain4/sig_e_shadow_portfolio_status_current.json`
- `outputs/_sig_e_shadow_portfolio1/sig_e_shadow_portfolio1_build_result.json`
- `outputs/_sig_e_shadow_portfolio1/sig_e_shadow_portfolio1_validation_result.json`

## What it summarizes

- detector count
- latest status of each detector
- active shadow matches
- caveated active matches
- near-miss totals
- shadow event counts
- pending / closed outcome counts
- data or field attention flags

## Boundary

This is portfolio observation only. It does not authorize:

- signal
- trade proposal
- entry / stop / target
- risk sizing
- broker/execution
- auto execution
- memory promotion
- rule rewrite

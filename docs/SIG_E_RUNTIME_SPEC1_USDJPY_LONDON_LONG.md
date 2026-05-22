# SIG-E-RUNTIME-SPEC1 — USDJPY London Long H1+M15

## Purpose

This patch registers the first SIG-E runtime specification contract for the historically selected lane:

`USDJPY / London / Long / H1 range expansion lower rejection / next H1 direction confirm / M15 inside-H1 directional close confirm`

It is a specification and compatibility layer only.

## Historical carried-forward evidence

- H1 reference validation N: 57
- M15 validation N: 55
- Retention vs H1 reference: 96.4912%
- H1 favorable rate: 56.1404%
- M15 favorable rate: 61.8182%
- Delta favorable: +5.6778 percentage points
- H1 average move: +0.139702 ATR
- M15 average move: +0.306398 ATR
- Delta average move: +0.166696 ATR
- Max validation year share: 30.9091%

## Authority boundary

This patch does **not** create or activate:

- signal
- runtime setup
- runtime trigger
- trade proposal
- entry / stop / target
- risk sizing
- broker integration
- auto execution
- memory promotion

## Next allowed step

Only after review:

`SIG-E-RUNTIME-SHADOW-DETECTOR1_USDJPY_LONDON_LONG_H1_M15`

That future step must remain shadow-only unless separately authorized by governance.

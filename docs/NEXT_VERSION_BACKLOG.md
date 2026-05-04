# Next Version Backlog — Post-V1 Candidates

Generated: `2026-05-04T10:51:03Z`

This backlog is not part of V1. It records possible future work without upgrading V1 authority.

## Candidate next-version items

### 1. Local execution proof pack

Goal: prove that `run_refresh.bat`, `run_refresh.py`, `check_runtime_status.py`, and `generate_panel_payload.py` run correctly on the user's Windows environment.

Boundary: local script proof only; not production readiness.

### 2. Credential-safe local live refresh

Goal: optional local environment variable based provider refresh with redacted outputs.

Boundary: no API key in chat, no real `.env` attached, no secret in output.

### 3. Current detailed candidate row store

Goal: package a current 4-row candidate/lifecycle/outcome store if produced by the runtime.

Boundary: no reconstruction from old mismatched summaries.

### 4. Cache feed plan completion

Goal: clarify whether `XAUUSD M5` should be added through a controlled upstream runtime/cache change.

Boundary: no fabricated cache surface in V1.

### 5. Optional source confidence expansion

Goal: evaluate second provider / conflict check / divergence / failover.

Boundary: future scope only; not V1 source truth.

### 6. Optional calendar/event context

Goal: evaluate lightweight calendar/event context.

Boundary: future scope only; no official event risk in V1.

### 7. Better panel UX

Goal: improve display clarity, filters, and state explanations.

Boundary: no action buttons, no trade surface.

### 8. Packaging installer / one-click launcher

Goal: make Windows launch easier.

Boundary: no background production scheduler claim unless separately proven.

### 9. Historical path integration note

Goal: document how historical learning/replay outputs may be viewed alongside runtime observation.

Boundary: historical path is not a V1 runtime blocker and must not become validation verdict.

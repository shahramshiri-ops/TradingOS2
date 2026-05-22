# SIG-E-SHADOW-COVERAGE1 — Lane Eligibility / Dropoff Coverage Monitor

Purpose:
Track where each live shadow lane drops off across refreshes.

This does not change detector rules. It reads the existing observation ledgers and classifies every refresh into a gate/dropoff stage:

- freshness gate
- session gate
- regime gate
- data/reference gate
- setup gate
- H1 trigger gate
- M15 confirm gate
- shadow match gate

Outputs:
- `runtime/sig_e/shadow_coverage1_current.json`
- `panel/brain4/sig_e_shadow_coverage1_current.json`
- `outputs/_sig_e_shadow_coverage1/sig_e_shadow_coverage1_current.json`
- `outputs/_sig_e_shadow_coverage1/sig_e_shadow_coverage1_current.md`

Why it matters:
Before adding more lanes or loosening rules, this tells us whether the current lanes are too narrow, out of session, data-blocked, regime-blocked, or simply waiting for rare setup events.

Boundary:
Coverage/dropoff monitor only. No signal, no trade proposal, no entry/stop/target, no risk sizing, no broker/execution, no auto execution.

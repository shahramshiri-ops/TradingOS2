# SIG-E-SHADOW-OBSREPORT1

Builds a daily/weekly/all-time observation report from the SIG-E shadow ledgers.

Outputs:
- `runtime/sig_e/shadow_observation_report_current.json`
- `panel/brain4/sig_e_shadow_observation_report_current.json`
- `outputs/_sig_e_shadow_report1/sig_e_shadow_observation_report_current.json`
- `outputs/_sig_e_shadow_report1/sig_e_shadow_observation_report_current.md`

It summarizes:
- last 24h / last 7d / all-time status counts
- near-miss / progress counts
- shadow event counts
- pending/closed outcome counts
- current portfolio status

Boundary: report-only, not signal, no trade proposal, no entry/stop/target, no risk sizing, no broker/execution.

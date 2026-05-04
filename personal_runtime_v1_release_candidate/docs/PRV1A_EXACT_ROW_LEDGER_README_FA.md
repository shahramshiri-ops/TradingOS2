# PRV1A Exact Row-Level Ledger Patch

وضعیت: Accepted with Caveats / Exact 4-Row Ledger Completed

این patch دو row قبلی را که به‌صورت aggregate shell بودند، با فایل‌های current SOT-02 کامل کرد. اکنون هر ۴ candidate دارای identity دقیق، instrument، timeframe، trigger UTC، lifecycle status و outcome observation هستند.

## اجرا / مشاهده

- پنل دقیق: `personal_runtime_v1/panel/index_row_level_exact.html`
- ledger دقیق: `personal_runtime_v1/ledger/candidate_observation_ledger_v1_exact.json`
- validation: `personal_runtime_v1/proofs/exact_row_level_validation_result.json`

## مرزها

این ledger فقط observation-only است؛ نه signal، نه buy/sell/hold، نه entry/stop/target، نه execution، نه PnL/win-loss، نه validation verdict و نه production readiness.

# PRV1A-01 — Row-Level Observation Ledger Sprint

## Verdict

Accepted with Caveats / Row-Level Ledger Built with Partial Exact Row Resolution

## چه ساخته شد؟

این patch، PRV1 را از نمایش صرفاً عددی به یک ledger قابل بازرسی تبدیل می‌کند. خروجی اصلی:

- `ledger/candidate_observation_ledger_v1.json`
- `ledger/candidate_lifecycle_rows_v1.json`
- `ledger/outcome_observation_rows_v1.json`
- `ledger/active_tracking_rows_v1.json`
- `ledger/candidate_evidence_index_v1.json`
- `panel/row_level_panel_payload_v1.json`
- `panel/index_row_level.html`
- `proofs/row_level_boundary_proof.json`

## وضعیت rowها

- exact rows: 2
- aggregate shell rows: 2
- candidate/lifecycle rows: 4
- final outcomes: 3
- active tracking: 1

## چرا فقط دو row exact است؟

artifactهای فعلی current countها را با ۴ candidate ثابت می‌کنند، اما registry/state کامل ۴ row را ارائه نمی‌کنند. دو row با شناسه دقیق پیدا شد؛ دو row دیگر فقط از aggregate current-state ثابت هستند. برای جلوگیری از جعل، instrument/timeframe/candidate_id آن‌ها unresolved نگه داشته شده است.

## فایل لازم برای exact کامل

برای تبدیل دو shell row به exact row، فایل‌های current SOT02 registry/lifecycle state از مسیر local runtime لازم است، نه API key و نه secret.

## Boundary

این ledger signal، پیشنهاد معامله، اجرای معامله، PnL، win/loss، validation verdict، adaptation decision یا production-readiness نیست.

# راهنمای اجرای PRV1 — Release Candidate

## دستور اصلی

در ویندوز وارد پوشهٔ release candidate شو و فقط این را اجرا کن:

```bat
RUN_DAILY.bat
```

این دستور به‌ترتیب این مسیر را اجرا می‌کند:

1. preflight
2. staged credentialed refresh
3. cache validation
4. post-refresh lifecycle update
5. candidate detection از cache محلی
6. panel/status/proofs نهایی

## خروجی‌های اصلی بعد از اجرا

- `panel/panel_payload_after_daily_runtime.json`
- `panel/index_daily_runtime.html`
- `logs/last_run_status_after_daily_runtime.json`
- `logs/runtime_heartbeat_after_daily_runtime.json`
- `proofs/daily_runtime_local_validation_result.json`

## وضعیت آخرین proof پذیرفته‌شده

- candidate_count: 4
- lifecycle_count: 4
- final_outcome_count: 3
- active_tracking_count: 1
- new_observation_candidate_count: 0

## مرزها

این سیستم observation-only است. سیگنال، توصیه معامله، خرید/فروش/نگهداری، entry/stop/target، broker، order، execution، PnL، win/loss، optimizer، validation verdict یا production readiness نیست.

API key را در چت نفرست. فقط باید به‌صورت local environment variable با نام `LFB_TWELVE_DATA_API_KEY` روی سیستم خودت باشد.

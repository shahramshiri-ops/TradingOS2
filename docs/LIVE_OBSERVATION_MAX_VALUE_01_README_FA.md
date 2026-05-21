# LIVE_OBSERVATION_MAX_VALUE_01 — لایه ثبت شواهد زنده برای چند ماه observation

این پچ برای این ساخته شده که اگر سیستم چند هفته یا چند ماه به صورت live روشن بماند، خروجی آن فقط چند عدد پراکنده یا پنل لحظه‌ای نباشد؛ بلکه به یک بسته شواهد forward-observation قابل review تبدیل شود.

## کارهایی که اضافه می‌شود

- ثبت وضعیت هر memory در هر refresh: `MATCHED_ACTIVE`, `NOT_MATCHED`, `NEAR_MISS`, `INPUT_INSUFFICIENT`, `DATA_OR_CONTEXT_NOT_READY`, `NOT_RUNTIME_ACTIVE`
- ساخت ledger رسمی eventها و snapshot کوچک context هنگام فعال بودن eventها
- ثبت near-miss و blocker rollup برای کشف اینکه کدام شرط‌ها دائماً مانع activation می‌شوند
- ثبت provider/data-health برای اینکه بعداً مشخص باشد مشکل از بازار بوده یا data freshness / pipeline
- ثبت baseline/control exposure denominator بر اساس instrument/timeframe/session؛ این baseline عملکردی نیست، فقط denominator پژوهشی است
- ساخت daily / weekly / monthly review pack

## فایل‌های اصلی بعد از هر refresh

```text
panel/brain4/live_observation_current.json
panel/brain4/live_memory_evaluation_current.json
panel/brain4/live_event_ledger_current.json
panel/brain4/live_observation_daily_summary_current.json
panel/brain4/live_observation_weekly_summary_current.json
panel/brain4/live_observation_monthly_review_pack_current.json
state/live_observation/live_observation_state_v1.json
```

## مرزهای غیرقابل تغییر

این پچ سیگنال نمی‌سازد، memory را promote/demote نمی‌کند، قانون را تغییر نمی‌دهد، خرید/فروش یا entry/stop/target نمی‌دهد و به بروکر وصل نیست.

## بعد از یک ماه چه کار باید کرد؟

فایل زیر را برای review بردارید:

```text
panel/brain4/live_observation_monthly_review_pack_current.json
```

در review ماهانه باید بررسی شود:

- کدام memory واقعاً در live فعال شده؟
- کدام‌ها فقط near-miss داشته‌اند؟
- کدام‌ها input/context insufficient داشته‌اند؟
- آیا داده تازه و قابل اتکا بوده؟
- outcomeها فقط observation بوده‌اند یا قابل مقایسه با baseline بعدی هستند؟

تصمیم‌های مجاز فقط بعد از review جداگانه:

```text
KEEP_AS_DISPLAY_CONTEXT
KEEP_AS_CAVEATED_WATCH
PROMOTE_TO_SETUP_TRIGGER_PILOT_REVIEW_ONLY
DEMOTE_TO_EXTENDED_OBSERVATION
PARK_NO_RUNTIME_USE
REJECT_OR_ARCHIVE
NEEDS_RESEARCH_RESPEC
```

هیچ تصمیمی خودکار نیست.

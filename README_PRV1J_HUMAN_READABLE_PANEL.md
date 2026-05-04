# PRV1J — Human-Readable Market State Panel Patch

این patch پنل موبایل را از حالت عددی/Proof-محور به پنل قابل‌فهم روزانه تبدیل می‌کند.

## نصب

محتویات این ZIP را در root repo فعلی `TradingOS2` extract کن، همان جایی که این فایل‌ها هستند:

```text
RUN_DAILY.bat
scripts/
.github/
config/
```

بعد commit و push کن. سپس workflow را یک بار دستی اجرا کن تا GitHub Pages دوباره ساخته شود.

## چه چیزی تغییر می‌کند؟

- `scripts/generate_mobile_pages_site_with_real_refresh_button.py` حالا یک پنل فارسی راست‌چین و قابل‌فهم می‌سازد.
- دکمهٔ Refresh واقعی حفظ می‌شود.
- متن‌های انگلیسی/فنی مثل `XAUUSD H1` یا `active_tracking` در spanهای LTR جدا می‌شوند تا متن فارسی خراب نشود.
- فایل‌های public جدید ساخته می‌شود:
  - `market_state_public.json`
  - `active_watch_public.json`
  - `latest_changes_public.json`
  - `plain_language_fa.json`

## مرزها

این patch هیچ signal، broker، execution، entry/stop/target، PnL، optimizer، validation verdict یا production-readiness claim اضافه نمی‌کند.

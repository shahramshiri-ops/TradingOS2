# PRV1M-RC1 — Active Watch Lifecycle Reclassification Fix

## مسئله
در پنل موبایل، Active Watch برای `XAUUSD H1` بعد از چند ساعت هنوز می‌گفت:

`no_completed_post_trigger_bars_available_yet`

در حالی که cache تازهٔ `XAUUSD H1` کندل‌های بعد از trigger را داشت. این یعنی مشکل از بازار نبود؛ مشکل از lifecycle updater بود.

## علت
نسخهٔ قبلی `run_post_refresh_candidate_lifecycle_update.py` فقط در سطح بالای فایل cache دنبال `values` یا `data` می‌گشت. بعضی cache snapshotها bars را داخل envelopeهای nested مثل `provider_payload.values` نگه می‌دارند. در نتیجه lifecycle updater ممکن بود cache را ظاهراً داشته باشد، اما bars را نخواند و active row را اشتباهاً با دلیل «کندل کافی موجود نیست» نگه دارد.

## اصلاح
این patch:

- cache reader را recursive می‌کند؛
- داخل `values`, `data`, `bars`, `records`, `candles`, `provider_payload`, `response`, `payload` و ساختارهای nested دنبال OHLC bars می‌گردد؛
- برای active lifecycle تعداد valid cache bars و post-trigger bars را در report ثبت می‌کند؛
- validator را سخت‌تر می‌کند تا اگر cache بعد از trigger کندل دارد ولی row هنوز reason قدیمی دارد، validation fail شود؛
- هیچ provider call جدید، secret read، broker، execution، signal، PnL یا validation verdict معاملاتی اضافه نمی‌کند.

## اجرا
بعد از extract کردن patch روی repo/package فعلی:

```bat
RUN_DAILY.bat
```

یا برای تست فقط post-refresh update:

```bat
scripts\run_post_refresh_candidate_lifecycle_update.bat
python scripts\validate_post_refresh_update_outputs.py .
```

بعد workflow را اجرا کن و پنل را refresh کن.

## انتظار
اگر cache واقعاً کندل‌های بعد از trigger دارد، Active Watch دیگر نباید با دلیل «کندل کافی بعد از trigger نیست» باقی بماند. باید یا final outcome بگیرد، یا با reason دقیق‌تری active بماند.

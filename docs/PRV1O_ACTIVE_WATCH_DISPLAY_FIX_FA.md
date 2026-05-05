# PRV1O — اصلاح خوانایی Active Watch

این patch برای دو مشکل نمایشی ساخته شده است:

1. ردیف‌های تازهٔ PRV1E در Active Watch دلیل خام `new_observation_candidate_seeded_by_prv1e_rule_engine_not_final` نشان می‌دادند.
2. ردیف‌های تازه‌ای که `trigger_bar_from_cache` داشتند، سطح‌های مرجع High/Low/Close را در پنل به‌صورت `—` نشان می‌دادند.

این patch کاری به منطق معامله، سیگنال، execution، PnL یا validation ندارد. فقط نمایش Active Watch را قابل‌فهم‌تر می‌کند.

## بعد از نصب چه چیزی باید تغییر کند؟

برای ردیف‌های فعال مثل `EURUSD H1` یا `XAUUSD M15` باید به‌جای متن خام، توضیح فارسی ببینی:

> این observation تازه در همین اجرای rule engine از cache ساخته شده و هنوز outcome نهایی ندارد؛ در اجرای بعدی دوباره بررسی می‌شود.

همچنین کارت‌های مرجع باید عددهای High/Low/Close را از `trigger_bar_from_cache` نشان دهند.

## نصب

فایل‌های patch را در root repo قرار بده، commit/push کن و workflow را یک بار دستی اجرا کن.

بعد پنل را با cache-bust باز کن:

`https://shahramshiri-ops.github.io/TradingOS2/?v=prv1o`

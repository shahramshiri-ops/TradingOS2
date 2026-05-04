# راهنمای کاربر — Personal Runtime V1

Generated: `2026-05-04T10:51:03Z`  
Program: `PRV1-01 — Personal Runtime V1 Final Productization Program`

## 1. این بسته چیست؟

`personal_runtime_v1` یک بستهٔ شخصی برای مشاهدهٔ آخرین وضعیت runtime است. هدف آن ساده است:

```text
run / refresh → latest state → candidate / lifecycle / outcome state → panel payload → display-ready files
```

این بسته فقط یک سطح مشاهدهٔ شخصی و display-only است. خروجی‌ها سیگنال، توصیهٔ معامله، خرید/فروش/نگهداری، ورود/حدضرر/هدف، سفارش، اجرا، اتصال بروکر، PnL، win/loss، اعتبارسنجی، تصمیم تطبیق یا ادعای آماده‌بودن production نیستند.

## 2. پوشه را چطور باز کنم؟

بعد از unzip کردن بسته، وارد این مسیر شو:

```text
personal_runtime_v1/
```

ساختار اصلی:

```text
config/   تنظیمات فعال V1
state/    وضعیت runtime، candidate/lifecycle، outcome
panel/    payload و پنل static
logs/     heartbeat و last run status
scripts/  اسکریپت‌های refresh/status/panel generation
reports/  گزارش‌ها و cache status
proofs/   proofهای مرزی و dry-run
```

## 3. چطور refresh کنم؟

روی Windows:

```bat
cd personal_runtime_v1
scriptsun_refresh.bat
```

یا با Python:

```bash
cd personal_runtime_v1
python scripts/run_refresh.py --package-root . --print-summary
python scripts/check_runtime_status.py --package-root .
```

این refresh در V1 مسیر **cache-first / state-first** دارد. یعنی از فایل‌های موجود داخل package استفاده می‌کند و بدون credential معتبر local نباید ادعای live fetch بسازد.

## 4. پنل را چطور ببینم؟

این فایل را با مرورگر باز کن:

```text
personal_runtime_v1/panel/index.html
```

یا خلاصهٔ متنی را بخوان:

```text
personal_runtime_v1/panel/panel_summary_v1.md
```

## 5. instrumentهای فعال V1

فقط این سه instrument فعال هستند:

- `XAUUSD`
- `EURUSD`
- `USDJPY`

`SPX` و `NQ` از active V1 حذف شده‌اند. نباید به‌عنوان blocked daily noise در پنل نمایش داده شوند.

## 6. وضعیت فعلی runtime در این package

- candidate count: `4`
- lifecycle count: `4`
- active tracking count: `1`
- final outcome observations: `3`

این اعداد summary هستند. اگر detailed row-level candidate store در اختیار package نباشد، package حق ندارد آن را از روی summary جعل یا بازسازی کند.

## 7. candidate یعنی چه؟

در V1، candidate یعنی یک **شیء مشاهده‌ای در lifecycle** که برای نمایش و مرور وضعیت ساخته شده است.

Candidate این‌ها نیست:

- توصیهٔ معامله
- buy / sell / hold
- نقطهٔ ورود
- stop / target
- allocation / size
- order یا execution
- verdict برای اعتبارسنجی

## 8. lifecycle یعنی چه؟

Lifecycle یعنی وضعیت مشاهده‌ای candidate در مسیر runtime. این tracking، execution tracking نیست. یعنی سیستم نمی‌گوید معامله‌ای باز شده، بسته شده، سود کرده یا ضرر کرده است.

## 9. outcome observation یعنی چه؟

Outcome observation فقط یک مشاهدهٔ توصیفی بعد از lifecycle است. این مفهوم نباید به PnL، win/loss، trade result، model approval یا validation verdict تبدیل شود.

در این بسته:

- final outcome recorded: `3`
- active tracking: `1`

## 10. source confidence را چطور بخوانم؟

در V1 فقط این حالت داریم:

```text
single-provider caveated context
```

یعنی:

- فقط یک provider در scope است.
- source دوم نداریم.
- conflict check نداریم.
- failover نداریم.
- این confidence، source truth یا validation نیست.

## 11. calendar/event در V1

Calendar/event رسمی در V1 نیست:

```text
calendar_event_source_not_in_v1_scope
```

بنابراین پنل نباید official CPI/FOMC/NFP/central-bank risk، event blocking یا event-based candidate logic نشان دهد.

## 12. هر روز چطور استفاده کنم؟

1. package را باز کن.
2. `scriptsun_refresh.bat` را اجرا کن.
3. `scripts\check_runtime_status.py` را اجرا کن یا خروجی status را بخوان.
4. `panel/index.html` را باز کن.
5. فقط latest state، candidate/lifecycle/outcome counts و caveatها را بخوان.
6. هیچ تصمیم معامله‌ای را از این panel استخراج نکن.

## 13. مهم‌ترین caveatها

- local execution proof روی سیستم کاربر هنوز جداگانه است.
- live fetch جدید در این بسته claim نشده.
- API key نباید داخل چت یا artifact ذخیره شود.
- cache، source authority نیست.
- scheduler heartbeat، production readiness نیست.
- panel payload، action surface نیست.
- Row 2 retained unopened.
- Rows 6–7 deferred re-entry.
- matrix-complete ≠ matrix-open.

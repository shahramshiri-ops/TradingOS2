# TRADINGOS_UI_WORKFLOW_HYGIENE_04

هدف این پچ: تمیز کردن سطح نمایش اصلی پنل و رفع وابستگی‌های workflow قدیمی که باعث ابهام در deploy/freshness می‌شدند.

## تغییرات اصلی

1. صفحه اصلی Brain4 دیگر به‌صورت پیش‌فرض پنل‌های shadow/outcome/diagnostic را load نمی‌کند.
2. پنل‌های diagnostic فقط با افزودن `?debug=1` یا `?diagnostics=1` به آدرس صفحه load می‌شوند.
3. workflow اصلی live refresh همچنان بعد از refresh به‌صورت explicit workflow deploy صفحات را trigger می‌کند، اما step قدیمی وابسته به `steps.commit_generated.outputs.changed` حذف شده است.
4. workflow پنل Brain4 نیز بدون وابستگی stale به `commit_generated.outputs.changed`، بعد از build موفق، deploy Pages را trigger می‌کند.
5. safe commit scope برای sync کردن JSONهای کوچک freshness/audit گسترش یافته است:
   - `runtime/sig_brain/*.json`
   - `data/live_m5/incremental/*.json`
   - `data/live_m5/reports/*.json`

## مرزهای ثابت

این پچ هیچ مجوزی برای signal، buy/sell، entry/stop/target، position sizing، broker/execution، auto-learning یا rule rewrite ایجاد نمی‌کند.

## تست محلی

بعد از اعمال فایل‌ها، از ریشه repo اجرا کن:

```powershell
python scripts/validate_tradingos_ui_workflow_hygiene_04.py
```

باید خروجی `PASS` بدهد و فایل proof زیر ساخته شود:

```text
proofs/tradingos_ui_workflow_hygiene_04_validation_result.json
```

## روش دیدن debug panels

آدرس عادی صفحه فقط active events / library / history رسمی را نشان می‌دهد.
برای دیدن diagnostic/shadow panels، انتهای آدرس پنل این را اضافه کن:

```text
?debug=1
```

مثال:

```text
https://shahramshiri-ops.github.io/TradingOS2/panel/brain4/?debug=1
```

# راهنمای PRV1J — پنل قابل‌فهم و راست‌چین

## کار لازم

1. Patch را روی root repo فعلی extract کن.
2. با GitHub Desktop commit/push کن.
3. در GitHub Actions، workflow را دستی اجرا کن.
4. لینک GitHub Pages را refresh کن.

## خروجی مورد انتظار

پنل باید به‌جای فقط عددها، این‌ها را نشان دهد:

- برداشت ساده به فارسی
- Active Watch
- وضعیت هر ابزار و تایم‌فریم
- cache و provider status
- توضیح اینکه outcomeها چه معنی دارند و چه معنی ندارند

## RTL

صفحه با `lang="fa"` و `dir="rtl"` ساخته می‌شود. عبارت‌های فنی انگلیسی با `dir="ltr"` جدا شده‌اند تا متن مخلوط فارسی/انگلیسی به‌هم نریزد.

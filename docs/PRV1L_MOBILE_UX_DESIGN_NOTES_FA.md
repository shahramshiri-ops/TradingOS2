# PRV1L Design Notes

مشکل نسخهٔ قبلی این بود که داده‌ها درست بودند، اما presentation روی موبایل حرفه‌ای نبود: تیترهای بزرگ، جدول‌های شکسته، متن زیاد، و سلسله‌مراتب بصری ضعیف.

PRV1L این موارد را اصلاح می‌کند:

1. Header sticky و خلاصهٔ خیلی کوتاه.
2. Metric bar compact.
3. Active Watch به عنوان مهم‌ترین کارت.
4. Freshness بدون table؛ هر surface یک row compact.
5. Instrument sections به صورت accordion.
6. No Candidate و توضیحات طولانی در بخش قابل باز شدن.
7. عبارت‌های فنی مثل `XAUUSD H1`، `UTC`، `bars` با جهت LTR ایزوله می‌شوند.

این patch منطق معاملاتی جدید اضافه نمی‌کند.

# PRV1L — Professional Mobile Dashboard Redesign

این patch فقط ظاهر و تجربهٔ کاربری پنل موبایل را حرفه‌ای‌تر می‌کند. منطق refresh، candidate detection، lifecycle update و Cloudflare refresh button همان مسیر پذیرفته‌شدهٔ قبلی را حفظ می‌کند.

## نصب

محتویات patch را در root repo `TradingOS2` بریز و commit/push کن.

فایل‌های مهم:

- `scripts/generate_mobile_pages_site_professional_dashboard.py`
- `scripts/generate_mobile_pages_site_with_real_refresh_button.py`
- `config/professional_mobile_dashboard_policy.json`
- `docs/PRV1L_PROFESSIONAL_DASHBOARD_SETUP_FA.md`

بعد workflow را از GitHub Actions اجرا کن و GitHub Pages را refresh کن.

## خروجی

پنل جدید:

- جدول‌های سنگین را حذف می‌کند.
- Freshness را با row/cardهای جمع‌وجور نشان می‌دهد.
- Active Watch را به بخش hero تبدیل می‌کند.
- ابزارها را به صورت accordion نمایش می‌دهد.
- متن‌های طولانی را کوتاه‌تر و collapse می‌کند.
- RTL/LTR را بهتر مدیریت می‌کند.

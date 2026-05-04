# PRV1K — Enhanced Market State Panel

این patch شش بهبود را اضافه می‌کند:

1. Active Watch Reference Levels
2. Run-to-Run Change Log
3. Freshness & Coverage Card
4. No Candidate Explanation
6. Attention Priority — نه سیگنال
7. RTL / UX polish

## نصب

محتویات patch را در root repo بریز، commit و push کن، سپس workflow فعلی را Run کن.

مسیر اصلی workflow همان است:

```text
.github/workflows/prv1_daily_runtime_mobile_panel.yml
```

چون workflow قبلاً این دستور را اجرا می‌کند، نیازی به تغییر workflow نیست:

```text
python scripts/generate_mobile_pages_site_with_real_refresh_button.py .
```

## مرزها

این patch هیچ broker، execution، signal، buy/sell/hold، entry/stop/target، PnL، optimizer، validation verdict یا production-readiness claim نمی‌سازد.

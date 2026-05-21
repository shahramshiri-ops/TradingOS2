# SHADOW_CANDIDATE_OUTCOME_BASELINE_01

این پچ برای کاندیدهای `SHADOW_CANDIDATE_UNIVERSE_01` یک لایه outcome و baseline پژوهشی می‌سازد.

## هدف

بعد از فعال شدن یک shadow candidate، سیستم باید در refreshهای بعدی بداند:

- outcome در H1+1 / H1+2 / H1+4 / H1+8 چه شده است؛
- outcome نسبت به baseline ساده همان instrument/session/direction چه وضعی دارد؛
- هر candidate چند بار evaluate شده، چند بار active شده، چند بار near-miss شده، و چند outcome بسته شده است؛
- آیا candidate فقط باید در shadow ادامه پیدا کند یا برای review انسانی آماده شده است.

## مرزهای ثابت

این پچ:

- memory رسمی نمی‌سازد؛
- candidate را promotion نمی‌دهد؛
- سیگنال، خرید/فروش، entry/stop/target، position size، PnL، profitability یا broker/execution ندارد؛
- هیچ ruleای را خودکار تغییر نمی‌دهد.

## فایل‌های مهم

```text
state/shadow_candidate_outcome_baseline/shadow_candidate_outcome_baseline_state_v1.json
panel/brain4/shadow_candidate_outcome_baseline_summary_current.json
panel/brain4/shadow_candidate_promotion_review_current.json
panel/brain4/shadow_candidate_outcome_baseline_research_pack_current.json
runtime/sig_shadow_candidate_outcome_baseline/shadow_candidate_outcome_baseline_current.json
```

## نکته UI

این پچ نباید صفحه اصلی پنل را شلوغ کند. خروجی‌ها برای review/research هستند و فقط از طریق JSONها یا بعداً debug/research dashboard قابل استفاده‌اند.

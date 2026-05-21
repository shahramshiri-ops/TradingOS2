# SHADOW_CANDIDATE_UNIVERSE_01 — بانک کاندیدهای پژوهشی برای live shadow

این پچ برای حل یک مشکل مهم ساخته شده است: تعداد memoryهای رسمی کم است و ممکن است در چند ماه live، eventهای کمی فعال شوند. راه‌حل این پچ زیاد کردن memoryهای رسمی نیست؛ بلکه اضافه کردن یک لایه میانی است:

```text
Shadow Candidate Universe
```

## معنی عملی

- candidateهای بیشتری در هر refresh بررسی می‌شوند.
- فقط اگر شروط pre-registered آن‌ها برقرار باشد، به عنوان `shadow-only candidate` وارد دفتر observation می‌شوند.
- در پنل اصلی به عنوان event یا سیگنال نمایش داده نمی‌شوند.
- memory رسمی ساخته نمی‌شود.
- هیچ ruleای تغییر نمی‌کند.
- هیچ خرید/فروش، entry، stop، target یا broker/execution مجاز نیست.

## چرا H1-first؟

نسخه اول عمداً H1-native است، چون context فعلی برای H1 فیلدهای قیمت بسته‌شده مثل `h1_close` دارد و outcome observer موجود می‌تواند H1+1 / H1+2 / H1+4 / H1+8 را به شکل observation-only ببندد.

M15 candidate universe بهتر است بعداً اضافه شود، وقتی price-anchor و closed-bar outcome hooks برای M15 صریح‌تر شوند.

## فایل‌های مهم

```text
config/shadow_candidate_universe_01_registry.json
state/shadow_candidate_universe/shadow_candidate_universe_state_v1.json
runtime/sig_shadow_candidate_universe/shadow_candidate_universe_current.json
runtime/sig_shadow_candidate_universe/shadow_candidate_universe_evaluations_current.json
runtime/sig_shadow_candidate_universe/shadow_candidate_universe_signal_intake_current.json
panel/brain4/shadow_candidate_universe_summary_current.json
panel/brain4/shadow_candidate_universe_review_pack_current.json
```

## چه چیزی وارد shadow observation می‌شود؟

فقط candidateهایی که در همان refresh کاملاً active شوند، به intake زیر می‌روند:

```text
runtime/sig_shadow_candidate_universe/shadow_candidate_universe_signal_intake_current.json
```

سپس با همان ابزار موجود shadow ledger ثبت می‌شوند تا outcomeهای آینده به شکل observation-only بسته شوند.

## تصمیم‌های مجاز بعد از چند هفته/ماه

بعد از review جداگانه، نه خودکار:

```text
KEEP_SHADOW_ONLY
PARK_SHADOW_CANDIDATE
REJECT_SHADOW_CANDIDATE
RESPECIFY_AS_NEW_CANDIDATE_VERSION
NOMINATE_FOR_CAVEATED_MEMORY_WATCH_REVIEW_ONLY
```

## تصمیم‌های ممنوع

```text
CREATE_SIGNAL
AUTHORIZE_TRADE
AUTO_PROMOTE_MEMORY
CHANGE_RULE_AFTER_SEEING_OUTCOME
OPEN_HOLDOUT_AUTOMATICALLY
```

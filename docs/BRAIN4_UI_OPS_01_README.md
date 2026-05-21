# BRAIN4-UI-OPS-01 — Visual & UX Polish

این patch فقط UI/UX را بهبود می‌دهد و هیچ authority یا منطق سیگنال را تغییر نمی‌دهد.

## مواردی که از روی پنل فعلی اصلاح می‌شود

- hierarchy ضعیف بین Shadow / Hero / Library
- شلوغی بیش از حد Shadow diagnostics
- badgeها و buttonها با ظاهر ناهماهنگ
- empty state کم‌قدرت و کم‌وضوح
- pattern cardها با spacing و typography ضعیف
- تراکم زیاد متن‌های توضیحی
- مرزبندی ضعیف بین sectionها

## خروجی

- shadow section hierarchy بهتر و card polish
- active event / empty state خواناتر
- library section و pattern cards تمیزتر
- pill/button style یکپارچه
- section eyebrow labels
- long text clamp برای cardهای pattern
- details style بهبود یافته

Boundary:

- UI_ONLY_PATCH
- NOT_SIGNAL
- NO_BUY_SELL
- NO_ENTRY_STOP_TARGET
- NO_BROKER_EXECUTION
- NO_AUTO_LEARNING
- NO_RULE_REWRITE

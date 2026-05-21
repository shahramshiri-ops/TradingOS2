# SIG-E-REGIME1 — قرارداد لایه Market State / Regime Runtime

## هدف

این پچ اولین لایه اجرایی بعد از `SIG-E-ARCH1` است و برای معماری هدف E ساخته شده است:

```text
Manual / Semi-Automated Trading Decision System
```

اما خروجی این مرحله هنوز فقط **context** است.

این لایه به سیستم کمک می‌کند به‌جای اینکه مستقیماً از memory یا field خام به setup برسد، ابتدا بفهمد بازار فعلی در چه وضعیت مکانیکی قرار دارد:

```text
trend / range / chop / compression / expansion
volatility state
D1/H4/H1 alignment
liquidity context
tradeability context
```

## مرز ثابت

`REGIME1` هیچ‌کدام از موارد زیر را تولید یا مجاز نمی‌کند:

```text
signal
buy/sell
entry
stop
target
risk percent
position sizing
broker integration
execution
auto trading
```

خروجی آن فقط برای مصرف لایه‌های آینده مانند `SETUP1`, `TRIGGER1`, `BLOCKER1`, `QUALITY_VECTOR1` است.

## خروجی‌های اصلی

```text
runtime/sig_e/market_state_current.json
runtime/sig_e/sig_e_regime1_market_state_current.json
panel/brain4/sig_e_market_state_current.json
outputs/_sig_e_regime1/sig_e_regime1_build_result.json
outputs/_sig_e_regime1/sig_e_regime1_validation_result.json
```

این فایل‌ها نباید در صفحه اصلی پنل به‌عنوان رویداد معاملاتی نمایش داده شوند. در صورت نیاز، فقط برای debug/research قابل استفاده‌اند.

## منطق کلی

ورودی اصلی از Brain5 context گرفته می‌شود:

```text
runtime/sig_brain/sig_brain5_derived_context_latest.json
```

و اگر موجود نبود، fallback می‌کند به:

```text
inputs/sig_brain4_live_context_latest.json
```

برای هر surface، سیستم این موارد را مکانیکی می‌سازد:

```text
trend_state
range_state
volatility_state
htf_alignment
liquidity_context
tradeability_context
setup_relevance_hints
```

## قانون مهم

`tradeability_context = REGIME_SUPPORTIVE` به معنی پیشنهاد معامله نیست.

فقط یعنی از نظر regime، داده به اندازه کافی قابل خواندن است و مانع مکانیکی واضحی در همین لایه دیده نشده است.

تصمیم معاملاتی فقط در مراحل آینده، بعد از setup، trigger، blocker، quality vector، signal candidate، trade plan و manual review ممکن است بررسی شود.

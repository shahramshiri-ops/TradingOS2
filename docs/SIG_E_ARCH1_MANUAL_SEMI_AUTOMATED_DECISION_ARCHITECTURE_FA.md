# SIG-E-ARCH1 — قرارداد معماری سیستم تصمیم‌یار معاملاتی دستی / نیمه‌خودکار

وضعیت: `ARCHITECTURE_CONTRACT_ACTIVE_NOT_RUNTIME_SIGNAL`

این پچ هدف معماری پروژه را از «پنل memory / مشاهده‌گر» به سمت **سیستم تصمیم‌یار معاملاتی دستی / نیمه‌خودکار** رسمی می‌کند؛ اما runtime فعلی هنوز **سیگنال معاملاتی، پیشنهاد معامله، entry/stop/target، sizing، broker یا execution** تولید نمی‌کند.

## تعریف معماری هدف

Target Architecture: `E_MANUAL_SEMI_AUTOMATED_TRADING_DECISION_SYSTEM`

مسیر هدف:

```text
Live Data
→ Market Regime
→ Memory Match
→ Setup Detection
→ Trigger Detection
→ Blocker Check
→ Quality Vector
→ Signal Candidate
→ Trade Plan Draft
→ Risk Model
→ Manual Review
→ Forward Shadow / Journal
```

## مرز فعلی runtime

```text
CURRENT_RUNTIME_NOT_SIGNAL
CURRENT_RUNTIME_NO_TRADE_PROPOSAL
CURRENT_RUNTIME_NO_ENTRY_STOP_TARGET
NO_BROKER_INTEGRATION
NO_AUTO_EXECUTION
NO_SELF_LEARNING_DEPLOYMENT
MANUAL_REVIEW_REQUIRED_ALWAYS
```

## قوانین غیرقابل‌تعبیر

```text
Memory is not a trade.
Setup is not a trade.
Trigger alone is not a trade.
Signal candidate is not execution.
Trade plan draft is manual-review only.
Risk draft is not an order.
Broker/execution remains forbidden unless a separate future architecture F is explicitly authorized.
```

## لایه‌های معماری E

1. Data Truth — freshness، provider health، closed-bar discipline.
2. Market State / Regime — trend/range/volatility/session/liquidity/event context.
3. Memory Engine — historical watch/context support؛ memory فقط ورودی تصمیم است.
4. Setup Engine — شکل‌گیری موقعیت اولیه، نه معامله.
5. Trigger Engine — تأیید رفتاری قیمت، نه معامله.
6. Blocker Engine — veto / no-trade مستقل.
7. Quality Vector — کیفیت چندبعدی، نه probability.
8. Signal Candidate — آبجکت بررسی دستی، نه execution.
9. Trade Plan Draft — entry/invalidation/target logic فقط بعد از gate آینده و فقط manual review.
10. Risk Model Draft — risk tier / risk cap برای بررسی دستی، نه order sizing اجرایی.
11. Forward Shadow Trade Plan — ارزیابی frozen plan بدون معامله واقعی.

## دلیل این پچ

پچ‌های قبلی forward evidence ساختند:

```text
LIVE_OBSERVATION_MAX_VALUE_01
SHADOW_CANDIDATE_UNIVERSE_01
SHADOW_CANDIDATE_OUTCOME_BASELINE_01
```

اما برای حرکت به سمت هدف E، قبل از ساخت setup/trigger/signal/trade-plan باید contractهای معماری قفل شوند تا سیستم تبدیل به rule-bot سطحی یا پیشنهاددهنده زودهنگام معامله نشود.

## ترتیب پیشنهادی بعد از ARCH1

```text
SIG-E-SETUP1     setup layer, no signal
SIG-E-TRIGGER1   trigger layer, no trade plan
SIG-E-BLOCKER1   blocker/no-trade veto layer
SIG-E-QV1        quality vector
SIG-E-SC1        signal candidate runtime, no entry/stop/target
SIG-E-TP1        trade plan draft, manual review only
SIG-E-RISK1      risk/position sizing draft, no execution
SIG-E-SHADOW1    forward shadow evaluation for trade plans
```

## نکته مهم برای پنل

این پچ نباید صفحه اصلی پنل را شلوغ کند. وضعیت SIG-E می‌تواند به‌صورت metadata/research/debug وجود داشته باشد، اما تا فعال شدن gateهای آینده نباید در صفحه اصلی به‌صورت پیشنهاد معامله یا signal دیده شود.

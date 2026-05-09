# راهنمای ورود معماری SIG Brain به GitHub

Created: 2026-05-09T05:10:53Z

## هدف

این pack برای وارد کردن معماری جدید مغز تاریخی به repo ساخته شده است:

```text
Brain Memory Registry
Brain4 runtime matcher + mobile panel
Brain5 upstream live context builder
Brain6 context field registry / feature catalog
```

## سه مورد فعلی مغز

```text
1) EURUSD_NY_UP_EXTENSION_UPPER_REJECTION_FADE_DOWN_v1_0
   status = HOLDOUT_WEAKENED_PARK_OR_REVIEW
   active = false
   score = 55

2) EURUSD_SESSION_UPSIDE_SWEEP_REJECTION_FADE_DOWN_CAVEATED_WATCH_v1_0
   status = ACTIVE_CAVEATED_WATCH_MEMORY_NOT_SIGNAL
   active = true
   score = 62

3) USDJPY_ALIGNMENT_ABSENT_CHOP_AVOID_SHORT_CONTEXT_CAVEATED_WATCH_v1_0
   status = ACTIVE_CAVEATED_NO_TRADE_WATCH_MEMORY_NOT_SIGNAL
   active = true
   score = 70
```

## نصب با PowerShell

بعد از unzip کردن pack:

```powershell
cd <مسیر unzip شده>\SIGBRAIN_GitHub_Integration_Pack_v1_0
.\install_scripts\install_sig_brain_architecture_to_product.ps1 -ProductPath "C:\Users\shahr\OneDrive\Documents\TradingOS\GitHub\TradingOS2\TradingOS2\personal_runtime_v1_release_candidate"
```

اگر product folder تو اسم دیگری دارد، همان فولدری را بده که داخلش پوشه‌های `scripts`, `inputs`, `runtime`, `panel` و `.github` قرار دارند.

## Validation بعد از نصب

```powershell
cd "C:\Users\shahr\OneDrive\Documents\TradingOS\GitHub\TradingOS2\TradingOS2\personal_runtime_v1_release_candidate"

py scripts\build_sig_brain5_live_context.py
py scripts\validate_sig_brain5_context_builder.py
py scripts\validate_sig_brain6_context_registry.py
py scripts\check_sig_brain6_runtime_context_coverage.py
```

یا:

```powershell
<مسیر pack>\install_scripts\verify_sig_brain_after_install.ps1 -ProductPath "C:\Users\shahr\OneDrive\Documents\TradingOS\GitHub\TradingOS2\TradingOS2\personal_runtime_v1_release_candidate"
```

## Commit در GitHub Desktop

```text
1. repo را در GitHub Desktop باز کن.
2. تغییرات را بررسی کن.
3. commit message:
   Integrate SIG brain runtime memory architecture
4. Push origin
```

## Commit با command line

```powershell
git status
git add data/sig_brain scripts inputs runtime panel contracts schemas docs proofs .github
git commit -m "Integrate SIG brain runtime memory architecture"
git push
```

## بعد از push

در GitHub Actions باید workflow زیر را ببینی:

```text
SIG Brain5 Context Builder + Brain4 Panel
```

## مرز مهم

این معماری هنوز signal engine نیست.

```text
not signal
no buy/sell/hold
no entry/stop/target
no profitability/tradability
no broker/execution
```

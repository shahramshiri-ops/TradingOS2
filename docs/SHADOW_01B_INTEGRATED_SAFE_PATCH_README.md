# SHADOW-01B Integrated Safe Patch v1.0

این پچ برای TradingOS2 طراحی شده و قبل از ساخت، context فعلی repo بررسی شده است.

## کار پچ

این پچ لایهٔ زیر را به سیستم فعلی اضافه می‌کند:

```text
Brain4 active memory matches
→ shadow-only signal candidate intake
→ shadow candidate ledger
→ shadow observation ledger
→ shadow summary
→ validation proof
```

## مرزهای سخت

```text
SHADOW_ONLY
NOT_SIGNAL
NO_BUY_SELL
NO_ENTRY_STOP_TARGET
NO_POSITION_SIZE
NO_BROKER_EXECUTION
NO_PROFITABILITY_CLAIM
NO_TRADABILITY_CLAIM
```

## فایل‌های اضافه‌شده

```text
scripts/build_sig_signal_candidate_shadow_intake.py
scripts/update_sig_shadow_candidate_ledger.py
scripts/update_sig_shadow_observations.py
scripts/summarize_sig_shadow_ledger.py
scripts/validate_sig_shadow_01b_integrated_outputs.py
scripts/run_sig_shadow_01b_integrated.py
scripts/apply_shadow_01b_integrated_workflow_patch.py

sig_brain/signal_candidate_shadow_intake_policy_v1_0.json
sig_brain/shadow_observation_policy_v1_0.json
sig_brain/shadow_ledger_schema_v1_0.json
```

## فایل‌های workflow که patch می‌شوند

```text
.github/workflows/sig_live_m5_refresh_resample_brain.yml
.github/workflows/sig_brain5_context_builder_brain4_panel.yml
.github/workflows/sig_brain4_display_only_mobile_panel.yml
```

پچ در همان workflowهای فعلی اجرا می‌شود؛ workflow جدا و دستی-only نیست.

## خروجی‌های runtime

```text
runtime/sig_signal_candidates/signal_candidate_payload_current.json
runtime/sig_signal_candidates/signal_candidate_summary_current.json
runtime/sig_shadow/shadow_candidate_ledger_current.json
runtime/sig_shadow/shadow_observation_ledger_current.json
runtime/sig_shadow/shadow_blocked_candidate_ledger_current.json
runtime/sig_shadow/shadow_summary_current.json
panel/brain4/sig_signal_candidate_payload_current.json
panel/brain4/sig_signal_candidate_summary_current.json
panel/brain4/sig_shadow_summary_current.json
proofs/sig_shadow_01b_integrated_validation_result.json
proofs/shadow_01b_workflow_patch_result.json
```

## نصب

PowerShell را در پوشهٔ extract‌شده باز کن:

```powershell
.\install_SHADOW_01B_INTEGRATED_SAFE_PATCH.ps1
```

اگر repo پیدا نشد:

```powershell
.\install_SHADOW_01B_INTEGRATED_SAFE_PATCH.ps1 -RepoRoot "$HOME\OneDrive\Documents\TradingOS\GitHub\TradingOS2\TradingOS2"
```

## بعد از نصب

از ریشه repo:

```powershell
python scripts\run_sig_shadow_01b_integrated.py
```

یا اگر venv داری:

```powershell
.\.venv\Scripts\python.exe scripts\run_sig_shadow_01b_integrated.py
```

## خروجی تست local

Installer خودش یک ZIP تست می‌سازد:

```text
outputs/SHADOW_01B_INTEGRATED_SAFE_LOCAL_TEST_OUTPUT.zip
```

آن را برای review بفرست.

## Commit / Push

با GitHub Desktop:

```text
Summary:
Add integrated SHADOW-01B forward-shadow ledger

Commit to main
Push origin
```

بعد از push، چون workflowهای فعلی patch شده‌اند، shadow pipeline همراه refresh/panel pipeline اجرا می‌شود.

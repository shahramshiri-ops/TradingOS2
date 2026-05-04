# PRV1H — راه‌اندازی GitHub Actions + پنل موبایل رایگان

## هدف

این sprint نسخهٔ Release Candidate فعلی PRV1 را به یک مسیر cloud رایگان/کم‌هزینه وصل می‌کند:

```text
GitHub Actions → RUN_DAILY.bat → تولید خروجی panel/status/proofs → GitHub Pages → نمایش روی موبایل
```

این مسیر همچنان فقط observation-only است: نه signal، نه buy/sell/hold، نه broker، نه order، نه execution، نه entry/stop/target، نه PnL، نه validation verdict.

## پیش‌نیازها

1. یک GitHub repository بساز. پیشنهاد امن‌تر: **Private repo**.
2. محتویات `personal_runtime_v1_release_candidate` را داخل repo قرار بده.
3. Secret زیر را در GitHub ذخیره کن:

```text
LFB_TWELVE_DATA_API_KEY
```

مسیر GitHub:

```text
Settings → Secrets and variables → Actions → New repository secret
```

API key را داخل فایل، README، commit، issue یا chat نگذار.

## فعال کردن GitHub Pages

در repository برو به:

```text
Settings → Pages
```

در قسمت Source، گزینهٔ GitHub Actions را انتخاب کن.

## اجرای دستی از موبایل

بعد از push کردن repo:

```text
Actions → PRV1 Daily Runtime Mobile Panel → Run workflow
```

بعد از اتمام workflow، آدرس GitHub Pages را باز کن. صفحهٔ موبایل در `index.html` ساخته می‌شود.

## آپدیت خودکار

Workflow به‌صورت پیش‌فرض هر ساعت یک بار اجرا می‌شود:

```yaml
cron: "7 * * * *"
```

برای V1 همین بهتر است، چون provider rate limit داریم و refresh تهاجمی لازم نیست.

## دکمه Refresh داخل خود پنل

در نسخهٔ GitHub Pages، پنل static است. دکمه داخل صفحه فقط می‌تواند تو را به GitHub Actions ببرد تا workflow را manual اجرا کنی. دکمهٔ واقعی داخل پنل که خودش backend را اجرا کند، نیاز به Cloud Run یا backend مشابه دارد و در PRV1H-01 عمداً ساخته نشده است.

## مسیر روزانهٔ canonical

در GitHub Actions فقط همین مسیر اجرا می‌شود:

```text
RUN_DAILY.bat
```

و بعد:

```text
scripts/generate_mobile_pages_site.py
```

## فایل‌های مهم

```text
.github/workflows/prv1_daily_runtime_mobile_panel.yml
scripts/generate_mobile_pages_site.py
config/github_actions_mobile_panel_policy.json
proofs/prv1h_pre_execution_boundary_proof.json
```

## بعد از اولین اجرای GitHub Actions چه proofهایی بفرستی؟

اگر خواستی من review کنم، artifactهای زیر را از workflow یا repo بفرست:

```text
site/panel_payload_public.json
site/status_public.json
proofs/daily_runtime_local_validation_result.json
proofs/daily_runtime_boundary_proof.json
proofs/daily_runtime_no_action_surface_proof.json
proofs/daily_runtime_secret_redaction_proof.json
logs/last_run_status_after_daily_runtime.json
logs/runtime_heartbeat_after_daily_runtime.json
```

`.env` یا API key نفرست.

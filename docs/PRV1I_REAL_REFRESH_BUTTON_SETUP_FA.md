# PRV1I-01 — دکمه Refresh واقعی داخل پنل موبایل

## معماری

GitHub Pages فقط سایت static است؛ بنابراین دکمهٔ واقعی به یک backend کوچک نیاز دارد. این patch از Cloudflare Worker به‌عنوان refresh proxy استفاده می‌کند:

```text
Mobile Panel on GitHub Pages
→ Refresh Now button
→ Cloudflare Worker /refresh
→ GitHub Actions workflow_dispatch
→ RUN_DAILY
→ GitHub Pages redeploy
```

Worker هیچ runtime معاملاتی اجرا نمی‌کند؛ فقط workflow را trigger می‌کند.

## نصب سریع

1. محتویات patch را در root repo بگذار و push کن.
2. یک Cloudflare Worker بساز و کد `cloudflare-worker/worker.js` را داخلش بگذار.
3. در Worker این variables را بگذار:

```text
GITHUB_OWNER = shahramshiri-ops
GITHUB_REPO = TradingOS2
GITHUB_WORKFLOW_ID = prv1_daily_runtime_mobile_panel.yml
GITHUB_REF = main
ALLOWED_ORIGIN = https://shahramshiri-ops.github.io
GITHUB_API_VERSION = 2022-11-28
```

4. در Worker این secrets را بگذار:

```text
GITHUB_ACTIONS_DISPATCH_TOKEN = [GitHub fine-grained token]
REFRESH_PIN = [PIN شخصی]
```

5. در GitHub repo یک Actions Variable بساز:

```text
MOBILE_REFRESH_WORKER_URL = https://YOUR_WORKER_URL
```

6. Workflow را دستی اجرا کن. بعد پنل را باز کن؛ دکمهٔ Refresh Now باید فعال باشد.

## GitHub token پیشنهادی

Fine-grained token با دسترسی فقط به repo `TradingOS2` و permission زیر:

```text
Repository permissions → Actions: Read and write
```

## خط قرمزها

هیچ‌کدام از این‌ها را داخل repo نگذار:

```text
GITHUB_ACTIONS_DISPATCH_TOKEN
REFRESH_PIN
LFB_TWELVE_DATA_API_KEY
.env
```

## مرزها

این patch broker، execution، signal، buy/sell/hold، entry/stop/target، PnL، validation verdict یا production readiness نمی‌سازد.

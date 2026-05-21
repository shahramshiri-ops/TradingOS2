# REPO-HYGIENE-01 — Generated Runtime File Conflict Control

این ابزار برای همین مشکل ساخته شده:  
فایل‌های live/generated/current مدام تغییر می‌کنند و باعث conflict می‌شوند.

## کار درست

فقط source files را commit کن:

- `scripts/*.py`
- `panel/brain4/assets/*.js`
- `panel/brain4/assets/*.css`
- `panel/brain4/index.html`
- `sig_brain/*policy*.json`
- `docs/*.md`
- `.github/workflows/*.yml`

فایل‌های generated را دستی commit نکن:

- `outputs/**`
- `data/live_m5/**`
- `runtime/sig_shadow/*current.json`
- `runtime/sig_shadow/live_logs/**`
- `runtime/sig_shadow/price_bridge_h1/**`
- `panel/brain4/*current.json`
- `proofs/*.json`
- `*.zip`

## اجرای سریع

```powershell
.\install_REPO_HYGIENE_01_PATCH.ps1
```

اگر هنوز merge conflict باز است:

```powershell
.\install_REPO_HYGIENE_01_PATCH.ps1 -AbortMerge
```

بعد از اجرا، GitHub Desktop باید تعداد تغییرات را خیلی کمتر نشان دهد و بیشترشان source باشند.

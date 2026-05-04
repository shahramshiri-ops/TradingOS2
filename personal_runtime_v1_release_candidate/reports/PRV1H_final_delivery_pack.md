# PRV1H — GitHub Actions + Mobile Static Panel Delivery Pack

Created at UTC: 2026-05-04T13:44:27Z

## Final verdict

Accepted with Caveats / GitHub Actions Mobile Static Panel Package Built; GitHub Execution Proof Requires User Repository

## Built

- GitHub Actions workflow for scheduled/manual PRV1 daily runtime execution.
- GitHub Pages static mobile panel generator.
- GitHub Secret policy for `LFB_TWELVE_DATA_API_KEY`.
- Setup guides in Persian and English.
- Security notes and `.gitignore` guardrails.
- Pre-execution boundary proof.

## Not claimed

- GitHub workflow has not been run from this chat.
- GitHub Pages has not been deployed from this chat.
- API key has not been requested or read here.
- No provider call was performed here.
- True in-panel backend refresh button is not built in this static-free GitHub Pages model.

## Canonical mobile path

```text
GitHub Actions → RUN_DAILY.bat → scripts/generate_mobile_pages_site.py → GitHub Pages
```

## User action required

1. Create GitHub repo.
2. Put this package at repo root.
3. Add GitHub Action secret `LFB_TWELVE_DATA_API_KEY`.
4. Enable Pages source: GitHub Actions.
5. Run workflow manually once.
6. Open generated Pages URL from mobile.

## Boundary

No broker, no order, no execution, no signal, no buy/sell/hold, no entry/stop/target, no PnL/win-loss, no optimizer, no validation verdict, no production-readiness claim.

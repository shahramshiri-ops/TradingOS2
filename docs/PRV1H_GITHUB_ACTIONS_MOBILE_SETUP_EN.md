# PRV1H — GitHub Actions + Mobile Static Panel Setup

## Goal

PRV1H connects the current PRV1 Release Candidate to a free/low-cost cloud path:

```text
GitHub Actions → RUN_DAILY.bat → panel/status/proof outputs → GitHub Pages → mobile view
```

It remains display-only and observation-only: no signal, no buy/sell/hold, no broker, no order, no execution, no entry/stop/target, no PnL, and no validation verdict.

## Setup

1. Create a GitHub repository. Safer default: **Private repository**.
2. Put the release candidate files at the repository root.
3. Add this repository secret:

```text
LFB_TWELVE_DATA_API_KEY
```

GitHub path:

```text
Settings → Secrets and variables → Actions → New repository secret
```

Never commit the API key or `.env` file.

## Enable GitHub Pages

Go to:

```text
Settings → Pages
```

Set Source to GitHub Actions.

## Manual refresh from mobile

Use:

```text
Actions → PRV1 Daily Runtime Mobile Panel → Run workflow
```

The generated mobile panel is deployed to GitHub Pages.

## Auto refresh

The workflow runs hourly by default:

```yaml
cron: "7 * * * *"
```

## In-panel refresh button caveat

GitHub Pages is static. The panel can link to GitHub Actions, but a real in-panel backend refresh button requires a backend service such as Cloud Run. That is intentionally out of PRV1H-01 scope.

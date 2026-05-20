# SHADOW-READY-01 Repo Patch v1.0

Purpose: harden the live shadow observation layer before leaving the system in the market for weeks/months.

Adds:
- near-miss logging
- pre-candidate blocker/gating diagnostics
- shadow health summary
- versioned cohort tracking
- observation completion status
- daily/weekly summaries
- panel-safe shadow status JSON
- manual PMO review queue

Boundaries:
- NOT a signal
- NO buy/sell
- NO entry/stop/target
- NO position sizing
- NO broker/execution
- NO automatic learning or rule rewrite

Install from the extracted patch folder:

```powershell
.\install_SHADOW_READY_01_REPO_PATCH.ps1
```

If needed:

```powershell
.\install_SHADOW_READY_01_REPO_PATCH.ps1 -RepoRoot "$HOME\OneDrive\Documents\TradingOS\GitHub\TradingOS2\TradingOS2"
```

After installation, send:

`outputs\SHADOW_READY_01_LOCAL_TEST_OUTPUT.zip`

Do not commit until that local output is reviewed.

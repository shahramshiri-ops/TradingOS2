# SIG-E-SHADOW-LIVE-OHLC-GZIP-HOTFIX

Adds `.csv.gz` support to SIG-E shadow detector live OHLC readers.

The previous output showed live resampled files existed but loaded as zero rows because compressed files were read as plain CSV.

Boundary: reader hotfix only; no signal, no trade proposal, no entry/stop/target, no risk sizing, no broker/execution.

Optional AutoGit:
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File APPLY_TRADINGOS_SIG_E_SHADOW_LIVE_OHLC_GZIP_HOTFIX.ps1 -RepoRoot $RepoRoot -AutoGit`

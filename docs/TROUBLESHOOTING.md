# Troubleshooting — Personal Runtime V1

Generated: `2026-05-04T10:51:03Z`

## 1. `python` is not recognized

Install Python 3.10+ or use the Python launcher if available:

```bat
py scriptsun_refresh.py --package-root . --print-summary
```

## 2. `run_refresh.bat` opens and closes quickly

Run it from PowerShell or Command Prompt instead of double-clicking:

```bat
cd personal_runtime_v1
scriptsun_refresh.bat
```

## 3. Panel does not update

Run:

```bash
python scripts/generate_panel_payload.py --package-root .
```

Then reopen:

```text
panel/index.html
```

## 4. Status says dry-run

This is expected for the packaged V1 proof. It means the script refreshed display files from existing package state and did not perform live fetch.

## 5. API key / `.env` confusion

Do not put secrets in chat or attach a real `.env` file. If a future local live fetch is enabled, credentials must stay in local environment variables only. Output files must remain redacted.

## 6. Missing SPX/NQ

Expected. `SPX` and `NQ` are out of V1 active scope.

## 7. No official event risk shown

Expected. Calendar/event source is not in V1 scope.

## 8. XAUUSD M5 caveat appears

Expected. The package does not fabricate `XAUUSD M5` into the RSP cache feed plan if it was absent.

## 9. Candidate rows are not visible

Expected in this V1 package if the current detailed 4-row store is not present. The package shows summary counts and must not reconstruct row details from older mismatched artifacts.

## 10. The panel appears to imply action

Treat that as a defect. The V1 panel must never show buy/sell/hold, entry/stop/target, size, allocation, broker status, order queue, or execution buttons.

## 11. What to send for debugging

Safe files to share:

- `logs/last_run_status.json`
- `logs/runtime_heartbeat.json`
- `reports/cache_status.json`
- `panel/panel_payload_v1.json`
- `proofs/refresh_dry_run_proof.json`

Do not share:

- real `.env`
- API keys
- terminal screenshots showing secrets

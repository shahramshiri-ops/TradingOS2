# PRV1O — Active Watch Display Readability Fix

## Verdict
Accepted with Caveats / Active Watch Display Fix Patch Built

## What this patch fixes
- Raw seeded-candidate reason text is translated into Persian.
- Active Watch reference levels use `trigger_bar_from_cache` for PRV1E-detected rows.
- High / Low / Close should no longer show as `—` for new active candidates when cache trigger bars exist.

## Not changed
- Candidate detection logic
- Lifecycle classification logic
- Broker/execution/signal/PnL/validation boundaries

## Files
- `scripts/generate_mobile_pages_site_professional_dashboard.py`
- `scripts/generate_mobile_pages_site_with_real_refresh_button.py`
- `scripts/generate_mobile_pages_site_human_readable.py`
- `scripts/generate_mobile_pages_site_enhanced_market_state.py`
- `config/active_watch_display_fix_policy.json`
- `docs/PRV1O_ACTIVE_WATCH_DISPLAY_FIX_FA.md`
- `proofs/PRV1O_package_build_proof.json`

# LIVE-SHADOW-FOUNDATION-01

## Purpose

This patch makes multi-month live observation useful by adding append-only logs.

It records:

- Context snapshots
- Memory/watch lifecycle
- Setup-shadow skeleton
- Trigger-shadow skeleton
- Blocker diagnostics
- Candidate snapshots
- Diagnostic records

## What it does not do

- No signal
- No buy/sell
- No entry/stop/target
- No position sizing
- No broker/execution
- No auto-learning
- No rule rewrite
- No outcome tracking yet

Outcome tracking remains a separate future patch.

## Outputs

- `runtime/sig_shadow/live_logs/YYYY-MM-DD/context_snapshot_log_YYYY-MM-DD.jsonl`
- `runtime/sig_shadow/live_logs/YYYY-MM-DD/memory_watch_log_YYYY-MM-DD.jsonl`
- `runtime/sig_shadow/live_logs/YYYY-MM-DD/setup_shadow_log_YYYY-MM-DD.jsonl`
- `runtime/sig_shadow/live_logs/YYYY-MM-DD/trigger_shadow_log_YYYY-MM-DD.jsonl`
- `runtime/sig_shadow/live_logs/YYYY-MM-DD/blocker_shadow_log_YYYY-MM-DD.jsonl`
- `runtime/sig_shadow/live_logs/YYYY-MM-DD/candidate_shadow_log_YYYY-MM-DD.jsonl`
- `runtime/sig_shadow/live_logs/YYYY-MM-DD/diagnostic_record_log_YYYY-MM-DD.jsonl`
- `runtime/sig_shadow/live_shadow_foundation_status_current.json`
- `panel/brain4/live_shadow_foundation_status_current.json`

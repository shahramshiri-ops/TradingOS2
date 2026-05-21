# ACTIONS-COMMIT-SCOPE-FIX-02

## مشکل

GitHub Actions در مرحله commit/push این فایل را وارد commit کرد:

```text
runtime/sig_shadow/live_logs/2026-05-21/outcome_observation_log_2026-05-21.jsonl
```

و چون اندازه آن بیش از 100MB بود، GitHub push را رد کرد.

## اصلاح

این patch مرحله broad commit را با safe commit جایگزین می‌کند:

```text
python scripts/actions_commit_generated_readonly_safe.py
```

safe commit فقط فایل‌های کوچک و لازم برای panel/read-only status را stage می‌کند و هرگز این‌ها را stage نمی‌کند:

- `runtime/sig_shadow/live_logs/**`
- `runtime/sig_shadow/price_bridge_h1/**`
- `outputs/**`
- `proofs/**`
- `data/live_m5/incremental/*.csv`
- `*.zip`
- `*.jsonl`

## Boundary

- NOT_SIGNAL
- NO_BUY_SELL
- NO_ENTRY_STOP_TARGET
- NO_BROKER_EXECUTION
- NO_AUTO_LEARNING
- NO_RULE_REWRITE

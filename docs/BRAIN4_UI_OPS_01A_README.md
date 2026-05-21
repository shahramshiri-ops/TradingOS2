# BRAIN4-UI-OPS-01A — UI Hotfix

01 install validated, but code review found a real JS issue:

`classList.add()` was receiving an array-like value instead of separate class tokens.

This patch fixes that with `addClasses()` and preserves the same visual polish layer.

Boundary:

- UI_ONLY_PATCH
- NOT_SIGNAL
- NO_BUY_SELL
- NO_ENTRY_STOP_TARGET
- NO_BROKER_EXECUTION
- NO_AUTO_LEARNING
- NO_RULE_REWRITE

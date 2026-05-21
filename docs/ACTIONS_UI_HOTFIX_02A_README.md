# ACTIONS-UI-HOTFIX-02A

## What this fixes

### 1) GitHub Actions failure

The previous safe commit script removed `outputs/**` and then tried to write:

```text
outputs/_actions_commit_scope_fix_02/actions_commit_scope_fix_02_result.json
```

That caused:

```text
FileNotFoundError: No such file or directory
```

02A recreates the report directory before writing and no longer removes the report directory.

### 2) Broken panel appearance

`BRAIN4-UI-OPS-01` was too aggressive. It added duplicated `Live View` labels and distorted the live event card.

02A replaces that JS with a safe stabilizer that removes old UI mutations and only applies conservative micro-polish.

## Boundary

- UI-only visual stabilizer
- safe commit scope only
- NOT_SIGNAL
- NO_BUY_SELL
- NO_ENTRY_STOP_TARGET
- NO_BROKER_EXECUTION
- NO_AUTO_LEARNING
- NO_RULE_REWRITE

# SIG-E-SHADOW-PERSIST1-HOTFIX1 — Offline-Safe Restore

## Problem

The first persistence patch tried to fetch prior state from GitHub Pages during local application. On Windows/proxy/DNS setups, `urllib` can hang or fail inside proxy resolution. The local apply was interrupted.

## Fix

- Local apply disables remote restore by setting `SIG_E_PERSIST_DISABLE_REMOTE_RESTORE=1`.
- The restore script now skips network restore outside GitHub Actions unless explicitly allowed.
- In GitHub Actions, remote restore remains allowed.
- Network errors are caught safely and do not fail the workflow.

## Local behavior

Local run:

`REMOTE_RESTORE_ALLOWED=False`

This is expected and correct.

## GitHub Actions behavior

GitHub Actions run:

`REMOTE_RESTORE_ALLOWED=True`

unless explicitly disabled.

## Boundaries

Persistence only. No signal, trade proposal, entry/stop/target, risk sizing, broker/execution, auto execution, memory promotion, or rule rewrite.

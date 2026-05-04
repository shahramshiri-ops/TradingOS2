# V1 Scope and Limits

Generated: `2026-05-04T10:51:03Z`

## V1 active scope

Active instruments:

- `XAUUSD`
- `EURUSD`
- `USDJPY`

Runtime surfaces included only as packaged display/state context:

- runtime state summary
- candidate/lifecycle summary
- outcome observation summary
- panel payload
- static HTML panel
- cache status
- heartbeat and last-run status
- dry-run refresh script
- usage guides

## Explicitly out of V1 active scope

- `SPX`
- `NQ`
- second provider
- second-provider conflict check
- provider divergence
- failover
- official calendar/event source
- CPI/FOMC/NFP/central-bank classification
- event blocking logic
- broker connector
- order management
- execution
- demo/live trading
- buy/sell/hold output
- entry/stop/target output
- position sizing or allocation
- PnL / win-loss
- optimizer
- validation verdict
- adaptation decision
- production-readiness claim

## Boundary invariants

1. runtime observation ≠ signal
2. candidate ≠ trade recommendation
3. outcome observation ≠ win/loss
4. lifecycle tracking ≠ execution tracking
5. cache ≠ source authority
6. single-provider confidence ≠ source truth
7. scheduler heartbeat ≠ production readiness
8. panel payload ≠ action surface
9. no broker
10. no order
11. no execution
12. no buy/sell/hold
13. no entry/stop/target
14. no PnL
15. no optimizer
16. no validation verdict
17. no adaptation decision
18. no production readiness claim
19. SPX/NQ are out of V1 scope
20. calendar/event is out of V1 scope
21. source-second-provider is out of V1 scope
22. Row 2 retained unopened
23. Rows 6–7 deferred re-entry
24. matrix-complete ≠ matrix-open

## V1 caveat reading

A visible caveat is not closure of that caveat. It only tells the operator what limitation remains.

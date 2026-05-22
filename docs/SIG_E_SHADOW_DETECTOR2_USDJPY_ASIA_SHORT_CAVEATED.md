# SIG-E Shadow Detector2 — USDJPY Asia Short H1+M15 Caveated

This patch adds the second live shadow observation lane:

`USDJPY / Asia / Short / aligned down pullback reject / H1 strong rejection close / M15 no early failure after H1 confirm`

Classification: `CAVEATED_OBSERVATION_ONLY`.

Why caveated:
- M15 validation N was only 17.
- This is not a primary lane.
- It is not a signal and cannot become a trade proposal without later evidence.

Boundaries:
- No signal
- No trade proposal
- No entry / stop / target
- No risk sizing
- No broker/execution
- No auto execution
- No memory promotion

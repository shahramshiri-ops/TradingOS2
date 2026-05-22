# SIG-E-SHADOW-LANE1-OVERLAP-PREFLIGHT1

Purpose:
Evaluate whether Lane1 should get a separate London-NY overlap shadow variant without changing Lane1.

Question:
If `USDJPY London Long H1+M15` accepted `LONDON_NY_OVERLAP` as a session, how many records that were rejected only by session would appear regime-eligible under Lane1-style long conditions?

This is not a detector change. It is a what-if preflight.

Outputs:
- `runtime/sig_e/shadow_lane1_overlap_preflight_current.json`
- `panel/brain4/sig_e_shadow_lane1_overlap_preflight_current.json`
- `outputs/_sig_e_shadow_lane1_overlap_preflight1/sig_e_shadow_lane1_overlap_preflight_current.json`
- `outputs/_sig_e_shadow_lane1_overlap_preflight1/sig_e_shadow_lane1_overlap_preflight_current.md`

Important limitation:
This preflight cannot evaluate H1 setup, H1 trigger, or M15 confirmation on records that Lane1 rejected at session gate. It only estimates whether the session-rejected overlap records would have passed session+regime eligibility.

Boundary:
No detector rule change, no portfolio lane change, no signal, no trade proposal, no entry/stop/target, no risk sizing, no broker/execution.

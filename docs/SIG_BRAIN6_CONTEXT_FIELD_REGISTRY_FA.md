# SIG-BRAIN6 — Context Field Registry / Feature Catalog

Created: 2026-05-08T14:46:35Z

## What this patch does

SIG-BRAIN6 formalizes the field layer for the historical brain.

It adds:

```text
data/sig_brain/context_field_registry_v1_0.json
data/sig_brain/feature_family_catalog_v1_0.json
data/sig_brain/context_builder_support_registry_v1_0.json
data/sig_brain/memory_context_requirements_matrix_v1_0.csv
scripts/validate_sig_brain6_context_registry.py
scripts/check_sig_brain6_runtime_context_coverage.py
```

## Why this matters

Each historical memory can require different live context fields.  
The right architecture is not to hardcode those fields into the mobile panel.

The right architecture is:

```text
Memory object declares required_context_fields
        ↓
Context Field Registry defines those fields
        ↓
Context Builder declares support coverage
        ↓
Runtime matcher evaluates memory or returns MEMORY_INPUT_INSUFFICIENT
```

## Current active field families

```text
core_time_session
direction_alignment
range_chop_volatility
sweep_liquidity
data_quality_freshness
```

Future / not yet active families:

```text
d1_context_levels
opening_drive
event_calendar_context
cost_friction_context
```

## Run

```powershell
py scripts\validate_sig_brain6_context_registry.py
py scripts\check_sig_brain6_runtime_context_coverage.py
```

The second command needs a current:

```text
inputs\sig_brain4_live_context_latest.json
```

from SIG-BRAIN5.

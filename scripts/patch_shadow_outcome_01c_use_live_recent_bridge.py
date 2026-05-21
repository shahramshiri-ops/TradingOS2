#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path

TARGET = Path("scripts/build_sig_shadow_outcome_01_outputs.py")
if not TARGET.exists():
    raise SystemExit("Missing scripts/build_sig_shadow_outcome_01_outputs.py")

text = TARGET.read_text(encoding="utf-8")
TARGET.with_suffix(TARGET.suffix + ".bak_shadow_outcome_01c_live_recent_bridge").write_text(text, encoding="utf-8")

if "SHADOW_OUTCOME_01C_LIVE_RECENT_PRICE_BRIDGE_GUARD" not in text:
    text = text.replace(
        'AUTHORITY = (\n    "SHADOW_OUTCOME_01|',
        'AUTHORITY = (\n    "SHADOW_OUTCOME_01|SHADOW_OUTCOME_01C_LIVE_RECENT_PRICE_BRIDGE_GUARD|',
        1
    )

needle = '    roots = [\n        ROOT / "data" / "canonical",'
replacement = '    roots = [\n        ROOT / "runtime" / "sig_shadow" / "price_bridge_h1",\n        ROOT / "data" / "canonical",'
if needle in text and 'ROOT / "runtime" / "sig_shadow" / "price_bridge_h1"' not in text:
    text = text.replace(needle, replacement, 1)

if '"price_source_bridge_version"' not in text:
    marker = '        "payload_version": "SHADOW_OUTCOME_01_STATUS_v1_0",'
    text = text.replace(marker, marker + '\n        "price_source_bridge_version": "SHADOW_OUTCOME_01C_LIVE_RECENT_PRICE_BRIDGE_GUARD_v1_0",', 1)

compile(text, str(TARGET), "exec")
TARGET.write_text(text, encoding="utf-8")
print("SHADOW_OUTCOME_01C_OUTCOME_SCRIPT_PATCHED")

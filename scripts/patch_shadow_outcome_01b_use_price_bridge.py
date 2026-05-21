#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path

TARGET = Path("scripts/build_sig_shadow_outcome_01_outputs.py")
if not TARGET.exists():
    raise SystemExit("Missing scripts/build_sig_shadow_outcome_01_outputs.py")

text = TARGET.read_text(encoding="utf-8")
backup = TARGET.with_suffix(TARGET.suffix + ".bak_shadow_outcome_01b_price_source_bridge")
backup.write_text(text, encoding="utf-8")

if "SHADOW_OUTCOME_01B_H1_PRICE_SOURCE_BRIDGE" not in text:
    text = text.replace(
        'AUTHORITY = (\n    "SHADOW_OUTCOME_01|',
        'AUTHORITY = (\n    "SHADOW_OUTCOME_01|SHADOW_OUTCOME_01B_H1_PRICE_SOURCE_BRIDGE|',
        1
    )

needle = "    roots = [\n        ROOT / \"data\" / \"canonical\","
replacement = "    roots = [\n        ROOT / \"runtime\" / \"sig_shadow\" / \"price_bridge_h1\",\n        ROOT / \"data\" / \"canonical\","
if needle in text and 'ROOT / "runtime" / "sig_shadow" / "price_bridge_h1"' not in text:
    text = text.replace(needle, replacement, 1)

if '"price_source_bridge_version"' not in text:
    status_needle = '        "price_anchor_patch_version": "SHADOW_OUTCOME_01A_PRICE_ANCHOR_v1_0",'
    if status_needle in text:
        text = text.replace(status_needle, status_needle + '\n        "price_source_bridge_version": "SHADOW_OUTCOME_01B_H1_PRICE_SOURCE_BRIDGE_v1_0",', 1)
    else:
        text = text.replace('        "payload_version": "SHADOW_OUTCOME_01_STATUS_v1_0",', '        "payload_version": "SHADOW_OUTCOME_01_STATUS_v1_0",\n        "price_source_bridge_version": "SHADOW_OUTCOME_01B_H1_PRICE_SOURCE_BRIDGE_v1_0",', 1)

compile(text, str(TARGET), "exec")
TARGET.write_text(text, encoding="utf-8")
print("SHADOW_OUTCOME_01B_OUTCOME_SCRIPT_PATCHED")

#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path

TARGET = Path("scripts/build_sig_shadow_outcome_01_outputs.py")
if not TARGET.exists():
    raise SystemExit("Missing scripts/build_sig_shadow_outcome_01_outputs.py")

text = TARGET.read_text(encoding="utf-8")
backup = TARGET.with_suffix(TARGET.suffix + ".bak_shadow_outcome_01a_price_anchor")
backup.write_text(text, encoding="utf-8")

if "SHADOW_OUTCOME_01A_PRICE_ANCHOR_PATCH" not in text:
    text = text.replace(
        'AUTHORITY = (\n    "SHADOW_OUTCOME_01|OBSERVATION_ONLY|H1_PATH_AFTER_SHADOW_OBJECTS|"',
        'AUTHORITY = (\n    "SHADOW_OUTCOME_01|SHADOW_OUTCOME_01A_PRICE_ANCHOR_PATCH|OBSERVATION_ONLY|H1_PATH_AFTER_SHADOW_OBJECTS|"',
        1
    )

if "def infer_instrument_from_memory(" not in text:
    marker = "def normalize_timeframe(value: Any) -> str:"
    helper = (
        "def infer_instrument_from_memory(memory_id: Any) -> Optional[str]:\n"
        "    s = str(memory_id or \"\").upper()\n"
        "    for inst in [\"EURUSD\", \"USDJPY\", \"XAUUSD\"]:\n"
        "        if s.startswith(inst) or (\"_\" + inst + \"_\") in s or inst in s:\n"
        "            return inst\n"
        "    return None\n\n\n"
    )
    if marker not in text:
        raise SystemExit("Could not find normalize_timeframe marker")
    text = text.replace(marker, helper + marker, 1)

old_inst = 'inst = normalize_instrument(row.get("instrument"))'
new_inst = 'inst = normalize_instrument(row.get("instrument")) or infer_instrument_from_memory(row.get("memory_id") or row.get("source_memory_id"))'
if old_inst in text:
    text = text.replace(old_inst, new_inst, 1)

old_block = (
    "    # Runtime created_utc is useful for logging but not a reliable price-bar anchor.\n"
    "    if subject.get(\"anchor_basis\") == \"created_utc_runtime_not_price_anchor\":\n"
    "        base[\"observation_status\"] = \"NOT_OBSERVABLE_RUNTIME_TIMESTAMP_ONLY\"\n"
    "        base[\"price_data_status\"] = \"NO_PRICE_BAR_ANCHOR\"\n"
    "        return base\n\n"
    "    bars, data_path = load_bars(inst, \"H1\")"
)
new_block = (
    "    # Runtime created_utc is not an event price anchor, but for live shadow records\n"
    "    # without a source_bar_open_ts_utc we can conservatively resolve to the latest\n"
    "    # closed H1 bar at or before runtime. This is explicitly labeled and remains\n"
    "    # observation-only, not PnL/trade evidence.\n"
    "    runtime_timestamp_only = subject.get(\"anchor_basis\") == \"created_utc_runtime_not_price_anchor\"\n\n"
    "    bars, data_path = load_bars(inst, \"H1\")"
)
if old_block in text:
    text = text.replace(old_block, new_block, 1)
elif "runtime_timestamp_only =" not in text:
    raise SystemExit("Could not patch runtime timestamp hard-stop block")

old_anchor = (
    "    anchor_bar = bars[anchor_idx]\n"
    "    base[\"anchor_h1_bar_open_ts_utc\"] = iso(anchor_bar[\"ts\"])\n"
    "    base[\"anchor_close\"] = anchor_bar[\"close\"]\n"
    "    base[\"latest_h1_bar_open_ts_utc\"] = iso(bars[-1][\"ts\"])\n"
    "    base[\"price_data_status\"] = \"H1_DATA_FOUND\""
)
new_anchor = (
    "    anchor_bar = bars[anchor_idx]\n"
    "    base[\"anchor_h1_bar_open_ts_utc\"] = iso(anchor_bar[\"ts\"])\n"
    "    base[\"anchor_close\"] = anchor_bar[\"close\"]\n"
    "    base[\"latest_h1_bar_open_ts_utc\"] = iso(bars[-1][\"ts\"])\n"
    "    if runtime_timestamp_only:\n"
    "        base[\"anchor_resolution_status\"] = \"CONTEXT_DERIVED_LATEST_CLOSED_H1_BAR\"\n"
    "        base[\"anchor_basis_resolved\"] = \"LATEST_CLOSED_H1_BAR_AT_OR_BEFORE_RUNTIME_CREATED_UTC\"\n"
    "        base[\"price_data_status\"] = \"H1_DATA_FOUND_CONTEXT_DERIVED_ANCHOR\"\n"
    "    else:\n"
    "        base[\"anchor_resolution_status\"] = \"SOURCE_PRICE_BAR_ANCHOR\"\n"
    "        base[\"anchor_basis_resolved\"] = subject.get(\"anchor_basis\")\n"
    "        base[\"price_data_status\"] = \"H1_DATA_FOUND\""
)
if old_anchor in text:
    text = text.replace(old_anchor, new_anchor, 1)
elif "anchor_resolution_status" not in text:
    raise SystemExit("Could not patch anchor resolution labels")

if "price_anchor_patch_version" not in text:
    text = text.replace(
        '        "payload_version": "SHADOW_OUTCOME_01_STATUS_v1_0",',
        '        "payload_version": "SHADOW_OUTCOME_01_STATUS_v1_0",\n        "price_anchor_patch_version": "SHADOW_OUTCOME_01A_PRICE_ANCHOR_v1_0",',
        1
    )
    text = text.replace(
        '        "payload_version": "SHADOW_OUTCOME_01_LEDGER_v1_0",',
        '        "payload_version": "SHADOW_OUTCOME_01_LEDGER_v1_0",\n        "price_anchor_patch_version": "SHADOW_OUTCOME_01A_PRICE_ANCHOR_v1_0",',
        1
    )

compile(text, str(TARGET), "exec")
TARGET.write_text(text, encoding="utf-8")
print("SHADOW_OUTCOME_01A_PRICE_ANCHOR_CODE_PATCHED")

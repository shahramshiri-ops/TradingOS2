from pathlib import Path

builder = Path("scripts/build_sig_shadow_count_normalize_01_outputs.py")
panel_js = Path("panel/brain4/assets/shadow_unified_panel.js")

if not builder.exists():
    raise SystemExit("Missing scripts/build_sig_shadow_count_normalize_01_outputs.py")
if not panel_js.exists():
    raise SystemExit("Missing panel/brain4/assets/shadow_unified_panel.js")

btxt = builder.read_text(encoding="utf-8")
Path(str(builder) + ".bak_count_normalize_null_fallback").write_text(btxt, encoding="utf-8")

if "def first_non_null(" not in btxt:
    marker = "def as_list(payload: Any, keys: List[str]) -> List[Dict[str, Any]]:"
    helper = 'def first_non_null(*values: Any) -> Any:\n    for value in values:\n        if value is not None:\n            return value\n    return None\n\n\n'
    if marker not in btxt:
        raise SystemExit("Could not find insertion marker for first_non_null")
    btxt = btxt.replace(marker, helper + marker, 1)

btxt = btxt.replace(
    '"raw_near_miss_count_from_ops": ops.get("near_miss_count_last_run"),',
    '"raw_near_miss_count_from_ops": first_non_null(ops.get("near_miss_count_last_run"), shadow.get("near_miss_count_last_run")),'
)
btxt = btxt.replace(
    '"raw_near_miss_high_count_from_ops": ops.get("near_miss_high_count_last_run"),',
    '"raw_near_miss_high_count_from_ops": first_non_null(ops.get("near_miss_high_count_last_run"), shadow.get("near_miss_high_count_last_run")),'
)

compile(btxt, str(builder), "exec")
builder.write_text(btxt, encoding="utf-8")

jtxt = panel_js.read_text(encoding="utf-8")
Path(str(panel_js) + ".bak_count_normalize_null_fallback").write_text(jtxt, encoding="utf-8")

old = '''  function n(v, fallback = 0) {
    const x = Number(v);
    return Number.isFinite(x) ? x : fallback;
  }'''
new = '''  function n(v, fallback = 0) {
    if (v === undefined || v === null || v === "") return fallback;
    const x = Number(v);
    return Number.isFinite(x) ? x : fallback;
  }'''

if old not in jtxt:
    if 'if (v === undefined || v === null || v === "") return fallback;' not in jtxt:
        raise SystemExit("Could not patch n() in shadow_unified_panel.js")
else:
    jtxt = jtxt.replace(old, new, 1)

panel_js.write_text(jtxt, encoding="utf-8")
print("COUNT_NORMALIZE_NULL_FALLBACK_PATCH_OK")

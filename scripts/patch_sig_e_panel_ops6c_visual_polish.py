
import json
import re
import shutil
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-PANEL-OPS6C-VISUAL-POLISH"

INDEX = Path("panel/brain4/index.html")
CSS = Path("panel/brain4/assets/sig_e_panel_ops6b.css")
JS = Path("panel/brain4/assets/sig_e_panel_ops6b.js")
OUT = Path("outputs/_sig_e_panel_ops6c/sig_e_panel_ops6c_visual_polish_result.json")

CSS_APPEND = '\n/* SIG-E-PANEL-OPS6C_VISUAL_POLISH_v1_0\n   Professional dark-first UI polish:\n   - fixes low-contrast light-mode rendering\n   - adds tabbar update age placement\n   - improves cards, spacing, readability and hierarchy\n*/\n\n:root {\n  --bg: #070d14;\n  --bg-soft: #0a121b;\n  --panel: rgba(13, 24, 36, 0.86);\n  --panel-strong: rgba(14, 27, 40, 0.96);\n  --line: rgba(148, 181, 209, 0.18);\n  --line-strong: rgba(148, 181, 209, 0.34);\n  --text: #edf6ff;\n  --muted: #a8bbcc;\n  --faint: #7f94a7;\n  --ink-strong: #f7fbff;\n  --accent: #67e8f9;\n  --accent-2: #8bffd2;\n  --warn: #fde68a;\n  --danger: #fda4af;\n  --ok: #86efac;\n  --card-grad-1: rgba(15, 29, 43, 0.92);\n  --card-grad-2: rgba(9, 18, 29, 0.88);\n}\n\nhtml,\nhtml[data-panel] {\n  color-scheme: dark;\n  background:\n    radial-gradient(circle at 16% 0%, rgba(103, 232, 249, 0.14), transparent 34rem),\n    radial-gradient(circle at 88% 12%, rgba(139, 255, 210, 0.10), transparent 30rem),\n    linear-gradient(145deg, #05080d 0%, #071018 46%, #09111a 100%) !important;\n}\n\nbody {\n  background: transparent !important;\n  color: var(--text) !important;\n  -webkit-font-smoothing: antialiased;\n  text-rendering: geometricPrecision;\n}\n\n.app-shell {\n  padding-top: 28px;\n}\n\nh1, h2, h3,\n.hero-status h2,\n.metric-card strong,\n.ops-card strong,\n.debug-card strong,\n.memory-card strong,\n.diagnostic-card strong {\n  color: var(--ink-strong) !important;\n  text-shadow: 0 1px 0 rgba(0,0,0,0.16);\n}\n\n.hero-card,\n.metric-card,\n.focus-card,\n.lane-card,\n.ops-card,\n.boundary-card,\n.debug-card,\n.memory-card,\n.history-card,\n.diagnostic-card {\n  color: var(--text) !important;\n  background:\n    linear-gradient(145deg, var(--card-grad-1), var(--card-grad-2)) !important;\n  border-color: rgba(157, 190, 217, 0.20) !important;\n  box-shadow:\n    0 28px 90px rgba(0, 0, 0, 0.40),\n    inset 0 1px 0 rgba(255,255,255,0.045) !important;\n}\n\n.hero-card,\n.focus-card,\n.boundary-card {\n  border-radius: 30px !important;\n}\n\n.metric-card {\n  border-radius: 26px !important;\n}\n\n.hero-status h2 {\n  max-width: 560px;\n  font-size: clamp(2.2rem, 5vw, 4.1rem) !important;\n  line-height: 0.98 !important;\n  letter-spacing: -0.075em !important;\n}\n\n.hero-status .muted,\n.metric-card span,\n.ops-card span,\n.debug-card span,\n.memory-card span,\n.diagnostic-card span,\n.lane-reason,\n.boundary-card p,\n.section-lead {\n  color: var(--muted) !important;\n}\n\n.eyebrow,\n.label,\n.lane-kicker {\n  color: var(--faint) !important;\n}\n\n.topbar {\n  padding-bottom: 14px !important;\n}\n\n.brand-mark {\n  background:\n    linear-gradient(145deg, rgba(103,232,249,0.14), rgba(139,255,210,0.05)) !important;\n  border-color: rgba(103,232,249,0.18) !important;\n}\n\n.tabbar-shell {\n  display: flex;\n  align-items: center;\n  gap: 12px;\n  padding: 8px;\n  margin: 0 0 16px;\n  border: 1px solid rgba(157, 190, 217, 0.16);\n  border-radius: 999px;\n  background:\n    linear-gradient(145deg, rgba(255,255,255,0.060), rgba(255,255,255,0.025));\n  box-shadow:\n    0 20px 60px rgba(0,0,0,0.24),\n    inset 0 1px 0 rgba(255,255,255,0.04);\n}\n\n.tabbar-shell .tabbar {\n  flex: 1;\n  min-width: 0;\n  margin: 0 !important;\n  padding: 0 !important;\n  border: 0 !important;\n  background: transparent !important;\n  box-shadow: none !important;\n}\n\n.tab-meta {\n  display: flex;\n  align-items: center;\n  justify-content: flex-end;\n  gap: 8px;\n  flex: 0 0 auto;\n  min-width: max-content;\n}\n\n.tab-update-age,\n.tab-update-time {\n  display: inline-flex;\n  align-items: center;\n  min-height: 34px;\n  padding: 0 12px;\n  border-radius: 999px;\n  font-size: 0.76rem;\n  font-weight: 900;\n  letter-spacing: -0.01em;\n  color: var(--text);\n  background: rgba(255,255,255,0.055);\n  border: 1px solid rgba(255,255,255,0.08);\n}\n\n.tab-update-age::before {\n  content: "";\n  width: 7px;\n  height: 7px;\n  margin-right: 8px;\n  border-radius: 99px;\n  background: var(--ok);\n  box-shadow: 0 0 0 5px rgba(134,239,172,0.12);\n}\n\n.tab-update-age.warn::before {\n  background: var(--warn);\n  box-shadow: 0 0 0 5px rgba(253,230,138,0.12);\n}\n\n.tab-update-age.danger::before {\n  background: var(--danger);\n  box-shadow: 0 0 0 5px rgba(253,164,175,0.12);\n}\n\n.tab-update-time {\n  color: var(--muted);\n  font-weight: 800;\n}\n\n.tab {\n  color: #b9c8d6 !important;\n  transition: transform 160ms ease, background 160ms ease, color 160ms ease;\n}\n\n.tab:hover {\n  color: var(--ink-strong) !important;\n  background: rgba(255,255,255,0.045);\n}\n\n.tab.active {\n  color: #071018 !important;\n  background: linear-gradient(145deg, #a7f3d0, #67e8f9) !important;\n  box-shadow:\n    0 8px 24px rgba(103,232,249,0.18),\n    inset 0 1px 0 rgba(255,255,255,0.42) !important;\n}\n\n.system-pill,\n.section-badge,\n.safety-chip,\n.lane-badge,\n.icon-button,\n.boundary-tags span {\n  background: rgba(255,255,255,0.055) !important;\n  border-color: rgba(255,255,255,0.10) !important;\n  color: var(--text) !important;\n}\n\n.system-pill.ok {\n  color: #d8ffe8 !important;\n  background: rgba(134,239,172,0.10) !important;\n  border-color: rgba(134,239,172,0.22) !important;\n}\n\n.icon-button {\n  cursor: pointer;\n  color: var(--text) !important;\n  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;\n}\n\n.icon-button:hover {\n  transform: translateY(-1px);\n  background: rgba(103,232,249,0.10) !important;\n  border-color: rgba(103,232,249,0.25) !important;\n}\n\n.hero-grid {\n  gap: 16px !important;\n}\n\n.hero-card,\n.metric-card {\n  min-height: 206px !important;\n}\n\n.hero-meta span,\n.lane-meta span,\n.mini-meta span {\n  color: #c5d4e0 !important;\n  background: rgba(255,255,255,0.055) !important;\n  border-color: rgba(255,255,255,0.09) !important;\n}\n\n.empty-state {\n  background: rgba(2, 9, 15, 0.30) !important;\n  border-color: rgba(157, 190, 217, 0.24) !important;\n}\n\n.empty-state strong {\n  color: var(--ink-strong) !important;\n}\n\n.lane-card::before {\n  background: linear-gradient(90deg, var(--accent), rgba(139,255,210,0.25), transparent) !important;\n}\n\n.stage-rail span {\n  background: rgba(255,255,255,0.08) !important;\n}\n\n.stage-rail span.done { background: rgba(134, 239, 172, 0.78) !important; }\n.stage-rail span.current { background: rgba(253, 230, 138, 0.92) !important; }\n.stage-rail span.blocked { background: rgba(252, 165, 165, 0.72) !important; }\n\n.memory-card,\n.debug-card,\n.diagnostic-card {\n  min-height: 168px !important;\n}\n\n.boundary-card {\n  background:\n    linear-gradient(145deg, rgba(27, 18, 27, 0.86), rgba(12, 20, 30, 0.90)) !important;\n  border-color: rgba(252, 165, 165, 0.20) !important;\n}\n\n.boundary-tags span {\n  color: #ffd7d7 !important;\n  border-color: rgba(252, 165, 165, 0.24) !important;\n  background: rgba(252, 165, 165, 0.08) !important;\n}\n\n/* Override the old light-mode block from OPS6B. The console is dark-first because\n   the attached screenshot showed low contrast in light mode. */\n@media (prefers-color-scheme: light) {\n  :root {\n    --bg: #070d14 !important;\n    --bg-soft: #0a121b !important;\n    --panel: rgba(13, 24, 36, 0.86) !important;\n    --panel-strong: rgba(14, 27, 40, 0.96) !important;\n    --line: rgba(148, 181, 209, 0.18) !important;\n    --line-strong: rgba(148, 181, 209, 0.34) !important;\n    --text: #edf6ff !important;\n    --muted: #a8bbcc !important;\n    --faint: #7f94a7 !important;\n    --shadow: 0 24px 80px rgba(0, 0, 0, 0.38) !important;\n  }\n\n  html,\n  html[data-panel] {\n    background:\n      radial-gradient(circle at 16% 0%, rgba(103, 232, 249, 0.14), transparent 34rem),\n      radial-gradient(circle at 88% 12%, rgba(139, 255, 210, 0.10), transparent 30rem),\n      linear-gradient(145deg, #05080d 0%, #071018 46%, #09111a 100%) !important;\n  }\n}\n\n@media (max-width: 820px) {\n  .tabbar-shell {\n    align-items: stretch;\n    flex-direction: column;\n    border-radius: 28px;\n  }\n\n  .tab-meta {\n    justify-content: space-between;\n  }\n\n  .tabbar-shell .tabbar {\n    width: 100%;\n  }\n}\n\n@media (max-width: 680px) {\n  .app-shell {\n    width: min(100% - 18px, 1180px) !important;\n  }\n\n  .hero-card,\n  .metric-card {\n    min-height: 150px !important;\n  }\n\n  .hero-status h2 {\n    font-size: clamp(2rem, 13vw, 3.2rem) !important;\n  }\n\n  .tab-update-time {\n    display: none;\n  }\n}\n'

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def backup(path):
    b = path.with_suffix(path.suffix + ".bak_ops6c")
    shutil.copyfile(path, b)
    return str(b)

def patch_index():
    item = {"file": str(INDEX), "exists": INDEX.exists(), "patched": False, "reason": None}
    if not INDEX.exists():
        item["reason"] = "MISSING"
        return item
    text = INDEX.read_text(encoding="utf-8")
    original = text

    if "SIG-E-PANEL-OPS6C_VISUAL_POLISH_v1_0" not in text:
        text = text.replace(
            '<html lang="en" data-panel="SIG-E-PANEL-OPS6B_TABBED_RESEARCH_CONSOLE_v1_0">',
            '<html lang="en" data-panel="SIG-E-PANEL-OPS6C_VISUAL_POLISH_v1_0">'
        )
        text = text.replace(
            '<title>TradingOS · SIG-E Research Console</title>',
            '<title>TradingOS · SIG-E Research Console · OPS6C</title>'
        )

    if 'id="tabUpdateAge"' not in text:
        pattern = re.compile(r'(<nav class="tabbar" aria-label="SIG-E panel sections">.*?</nav>)', re.DOTALL)
        m = pattern.search(text)
        if m:
            wrapped = (
                '<div class="tabbar-shell">\n'
                + m.group(1)
                + '\n  <div class="tab-meta" aria-label="Refresh age">\n'
                + '    <span class="tab-update-age" id="tabUpdateAge">Updated —</span>\n'
                + '    <span class="tab-update-time" id="tabUpdateTime">—</span>\n'
                + '  </div>\n'
                + '</div>'
            )
            text = text[:m.start()] + wrapped + text[m.end():]
        else:
            item["reason"] = "TABBAR_NOT_FOUND"
            return item

    if text != original:
        item["backup"] = backup(INDEX)
        INDEX.write_text(text, encoding="utf-8")
        item["patched"] = True
        item["reason"] = "INDEX_TAB_UPDATE_AGE_ADDED"
    else:
        item["reason"] = "ALREADY_PRESENT"
    return item

def patch_css():
    item = {"file": str(CSS), "exists": CSS.exists(), "patched": False, "reason": None}
    if not CSS.exists():
        item["reason"] = "MISSING"
        return item
    text = CSS.read_text(encoding="utf-8")
    if "SIG-E-PANEL-OPS6C_VISUAL_POLISH_v1_0" in text:
        item["reason"] = "ALREADY_PRESENT"
        return item
    item["backup"] = backup(CSS)
    CSS.write_text(text.rstrip() + "\n\n" + CSS_APPEND + "\n", encoding="utf-8")
    item["patched"] = True
    item["reason"] = "CSS_VISUAL_POLISH_APPENDED"
    return item

def patch_js():
    item = {"file": str(JS), "exists": JS.exists(), "patched": False, "reason": None}
    if not JS.exists():
        item["reason"] = "MISSING"
        return item
    text = JS.read_text(encoding="utf-8")
    original = text

    if "SIG-E-PANEL-OPS6C_VISUAL_POLISH_v1_0" not in text:
        text = text.replace(
            'const VERSION = "SIG-E-PANEL-OPS6B_TABBED_RESEARCH_CONSOLE_v1_0";',
            'const VERSION = "SIG-E-PANEL-OPS6C_VISUAL_POLISH_v1_0";'
        )
        text = text.replace(
            '/* SIG-E-PANEL-OPS6B_TABBED_RESEARCH_CONSOLE_v1_0 */',
            '/* SIG-E-PANEL-OPS6C_VISUAL_POLISH_v1_0 */'
        )

    if "function updateTabRefreshAge" not in text:
        insert_after = '''  function formatTime(value) {
    const d = parseUtc(value);
    if (!d) return "—";
    return d.toISOString().replace(".000Z", "Z");
  }
'''
        helper = '''
  function updateTabRefreshAge(createdUtc) {
    const age = ageMinutes(createdUtc);
    const ageEl = $("tabUpdateAge");
    const timeEl = $("tabUpdateTime");
    if (!ageEl || !timeEl) return;

    ageEl.classList.remove("warn", "danger");

    if (age === null) {
      ageEl.textContent = "Updated —";
      timeEl.textContent = "refresh time unavailable";
      ageEl.classList.add("warn");
      return;
    }

    const label = age <= 1 ? "Updated just now" : `Updated ${age}m ago`;
    ageEl.textContent = label;
    timeEl.textContent = formatTime(createdUtc);

    if (age > 30) ageEl.classList.add("danger");
    else if (age > 10) ageEl.classList.add("warn");
  }
'''
        if insert_after in text:
            text = text.replace(insert_after, insert_after + helper, 1)
        else:
            item["reason"] = "FORMAT_TIME_ANCHOR_NOT_FOUND"
            return item

    if "updateTabRefreshAge(createdUtc);" not in text:
        anchor = '$("portfolioSource").textContent = portfolioPath ? portfolioPath.split("/").slice(-2).join("/") : "source —";'
        if anchor in text:
            text = text.replace(anchor, anchor + "\n    updateTabRefreshAge(createdUtc);", 1)
        else:
            item["reason"] = "PORTFOLIO_SOURCE_ANCHOR_NOT_FOUND"
            return item

    if text != original:
        item["backup"] = backup(JS)
        JS.write_text(text, encoding="utf-8")
        item["patched"] = True
        item["reason"] = "JS_UPDATE_AGE_ADDED"
    else:
        item["reason"] = "ALREADY_PRESENT"
    return item

def main():
    results = [patch_index(), patch_css(), patch_js()]
    status = "PASS" if all(r.get("patched") or r.get("reason") == "ALREADY_PRESENT" for r in results) else "PARTIAL_OR_FAIL"
    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "patch_status": status,
        "results": results,
        "changes": [
            "tabbar update-age indicator on the right side",
            "dark-first color system to fix low contrast",
            "stronger card contrast and modern depth",
            "improved tab active/hover styling",
            "mobile-friendly tabbar wrapping"
        ],
        "boundary": [
            "PANEL_VISUAL_POLISH_ONLY",
            "DISPLAY_ONLY",
            "SHADOW_RESEARCH_ONLY",
            "NOT_SIGNAL",
            "NO_TRADE_PROPOSAL",
            "NO_ENTRY_STOP_TARGET",
            "NO_BROKER_EXECUTION",
            "NO_AUTO_EXECUTION"
        ]
    }
    write_json(OUT, result)
    print("SIG_E_PANEL_OPS6C_VISUAL_POLISH_" + status)
    for r in results:
        print(r["file"] + " -> " + str(r["reason"]))
    if status != "PASS":
        raise SystemExit(2)

if __name__ == "__main__":
    main()

/*
 BRAIN4-UI-STABILIZE-02 — safe visual rollback/stabilizer

Purpose:
- Remove aggressive BRAIN4-UI-OPS-01 DOM mutations that created duplicate "Live View" pills
  and distorted the live event card layout.
- Keep only safe non-authority UI marker.
- UI only. No signal, no trading authority.
*/
(function () {
  "use strict";

  const PATCH_ID = "BRAIN4_UI_STABILIZE_02_v1_0";

  function qsa(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function removeOldUiMutations() {
    qsa(".brain4-ui-eyebrow").forEach(el => el.remove());

    const classes = [
      "brain4-ui-card",
      "brain4-ui-shadow-card",
      "brain4-ui-hero-card",
      "brain4-ui-empty-state",
      "brain4-ui-library-card",
      "brain4-ui-pattern-card",
      "brain4-ui-tabrow",
      "brain4-ui-btn",
      "brain4-ui-pill",
      "brain4-ui-chipbar-host",
      "brain4-ui-details",
      "brain4-ui-clamp-4",
      "brain4-ui-muted-link"
    ];

    qsa("*").forEach(el => {
      classes.forEach(cls => el.classList.remove(cls));
    });
  }

  function init() {
    removeOldUiMutations();
    document.documentElement.classList.remove("brain4-ui-ops01-root");
    document.body.classList.remove("brain4-ui-ops01-body");
    document.documentElement.classList.add("brain4-ui-stabilize02-root");
    document.body.classList.add("brain4-ui-stabilize02-body");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.BRAIN4_UI_OPS_01 = { patchId: PATCH_ID, init };
})();

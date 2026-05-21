#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run SHADOW_CANDIDATE_UNIVERSE_01 and feed active research candidates into existing shadow observation ledger."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run(args):
    print("RUN:", " ".join([sys.executable] + args))
    subprocess.run([sys.executable] + args, check=True)


def main() -> int:
    # 1) Build universe outputs and active research-only candidate intake.
    run(["scripts/build_shadow_candidate_universe_01.py"])

    # 2) Merge active universe candidates into the existing shadow candidate ledger.
    #    This is deliberately shadow-only and uses existing observation machinery. It does not alter memories.
    intake = "runtime/sig_shadow_candidate_universe/shadow_candidate_universe_signal_intake_current.json"
    if Path(intake).exists():
        run(["scripts/update_sig_shadow_candidate_ledger.py", "--intake", intake])
        run(["scripts/update_sig_shadow_observations.py"])
        run(["scripts/summarize_sig_shadow_ledger.py"])

    # 3) Validate both the universe and the base shadow ledger boundaries.
    run(["scripts/validate_shadow_candidate_universe_01.py"])
    run(["scripts/validate_sig_shadow_01b_integrated_outputs.py"])

    print(json.dumps({
        "status": "SHADOW_CANDIDATE_UNIVERSE_01_PIPELINE_COMPLETED",
        "research_shadow_only": True,
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

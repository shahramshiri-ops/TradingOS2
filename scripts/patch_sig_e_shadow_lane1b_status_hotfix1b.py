
import json
import re
import shutil
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1B"

TARGET = Path("scripts/build_sig_e_shadow_detector1b_overlap_diagnostic.py")
OUT = Path("outputs/_sig_e_shadow_lane1b_status_hotfix1/sig_e_shadow_lane1b_status_hotfix1b_patch_result.json")

NORMALIZER = 
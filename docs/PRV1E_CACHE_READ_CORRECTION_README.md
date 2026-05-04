# PRV1E Cache Read Correction Patch

This patch corrects the PRV1E detector so it must actually read local provider cache bars before passing validation.

Run from `personal_runtime_v1`:

```bat
scripts\run_candidate_detection_rule_engine_cache_read_fix.bat
python scripts\validate_candidate_detection_outputs_strict.py .
```

The patch performs no provider call and does not read any API key or `.env` file. It reads local cache snapshots under `data/provider_cache/twelve_data/*.json`.

Send back the standard PRV1E files after running.

# Workflow YAML Sanitize Hotfix — Python 3.8 Fix

The previous sanitize script failed on Python 3.8 because `Path.write_text(..., newline="\n")` is not supported.

This hotfix replaces that call with Python 3.8-compatible:

```python
with open(path, "w", encoding="utf-8", newline="\n") as f:
    f.write(text)
```

It still removes YAML-forbidden control characters from:

`.github/workflows/sig_live_m5_refresh_resample_brain.yml`

No detector logic, trading logic, signal logic, broker/execution, or portfolio semantics are changed.

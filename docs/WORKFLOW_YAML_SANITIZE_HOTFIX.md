# Workflow YAML Sanitize Hotfix

GitHub reported:

`Invalid workflow file — You have an error in your yaml syntax`

The uploaded workflow contained C1 control characters, especially `#x009d`, introduced by mojibake in comments like corrupted em-dashes. Even though these were in comments, GitHub rejects the whole workflow file.

This hotfix:
- removes YAML-forbidden control characters from `.github/workflows/sig_live_m5_refresh_resample_brain.yml`
- normalizes corrupted comment dashes to plain ASCII
- preserves the workflow name and SIG-E shadow detector chain
- verifies that no C0/C1 forbidden characters remain

It does not change detector logic, signals, trading rules, broker/execution, or portfolio semantics.

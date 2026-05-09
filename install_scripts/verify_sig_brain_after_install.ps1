param(
    [Parameter(Mandatory=$false)]
    [string]$ProductPath = "."
)
$ErrorActionPreference = "Stop"
Push-Location $ProductPath
try {
    py scripts\build_sig_brain5_live_context.py
    py scripts\validate_sig_brain5_context_builder.py
    py scripts\validate_sig_brain6_context_registry.py
    py scripts\check_sig_brain6_runtime_context_coverage.py
    Write-Host "PASS: SIG Brain architecture validations completed."
} finally { Pop-Location }

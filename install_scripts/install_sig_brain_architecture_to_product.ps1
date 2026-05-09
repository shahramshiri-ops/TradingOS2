param(
    [Parameter(Mandatory=$true)]
    [string]$ProductPath
)
$ErrorActionPreference = "Stop"
$PackRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Overlay = Join-Path (Split-Path -Parent $PackRoot) "github_overlay_product_root"
if (!(Test-Path $Overlay)) { throw "Overlay folder not found: $Overlay" }
if (!(Test-Path $ProductPath)) { throw "ProductPath not found: $ProductPath" }
Write-Host "Installing SIG Brain architecture overlay..."
Write-Host "From: $Overlay"
Write-Host "To:   $ProductPath"
Copy-Item -Path (Join-Path $Overlay "*") -Destination $ProductPath -Recurse -Force
Write-Host "Installed. Now validate from the product folder."

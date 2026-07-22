[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

$python = Get-Command python -ErrorAction Stop
Write-Host "FAB will open Google authorization in your browser." -ForegroundColor Cyan
Write-Host "Approve Drive access only for the Google account that owns the configured intake folder."
Write-Host ""

& $python.Source -m src.authorize_google_drive
if ($LASTEXITCODE -ne 0) {
    throw "Google Drive authorization was not completed. Review the status above."
}

Write-Host ""
Write-Host "Google Drive is authorized for FAB." -ForegroundColor Green
Write-Host "Restart FAB so the worker and dashboard immediately reload the token."

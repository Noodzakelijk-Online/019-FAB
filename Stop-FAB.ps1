[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimePath = Join-Path $root "data\fab-runtime.json"

function Stop-FabProcessTree {
    param(
        [AllowNull()][object]$ProcessId,
        [Parameter(Mandatory = $true)][string]$CommandMarker,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if (-not $ProcessId) {
        return
    }

    $rootProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if (-not $rootProcess) {
        return
    }
    if (-not $rootProcess.CommandLine -or $rootProcess.CommandLine -notlike "*$CommandMarker*") {
        Write-Warning "Refusing to stop PID $ProcessId because it no longer matches $Name."
        return
    }

    $processIds = [System.Collections.Generic.List[int]]::new()
    $pending = [System.Collections.Generic.Queue[int]]::new()
    $pending.Enqueue([int]$ProcessId)
    while ($pending.Count -gt 0) {
        $currentId = $pending.Dequeue()
        $processIds.Add($currentId)
        Get-CimInstance Win32_Process -Filter "ParentProcessId = $currentId" -ErrorAction SilentlyContinue | ForEach-Object {
            $pending.Enqueue([int]$_.ProcessId)
        }
    }

    for ($index = $processIds.Count - 1; $index -ge 0; $index--) {
        Stop-Process -Id $processIds[$index] -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Stopped $Name."
}

if (-not (Test-Path -LiteralPath $runtimePath)) {
    Write-Host "No FAB runtime metadata was found. The managed services are already stopped."
    exit 0
}

$runtime = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
Stop-FabProcessTree -ProcessId $runtime.webPid -CommandMarker "pnpm" -Name "FAB dashboard"
Stop-FabProcessTree -ProcessId $runtime.workerPid -CommandMarker "src.run_worker" -Name "FAB autonomous worker"
Stop-FabProcessTree -ProcessId $runtime.apiPid -CommandMarker "src.operations.local_api" -Name "FAB ledger API"

Remove-Item -LiteralPath $runtimePath -Force
Write-Host "FAB local services are stopped."

$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$orbTaskName='TradingBacktests-QQQ-ORB-Simulation'
function Get-OrbPython([switch]$Windowless) {
    $orbExecutable=if ($Windowless) {'pythonw.exe'} else {'python.exe'}
    $orbPath=Join-Path 'C:/Python314' $orbExecutable
    if (Test-Path -LiteralPath $orbPath) { return $orbPath }
    return (Get-Command $orbExecutable -ErrorAction Stop).Source
}

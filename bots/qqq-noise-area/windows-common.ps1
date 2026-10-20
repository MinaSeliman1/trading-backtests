$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$qqqWorkspace = (Resolve-Path -LiteralPath '../../..').Path
$qqqPackages = Join-Path $qqqWorkspace '.python_packages'
if (Test-Path -LiteralPath $qqqPackages) { $env:PYTHONPATH = $qqqPackages }
$qqqTaskName = 'TradingBacktests-QQQ-NoiseArea-Simulation'
function Get-QqqPython([switch]$Windowless) {
    $qqqExecutable = if ($Windowless) { 'pythonw.exe' } else { 'python.exe' }
    $qqqCandidates = @((Join-Path $PSScriptRoot ".venv/Scripts/$qqqExecutable"), (Join-Path 'C:/Python314' $qqqExecutable))
    foreach ($qqqCandidate in $qqqCandidates) {
        if (Test-Path -LiteralPath $qqqCandidate) { return (Resolve-Path -LiteralPath $qqqCandidate).Path }
    }
    return (Get-Command $qqqExecutable -ErrorAction Stop).Source
}

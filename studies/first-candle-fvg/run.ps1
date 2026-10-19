param([Parameter(ValueFromRemainingArguments = $true)][string[]]$TaskArgs)
$ErrorActionPreference = 'Stop'
$env:PYTHONPATH = Join-Path $PSScriptRoot '.python_packages'
$env:MPLCONFIGDIR = Join-Path $PSScriptRoot '.mplconfig'
Push-Location -LiteralPath $PSScriptRoot
try {
    python -m fvg_backtest @TaskArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }

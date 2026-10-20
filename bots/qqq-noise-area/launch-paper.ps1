param(
    [ValidateSet('paper','shadow')][string]$Mode = 'shadow',
    [ValidateSet('iex','sip')][string]$Feed = 'sip',
    [switch]$Check,
    [string]$ReadyFile = ''
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$studyWorkspace = (Resolve-Path ../../..).Path
$localPackages = Join-Path $studyWorkspace '.python_packages'
if (Test-Path -LiteralPath $localPackages) { $env:PYTHONPATH = $localPackages }
$botPython = if (Test-Path -LiteralPath '.venv/Scripts/python.exe') { (Resolve-Path '.venv/Scripts/python.exe').Path } elseif (Test-Path -LiteralPath 'C:/Python314/python.exe') { 'C:/Python314/python.exe' } else { 'python' }
$botArgs = @('-m','qqq_paper','--mode',$Mode,'--feed',$Feed)
if ($Check) { $botArgs += '--check' }
function Read-BotSecret([string]$Label) {
    $maskedValue = Read-Host $Label -AsSecureString
    $secretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($maskedValue)
    try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPointer) }
}
try {
    Write-Host 'QQQ NOISE AREA - ALPACA PAPER UNIQUEMENT. Cles masquees, non sauvegardees.'
    $env:ALPACA_PAPER_KEY_ID = Read-BotSecret 'Paper API Key ID'
    $env:ALPACA_PAPER_SECRET_KEY = Read-BotSecret 'Paper API Secret'
    if ($ReadyFile) {
        Write-Host 'Cles gardees dans cette console. Attente de la fin des verifications ; aucun ordre envoye.'
        while (-not (Test-Path -LiteralPath $ReadyFile)) { Start-Sleep -Seconds 1 }
    }
    & $botPython @botArgs
} finally {
    Remove-Item Env:ALPACA_PAPER_KEY_ID -ErrorAction SilentlyContinue
    Remove-Item Env:ALPACA_PAPER_SECRET_KEY -ErrorAction SilentlyContinue
    Write-Host 'La console peut etre fermee. Les cles n ont pas ete sauvegardees.'
}

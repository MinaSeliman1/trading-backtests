. (Join-Path $PSScriptRoot 'windows-common.ps1')
$Host.UI.RawUI.WindowTitle = 'QQQ - CONFIGURATION WINDOWS'
& (Get-QqqPython) -m qqq_paper.windows_setup --runtime (Join-Path $PSScriptRoot 'runtime')
$qqqSetupExit = $LASTEXITCODE
if ($qqqSetupExit -eq 0) {
    Write-Host 'Configuration terminee. Cette fenetre va se fermer ; le bot utilisera une tache sans console.'
    Start-Sleep -Seconds 3
} else {
    Write-Host 'Configuration non terminee. Aucune cle ne doit etre envoyee dans le chat.'
    [void](Read-Host 'Appuyez sur Entree pour fermer')
}
exit $qqqSetupExit

param([switch]$Apply)
$ErrorActionPreference='Stop'
# Permanent AC fallback for both local shadow bots. No task, key or ledger access.
function Get-AcAvailabilityScheme {
    $acText=(& powercfg /getactivescheme | Out-String)
    if ($LASTEXITCODE -ne 0) {throw 'Cannot read active power scheme.'}
    $acGuid=[regex]::Match($acText,'[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}').Value
    if (-not $acGuid) {throw 'Cannot identify active power scheme.'}
    return $acGuid
}
function Get-AcAvailabilityPolicy($Scheme) {
    $acValues=[ordered]@{}
    foreach ($acAlias in @('RTCWAKE','STANDBYIDLE','HIBERNATEIDLE')) {
        $acText=(& powercfg /query $Scheme SUB_SLEEP $acAlias | Out-String)
        if ($LASTEXITCODE -ne 0) {throw ('Cannot read sleep policy: '+$acAlias)}
        $acIndices=[regex]::Matches($acText,'0x([0-9a-fA-F]{8})')
        # Timeout settings also print hex minimum/maximum BEFORE the AC/DC values.
        if ($acIndices.Count -lt 2) {throw ('Cannot parse AC/DC indices: '+$acAlias)}
        $acValues[$acAlias]=[ordered]@{ac=[Convert]::ToInt64($acIndices[$acIndices.Count-2].Groups[1].Value,16);dc=[Convert]::ToInt64($acIndices[$acIndices.Count-1].Groups[1].Value,16)}
    }
    return $acValues
}
$acScheme=Get-AcAvailabilityScheme
$acBefore=Get-AcAvailabilityPolicy $acScheme
$acDesired=[ordered]@{RTCWAKE=1;STANDBYIDLE=0;HIBERNATEIDLE=0}
if (-not $Apply) {
    [ordered]@{state='audit_only';scheme=$acScheme;settings=$acBefore;desired_ac=$acDesired} | ConvertTo-Json -Depth 6
    return
}
$acFolder=Join-Path $PSScriptRoot 'runtime/windows'
New-Item -ItemType Directory -Path $acFolder -Force | Out-Null
$acBackup=Join-Path $acFolder ('ac_availability_before-'+$acScheme+'.json')
if (-not (Test-Path -LiteralPath $acBackup)) {
    [ordered]@{scheme=$acScheme;utc=[DateTime]::UtcNow.ToString('o');settings=$acBefore} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $acBackup -Encoding UTF8
}
$acAttempted=@()
try {
    foreach ($acAlias in $acDesired.Keys) {
        if ($acBefore[$acAlias].ac -ne $acDesired[$acAlias]) {
            $acAttempted+=,$acAlias
            & powercfg /setacvalueindex $acScheme SUB_SLEEP $acAlias $acDesired[$acAlias]
            if ($LASTEXITCODE -ne 0) {throw ('Cannot set AC sleep policy: '+$acAlias)}
        }
    }
    if ($acAttempted.Count) {
        & powercfg /setactive $acScheme
        if ($LASTEXITCODE -ne 0) {throw 'Cannot apply active power plan.'}
    }
    if ((Get-AcAvailabilityScheme) -ne $acScheme) {throw 'Active power scheme changed during configuration.'}
    $acAfter=Get-AcAvailabilityPolicy $acScheme
    foreach ($acAlias in $acDesired.Keys) {
        if ($acAfter[$acAlias].ac -ne $acDesired[$acAlias] -or $acAfter[$acAlias].dc -ne $acBefore[$acAlias].dc) {throw ('AC verification or DC preservation failed: '+$acAlias)}
    }
    $acProof=[ordered]@{state='applied';scheme=$acScheme;utc=[DateTime]::UtcNow.ToString('o');backup=$acBackup;before=$acBefore;after=$acAfter;dc_preserved=$true;scope='active_plan_ac_automatic_sleep_only'}
    $acProof | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $acFolder 'ac_availability_current.json') -Encoding UTF8
} catch {
    $acError=$_
    $acRestored=$true
    for ($acIndex=$acAttempted.Count-1;$acIndex -ge 0;$acIndex--) {
        $acAlias=$acAttempted[$acIndex]
        & powercfg /setacvalueindex $acScheme SUB_SLEEP $acAlias $acBefore[$acAlias].ac
        if ($LASTEXITCODE -ne 0) {$acRestored=$false}
    }
    if ($acAttempted.Count) {
        & powercfg /setactive $acScheme
        if ($LASTEXITCODE -ne 0) {$acRestored=$false}
    }
    try {
        $acRestoredValues=Get-AcAvailabilityPolicy $acScheme
        foreach ($acAlias in $acDesired.Keys) {
            if ($acRestoredValues[$acAlias].ac -ne $acBefore[$acAlias].ac -or $acRestoredValues[$acAlias].dc -ne $acBefore[$acAlias].dc) {$acRestored=$false}
        }
    } catch {$acRestored=$false}
    try {
    [ordered]@{state=$(if($acRestored){'failed_rolled_back'}else{'rollback_incomplete'});scheme=$acScheme;utc=[DateTime]::UtcNow.ToString('o');backup=$acBackup} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $acFolder 'ac_availability_current.json') -Encoding UTF8
    } catch {Write-Warning 'Rollback attempted; the status proof could not be written.'}
    throw $acError
}
$acProof | ConvertTo-Json -Depth 6

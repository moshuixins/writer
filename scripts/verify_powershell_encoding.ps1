Set-StrictMode -Version Latest

. $PSScriptRoot\powershell_utf8.ps1

$samplePath = Join-Path $env:TEMP 'writer-powershell-utf8-check.txt'
$sampleText = '中文编码校验 ABC 123'

Write-Utf8NoBomFile -Path $samplePath -Content $sampleText | Out-Null

$bytes = [System.IO.File]::ReadAllBytes($samplePath)
if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    throw "BOM detected in $samplePath"
}

$text = Read-Utf8Text -Path $samplePath
if ($text -ne $sampleText) {
    throw "Chinese text verification failed: $text"
}

Write-Host "PowerShell UTF-8 no BOM check passed: $samplePath"

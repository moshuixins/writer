Set-StrictMode -Version Latest

$script:Utf8NoBom = [System.Text.UTF8Encoding]::new($false)

function Use-WriterUtf8 {
    [CmdletBinding()]
    param()

    [Console]::InputEncoding = $script:Utf8NoBom
    [Console]::OutputEncoding = $script:Utf8NoBom
    $global:OutputEncoding = $script:Utf8NoBom
    $env:PYTHONIOENCODING = 'utf-8'

    $chcp = Get-Command chcp.com -ErrorAction SilentlyContinue
    if ($null -ne $chcp) {
        & $chcp.Path 65001 > $null
    }
}

function Resolve-WriterPath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (Test-Path -LiteralPath $Path) {
        return (Resolve-Path -LiteralPath $Path).Path
    }

    return [System.IO.Path]::GetFullPath($Path)
}

function Read-Utf8Text {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $resolved = Resolve-WriterPath -Path $Path
    return [System.IO.File]::ReadAllText($resolved, $script:Utf8NoBom)
}

function Write-Utf8NoBomFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path,
        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    $resolved = Resolve-WriterPath -Path $Path
    $directory = [System.IO.Path]::GetDirectoryName($resolved)
    if ($directory -and -not (Test-Path -LiteralPath $directory)) {
        [System.IO.Directory]::CreateDirectory($directory) | Out-Null
    }

    [System.IO.File]::WriteAllText($resolved, $Content, $script:Utf8NoBom)
    return $resolved
}

function Append-Utf8NoBomFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path,
        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    $resolved = Resolve-WriterPath -Path $Path
    $directory = [System.IO.Path]::GetDirectoryName($resolved)
    if ($directory -and -not (Test-Path -LiteralPath $directory)) {
        [System.IO.Directory]::CreateDirectory($directory) | Out-Null
    }

    $writer = [System.IO.StreamWriter]::new($resolved, $true, $script:Utf8NoBom)
    try {
        $writer.Write($Content)
    }
    finally {
        $writer.Dispose()
    }

    return $resolved
}

function Convert-FileToUtf8NoBom {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $resolved = Resolve-WriterPath -Path $Path
    $text = [System.IO.File]::ReadAllText($resolved)
    [System.IO.File]::WriteAllText($resolved, $text, $script:Utf8NoBom)
    return $resolved
}

Use-WriterUtf8

param(
    [string]$OutputPath = (Join-Path $PSScriptRoot "..\browser_call\build\ProcessLoopbackCapture.exe")
)

$ErrorActionPreference = "Stop"
$compiler = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path -LiteralPath $compiler -PathType Leaf)) {
    $compiler = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe"
}
if (-not (Test-Path -LiteralPath $compiler -PathType Leaf)) {
    throw "The Windows C# compiler is unavailable."
}

$source = Join-Path $PSScriptRoot "ProcessLoopbackCapture.cs"
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
$outputDirectory = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null

& $compiler /nologo /optimize+ /target:exe "/out:$resolvedOutput" $source
if ($LASTEXITCODE -ne 0) {
    throw "Process-loopback helper compilation failed."
}

& $resolvedOutput --self-test
if ($LASTEXITCODE -ne 0) {
    throw "Process-loopback helper self-test failed."
}

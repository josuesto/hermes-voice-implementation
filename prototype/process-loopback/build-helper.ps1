$canonical = Join-Path $PSScriptRoot "..\..\companion\process_loopback\build-helper.ps1"
& $canonical @args
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

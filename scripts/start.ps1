param([string]$Python = 'python', [int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try { & $Python -m foodarena.api --port $Port; if ($LASTEXITCODE -ne 0) { throw 'Model service failed to start.' } }
finally { Pop-Location }

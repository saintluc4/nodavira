$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python build.py
if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar executável.' }

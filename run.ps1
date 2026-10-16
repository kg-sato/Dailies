$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PYTHONPATH = "$PSScriptRoot/.packages"
python -m uvicorn app:app --host 127.0.0.1 --port 8765

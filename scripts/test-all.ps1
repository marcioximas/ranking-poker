$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonDir = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312'
$nodeDir = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.18.0-win-x64'

if (Test-Path (Join-Path $pythonDir 'python.exe')) {
  $env:Path = "$pythonDir;$pythonDir\Scripts;$env:Path"
}

if (Test-Path (Join-Path $nodeDir 'node.exe')) {
  $env:Path = "$nodeDir;$env:Path"
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw 'Python nao encontrado. Instale Python 3.12 ou adicione ao PATH.'
}

if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
  throw 'Node/npx nao encontrado. Instale Node.js LTS ou adicione ao PATH.'
}

Write-Host '==> Rodando testes de backend (pytest)...'
Push-Location (Join-Path $repoRoot 'backend')
python -m pytest
$backendExitCode = $LASTEXITCODE
Pop-Location

if ($backendExitCode -ne 0) {
  Write-Host "Backend falhou com codigo $backendExitCode"
  exit $backendExitCode
}

Write-Host '==> Rodando testes de UI (Playwright)...'
Push-Location $repoRoot
npx playwright test --reporter=line --workers=1
$uiExitCode = $LASTEXITCODE
Pop-Location

if ($uiExitCode -ne 0) {
  Write-Host "UI falhou com codigo $uiExitCode"
  exit $uiExitCode
}

Write-Host '==> Tudo verde: backend + UI.'

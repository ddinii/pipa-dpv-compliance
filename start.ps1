$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Python 가상환경이 없습니다. README의 백엔드 설치 단계를 먼저 진행하세요.' }
if (-not (Test-Path (Join-Path $PSScriptRoot 'frontend\node_modules'))) { throw '프론트엔드 의존성이 없습니다. frontend 폴더에서 npm install을 먼저 실행하세요.' }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw 'npm을 찾을 수 없습니다. Node.js를 설치하세요.' }

if (-not $env:PIPA_EXTRACTOR) { $env:PIPA_EXTRACTOR = 'mock' }
if ($env:PIPA_EXTRACTOR -eq 'llm' -and -not $env:ANTHROPIC_API_KEY) { throw 'LLM 모드에는 ANTHROPIC_API_KEY 환경변수가 필요합니다.' }

Write-Host "백엔드 실행 (모드: $env:PIPA_EXTRACTOR)"
$backend = $null
$frontend = $null
try {
    $backend = Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $PSScriptRoot -PassThru -NoNewWindow
    $frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList @('run','dev','--','--host','127.0.0.1','--port','5173','--strictPort') -WorkingDirectory (Join-Path $PSScriptRoot 'frontend') -PassThru -NoNewWindow
    Write-Host '접속: http://localhost:5173  |  API: http://127.0.0.1:8000/health'
    Write-Host '종료: Ctrl+C'
    while (-not $backend.HasExited -and -not $frontend.HasExited) {
        Start-Sleep -Seconds 1
        $backend.Refresh()
        $frontend.Refresh()
    }
}
finally {
    Write-Host '서버를 종료합니다...'
    foreach ($proc in @($backend, $frontend)) {
        if ($null -ne $proc -and -not $proc.HasExited) {
            # Windows에서는 자식 프로세스까지 함께 정리
            & taskkill.exe /PID $proc.Id /T /F 2>$null | Out-Null
        }
    }
}

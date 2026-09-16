param(
    [string]$PatchFile = (Join-Path $PSScriptRoot "pipa_rule_v1_freeze.patch")
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Fail([string]$Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".git")) {
    Fail "Git 저장소 루트에서 실행하세요. 예: C:\Users\user\Documents\GitHub\pipa-dpv-compliance-main"
}

if (-not (Test-Path "app\rules\engine.py")) {
    Fail "app\rules\engine.py를 찾지 못했습니다. 프로젝트 루트가 맞는지 확인하세요."
}

if (-not (Test-Path $PatchFile)) {
    Fail "패치 파일을 찾지 못했습니다: $PatchFile"
}

$targetFiles = @(
    "README.md",
    "app/rules/engine.py",
    "docs/temporary_spec.md",
    "rules/p0_rules.json",
    "tests/test_p0_rule_engine_v2.py"
)

$dirty = $false
foreach ($file in $targetFiles) {
    git diff --quiet -- $file
    if ($LASTEXITCODE -ne 0) { $dirty = $true }

    git diff --cached --quiet -- $file
    if ($LASTEXITCODE -ne 0) { $dirty = $true }
}

if ($dirty) {
    Write-Host ""
    Write-Host "패치 대상 파일에 아직 커밋하지 않은 변경이 있습니다." -ForegroundColor Yellow
    Write-Host "먼저 아래처럼 체크포인트 커밋을 만든 뒤 다시 실행하세요:"
    Write-Host '  git add -A'
    Write-Host '  git commit -m "chore: checkpoint before P0 rule freeze patch"'
    Write-Host '  git push'
    exit 2
}

Write-Host "[1/4] 패치 적용 가능 여부 확인..."
git apply --check $PatchFile
if ($LASTEXITCODE -ne 0) {
    Fail "git apply --check 실패. 업로드 당시 프로젝트와 현재 파일이 달라졌을 수 있습니다."
}

Write-Host "[2/4] 패치 적용..."
git apply $PatchFile
if ($LASTEXITCODE -ne 0) {
    Fail "패치 적용 실패."
}

Write-Host "[3/4] whitespace/diff 검사..."
git diff --check
if ($LASTEXITCODE -ne 0) {
    Fail "git diff --check 실패. 변경 내용을 확인하세요."
}

Write-Host "[4/4] P0 Rule 테스트..."
python -m pytest -q tests\test_p0_rule_engine_v2.py
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "패치는 적용됐지만 P0 테스트가 실패했습니다." -ForegroundColor Yellow
    Write-Host "의존성 설치 후 다시 실행하세요:"
    Write-Host "  python -m pip install -r requirements.txt"
    Write-Host "  python -m pytest -q tests\test_p0_rule_engine_v2.py"
    exit 3
}

Write-Host ""
Write-Host "패치 적용 및 P0 테스트 완료." -ForegroundColor Green
Write-Host "다음 명령으로 변경을 확인하세요:"
Write-Host "  git status"
Write-Host "  git diff --stat"
Write-Host "  git diff"

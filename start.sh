#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python ]]; then
  echo "[오류] Python 가상환경이 없습니다. README의 백엔드 설치 단계를 먼저 진행하세요." >&2
  exit 1
fi
if [[ ! -d frontend/node_modules ]]; then
  echo "[오류] 프론트엔드 의존성이 없습니다. frontend 폴더에서 npm install을 먼저 실행하세요." >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "[오류] npm을 찾을 수 없습니다. Node.js를 설치하세요." >&2
  exit 1
fi

# 기본값은 무료 Mock 모드. LLM 모드는 PIPA_EXTRACTOR=llm로 명시적으로 선택.
export PIPA_EXTRACTOR="${PIPA_EXTRACTOR:-mock}"
if [[ "$PIPA_EXTRACTOR" == "llm" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "[오류] LLM 모드에는 ANTHROPIC_API_KEY 환경변수가 필요합니다." >&2
  exit 1
fi

backend_pid=''
frontend_pid=''
cleanup() {
  trap - INT TERM EXIT
  echo
  echo '서버를 종료합니다...'
  [[ -z "$backend_pid" ]] || kill "$backend_pid" 2>/dev/null || true
  [[ -z "$frontend_pid" ]] || kill "$frontend_pid" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "백엔드 실행 (모드: $PIPA_EXTRACTOR)"
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
backend_pid=$!
echo '프론트엔드 실행'
(cd frontend && npm run dev -- --host 127.0.0.1 --port 5173 --strictPort) &
frontend_pid=$!
echo '접속: http://localhost:5173  |  API: http://127.0.0.1:8000/health'
echo '종료: Ctrl+C'
# 두 프로세스 중 하나가 종료되면 나머지도 정리
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

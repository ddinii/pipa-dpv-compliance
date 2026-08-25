"""
PIPA-DPV Compliance PoC — 통합 실행 스크립트

개발 중 기능을 빠르게 확인할 때 백엔드(FastAPI)와 프론트엔드(Streamlit)를
한 번에 띄우기 위한 편의 스크립트입니다.

실행:
    python app.py

- 백엔드:   http://localhost:8000  (Swagger: /docs)
- 프론트엔드: http://localhost:8501

Ctrl+C 한 번으로 두 프로세스가 함께 종료됩니다.
개별 실행이 필요하면 README의 "빠른 시작" 절을 참고하세요
(uvicorn backend.main:app / streamlit run frontend/app.py).
"""

from __future__ import annotations

import subprocess
import sys
import time


def _stop(proc: subprocess.Popen, name: str) -> None:
    """프로세스(및 그 자식 프로세스)를 종료한다.

    uvicorn --reload는 감시용 자식 프로세스를 추가로 띄우는데, Windows의
    Popen.terminate()는 자식까지 정리하지 못해 재실행 시 포트가 점유된 채로
    남는 문제가 있어 `taskkill /T`로 프로세스 트리 전체를 종료한다.
    """
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
        )
    else:
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    print(f"[app.py] {name} 프로세스 종료 완료")


def main() -> int:
    backend_cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.main:app", "--reload", "--port", "8000",
    ]
    frontend_cmd = [
        sys.executable, "-m", "streamlit", "run", "frontend/app.py",
        "--server.port", "8501",
    ]

    print("[app.py] 백엔드 실행: " + " ".join(backend_cmd))
    backend = subprocess.Popen(backend_cmd)

    # 백엔드가 먼저 뜰 시간을 잠깐 준 뒤 프론트엔드 실행
    time.sleep(2)

    print("[app.py] 프론트엔드 실행: " + " ".join(frontend_cmd))
    frontend = subprocess.Popen(frontend_cmd)

    print("\n[app.py] 백엔드:   http://localhost:8000/docs")
    print("[app.py] 프론트엔드: http://localhost:8501")
    print("[app.py] 종료하려면 Ctrl+C\n")

    try:
        while True:
            backend_code = backend.poll()
            frontend_code = frontend.poll()
            if backend_code is not None or frontend_code is not None:
                print("[app.py] 프로세스가 예기치 않게 종료되어 전체를 정리합니다.")
                break
            time.sleep(1)
        return 1
    except KeyboardInterrupt:
        print("\n[app.py] 종료 신호를 받았습니다. 프로세스를 정리합니다...")
        return 0
    finally:
        _stop(frontend, "frontend")
        _stop(backend, "backend")


if __name__ == "__main__":
    raise SystemExit(main())

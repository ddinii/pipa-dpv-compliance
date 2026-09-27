from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.compliance import router as compliance_router
from app.api.validate import router as validation_router


app = FastAPI(
    title="PIPA-DPV Compliance Prototype",
    version="0.1.0",
    description=(
        "PIPA-DPV 기반 개인정보 처리 사실 검증 프로토타입. "
        "PASS는 현재 구현된 형식 규칙을 충족했다는 의미이며 "
        "최종적인 법률상 적법성 판단을 의미하지 않습니다."
    ),
)

# Development-only CORS: allow the local Vite dev server origins so the
# React frontend can call the JSON POST compliance API directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

app.include_router(validation_router)
app.include_router(compliance_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok"
    }
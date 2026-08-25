"""
PIPA-DPV Compliance API

3계층 아키텍처의 3층(National Privacy Compliance API)에 해당하는
데모용 FastAPI 서버입니다.

실행:
    uvicorn backend.main:app --reload --port 8000

엔드포인트:
    POST /compliance-check/text   - 처리방침 원문 텍스트를 입력받아 점검
    POST /compliance-check/pdf    - 처리방침 PDF 파일을 업로드받아 텍스트 추출 후 점검
    POST /compliance-check/facts  - 이미 구조화된 Fact를 입력받아 점검 (테스트/디버깅용)
    GET  /rules                   - 현재 적용 중인 규칙 목록 조회
    GET  /health                  - 헬스체크
"""

from __future__ import annotations
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from backend.models import PolicyFacts, ComplianceReport
from backend.rules.rule_engine import evaluate_policy, RULES
from backend.extraction.llm_extractor import get_extractor
from backend.extraction.file_parsers import extract_text_from_pdf

app = FastAPI(
    title="PIPA-DPV Compliance API",
    description="W3C DPV 기반 한국 개인정보보호법 기계판독 규칙체계 PoC",
    version="0.1.0",
)

# 팀원들이 로컬 프론트엔드(Streamlit/React 등)에서 바로 붙여볼 수 있도록 개방
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PolicyTextRequest(BaseModel):
    text: str


class ComplianceCheckResponse(BaseModel):
    facts: PolicyFacts
    report: ComplianceReport
    disclaimer: str = (
        "본 판정 결과는 참고용 자동 점검 결과이며, 법적 적법성을 확정하지 않습니다. "
        "GREEN 판정도 최종 적법성을 보장하지 않으며, RED/AMBER 항목은 반드시 "
        "전문가 검토를 거쳐야 합니다."
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/rules")
def list_rules():
    return [
        {
            "rule_id": r.rule_id,
            "rule_name": r.rule_name,
            "legal_basis": r.legal_basis,
            "field": r.field_name,
        }
        for r in RULES
    ]


def _run_text_check(text: str) -> ComplianceCheckResponse:
    if not text or len(text.strip()) < 20:
        raise HTTPException(status_code=400, detail="처리방침 텍스트가 너무 짧습니다.")

    extractor = get_extractor()
    facts = extractor.extract(text)
    report = evaluate_policy(facts)
    return ComplianceCheckResponse(facts=facts, report=report)


@app.post("/compliance-check/text", response_model=ComplianceCheckResponse)
def check_from_text(req: PolicyTextRequest):
    return _run_text_check(req.text)


@app.post("/compliance-check/pdf", response_model=ComplianceCheckResponse)
async def check_from_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다.")

    file_bytes = await file.read()
    try:
        text = extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return _run_text_check(text)


@app.post("/compliance-check/facts", response_model=ComplianceCheckResponse)
def check_from_facts(facts: PolicyFacts):
    report = evaluate_policy(facts)
    return ComplianceCheckResponse(facts=facts, report=report)

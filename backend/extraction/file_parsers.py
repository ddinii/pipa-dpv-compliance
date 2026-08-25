"""
파일 업로드(PDF 등)에서 처리방침 원문 텍스트를 뽑아내는 계층.

여기서 뽑은 텍스트는 backend/extraction/llm_extractor.py 의 입력으로
그대로 흘러들어가며, 그 이후 파이프라인(Fact 추출 -> Rule Engine)은
텍스트로 직접 입력했을 때와 동일합니다.
"""

from __future__ import annotations

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """PDF 바이트에서 텍스트를 추출한다.

    텍스트 레이어가 없는 스캔 이미지 PDF나 손상된 파일은 ValueError로
    감싸서 호출자(API 레이어)가 사용자에게 명확한 안내를 줄 수 있게 한다.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except (PdfReadError, ValueError) as e:
        raise ValueError(f"PDF 파일을 읽을 수 없습니다 (손상되었거나 지원하지 않는 형식): {e}") from e

    if not text.strip():
        raise ValueError(
            "PDF에서 텍스트를 추출하지 못했습니다. 스캔 이미지로만 된 PDF는 "
            "아직 지원하지 않습니다 — 텍스트를 직접 입력해주세요."
        )
    return text

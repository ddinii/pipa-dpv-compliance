"""Poc1Extractor Protocol을 구현하는 실제 LLM 추출기.

`MockPoC1Extractor`를 대체하는 자리다 (docs/context/backend/LLM_EXTRACTOR_HANDOFF.md
6장). Protocol 시그니처와 정본 Fact 계약만 지키면 `app/services/compliance.py`,
`OntologyMapper`, `P0RuleEngine`, 프론트엔드 어느 쪽도 바뀌지 않는다.

추출 로직 자체는 `app/extractors/poc1.py`의 2-pass 구현에 있다. 이 모듈은
호출 규약을 맞추고 진단 정보를 밖으로 빼는 얇은 어댑터다.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from app.extractors.poc1 import DEFAULT_MODEL, ExtractionResult, MessagesClient, PoC1Extractor

ENV_API_KEY = "ANTHROPIC_API_KEY"


class LlmPoC1Extractor:
    """처리방침 원문에서 F1-01~F1-12 Fact를 추출한다.

    Protocol이 요구하는 `analysis_id` / `controller_id` / `controller_name`은
    추출에 쓰지 않는다. 인스턴스 URI는 `OntologyMapper`가 이 값들을 받아 만들고,
    Extractor는 Fact만 낸다 (handoff 1장의 경계).

    `on_result`는 추출 결과 전체를 받는 선택적 훅이다. 거부된 Fact의 사유 분포를
    보려면 여기서 꺼낸다. 기본값이 None이라 원문이 어디에도 새지 않는다
    (handoff 7장: 원문을 불필요하게 로깅하지 않는다).
    """

    def __init__(
        self,
        messages: MessagesClient,
        *,
        model: str = DEFAULT_MODEL,
        cache_document: bool = True,
        on_result: Callable[[ExtractionResult], None] | None = None,
    ) -> None:
        self._extractor = PoC1Extractor(
            messages, model=model, cache_document=cache_document
        )
        self._on_result = on_result

    @classmethod
    def from_environment(
        cls,
        *,
        model: str = DEFAULT_MODEL,
        cache_document: bool = True,
        on_result: Callable[[ExtractionResult], None] | None = None,
    ) -> "LlmPoC1Extractor":
        """환경변수의 자격증명으로 Anthropic 클라이언트를 만든다.

        키를 인자로 받지 않는다. SDK가 ANTHROPIC_API_KEY를 직접 읽으므로 이
        코드가 키 값을 보지 않는다 (handoff 7장).
        """
        if not os.environ.get(ENV_API_KEY):
            raise RuntimeError(
                f"{ENV_API_KEY} 환경변수가 없습니다. 키를 소스나 인자로 넘기지 마십시오."
            )
        import anthropic  # 지연 import: SDK 없이도 이 모듈을 불러올 수 있어야 한다

        return cls(
            anthropic.Anthropic().messages,
            model=model,
            cache_document=cache_document,
            on_result=on_result,
        )

    def extract(
        self,
        *,
        analysis_id: str,
        controller_id: str,
        controller_name: str | None,
        policy_text: str,
    ) -> list[dict[str, Any]]:
        result = self._extractor.extract(policy_text)
        if self._on_result is not None:
            self._on_result(result)
        return result.facts

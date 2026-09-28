"""기본 Extractor 선택.

handoff 6장은 Mock 자리에 실제 Extractor를 꽂는 것을 연동의 마지막 단계로 둔다.
다만 실제 Extractor는 호출마다 과금되므로, 무엇이 기본값인지는 배포 환경이
정해야 한다. 그래서 코드가 아니라 환경변수가 고른다.

    PIPA_EXTRACTOR=mock   기본값. 고정 합성 시나리오. 과금 없음
    PIPA_EXTRACTOR=llm    실제 LLM. ANTHROPIC_API_KEY가 있어야 한다

`llm`인데 키가 없으면 import 시점이 아니라 **첫 요청 시점에** 실패한다.
서버가 키 없이도 뜨고, PoC3와 나머지 endpoint는 계속 동작해야 하기 때문이다.
"""

from __future__ import annotations

import os
from typing import Any

from app.extractors.base import Poc1Extractor, Poc2Extractor
from app.extractors.poc1_mock_extractor import MockPoC1Extractor
from app.extractors.poc2_mock_extractor import MockPoc2Extractor

ENV_EXTRACTOR = "PIPA_EXTRACTOR"
ENV_MODEL = "PIPA_EXTRACTOR_MODEL"

MOCK = "mock"
LLM = "llm"
MODES = (MOCK, LLM)


def selected_mode() -> str:
    """환경변수가 고른 모드. 모르는 값이면 즉시 실패한다 (COM-002 임의 보완 금지)."""
    mode = (os.environ.get(ENV_EXTRACTOR) or MOCK).strip().lower()
    if mode not in MODES:
        raise ValueError(
            f"{ENV_EXTRACTOR}는 {list(MODES)} 중 하나여야 합니다. 받은 값: {mode!r}"
        )
    return mode


def _model_kwargs() -> dict[str, Any]:
    model = os.environ.get(ENV_MODEL)
    return {"model": model} if model else {}


class _LazyExtractor:
    """첫 호출에서 실제 Extractor를 만든다.

    모듈 import 시점에 만들면 키 없는 환경에서 서버가 아예 뜨지 않는다.
    PoC3와 다른 endpoint는 키와 무관하므로 그 지점까지 실패를 미룬다.
    """

    def __init__(self, factory) -> None:
        self._factory = factory
        self._delegate: Any = None

    def extract(self, **kwargs) -> Any:
        if self._delegate is None:
            self._delegate = self._factory()
        return self._delegate.extract(**kwargs)


def default_poc1_extractor() -> Poc1Extractor:
    if selected_mode() == MOCK:
        return MockPoC1Extractor()

    def build():
        from app.extractors.poc1_llm_extractor import LlmPoC1Extractor

        return LlmPoC1Extractor.from_environment(**_model_kwargs())

    return _LazyExtractor(build)


def default_poc2_extractor() -> Poc2Extractor:
    if selected_mode() == MOCK:
        return MockPoc2Extractor()

    def build():
        from app.extractors.poc2_llm_extractor import LlmPoc2Extractor

        return LlmPoc2Extractor.from_environment(**_model_kwargs())

    return _LazyExtractor(build)

"""기본 Extractor 선택 (handoff 6장 Mock -> 실제 교체 지점).

실제 Extractor는 호출마다 과금되므로 무엇이 기본값인지는 배포 환경이 정한다.
그 선택이 조용히 뒤집히면 둘 중 하나가 일어난다 — 데모가 Mock 결과를 실제처럼
보여주거나, 아무도 의도하지 않은 과금이 시작된다.
"""

import pytest

from app.extractors.poc1_mock_extractor import MockPoC1Extractor
from app.extractors.poc2_mock_extractor import MockPoc2Extractor
from app.extractors.selection import (
    ENV_EXTRACTOR,
    ENV_MODEL,
    LLM,
    MOCK,
    default_poc1_extractor,
    default_poc2_extractor,
    selected_mode,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_EXTRACTOR, raising=False)
    monkeypatch.delenv(ENV_MODEL, raising=False)


# --- 기본값 --------------------------------------------------------------


def test_default_is_mock_so_the_server_costs_nothing_to_start():
    assert selected_mode() == MOCK
    assert isinstance(default_poc1_extractor(), MockPoC1Extractor)
    assert isinstance(default_poc2_extractor(), MockPoc2Extractor)


@pytest.mark.parametrize("value", ["MOCK", " mock ", "Mock"])
def test_mode_is_case_and_space_insensitive(monkeypatch, value: str):
    monkeypatch.setenv(ENV_EXTRACTOR, value)
    assert selected_mode() == MOCK


def test_unknown_mode_fails_instead_of_falling_back(monkeypatch):
    """COM-002 임의 보완 금지. 오타를 조용히 mock으로 처리하면 안 된다."""
    monkeypatch.setenv(ENV_EXTRACTOR, "real")
    with pytest.raises(ValueError, match=ENV_EXTRACTOR):
        selected_mode()


# --- llm 모드 ------------------------------------------------------------


def test_llm_mode_does_not_need_a_key_to_construct(monkeypatch):
    """서버가 키 없이도 떠야 한다. PoC3와 다른 endpoint는 키와 무관하다."""
    monkeypatch.setenv(ENV_EXTRACTOR, LLM)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    default_poc1_extractor()  # 예외가 나면 안 된다
    default_poc2_extractor()


def test_llm_mode_fails_on_the_first_request_when_the_key_is_missing(monkeypatch):
    """실패를 미루되 삼키지는 않는다. 첫 호출에서 분명히 드러나야 한다."""
    monkeypatch.setenv(ENV_EXTRACTOR, LLM)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    extractor = default_poc1_extractor()
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        extractor.extract(
            analysis_id="x", controller_id="c", controller_name=None, policy_text="문서"
        )


def test_llm_mode_builds_the_real_extractor_when_a_key_is_present(monkeypatch):
    monkeypatch.setenv(ENV_EXTRACTOR, LLM)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-a-real-key")
    from app.extractors.poc1_llm_extractor import LlmPoC1Extractor

    built = {}

    def fake_from_environment(**kwargs):
        built.update(kwargs)
        return object()

    monkeypatch.setattr(LlmPoC1Extractor, "from_environment", fake_from_environment)
    extractor = default_poc1_extractor()
    try:
        extractor.extract(analysis_id="x", controller_id="c",
                          controller_name=None, policy_text="문서")
    except AttributeError:
        pass  # 더미 객체에는 extract가 없다. 생성이 일어났는지만 본다
    assert built == {}, "모델을 지정하지 않으면 기본 모델을 쓴다"


def test_model_override_is_passed_through(monkeypatch):
    monkeypatch.setenv(ENV_EXTRACTOR, LLM)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-a-real-key")
    monkeypatch.setenv(ENV_MODEL, "claude-sonnet-5")
    from app.extractors.poc2_llm_extractor import LlmPoc2Extractor

    built = {}

    def fake_from_environment(**kwargs):
        built.update(kwargs)
        return object()

    monkeypatch.setattr(LlmPoc2Extractor, "from_environment", fake_from_environment)
    extractor = default_poc2_extractor()
    try:
        extractor.extract(analysis_id="x", controller_id="c", controller_name=None,
                          incident={"record": "기록"}, notification=None)
    except AttributeError:
        pass
    assert built == {"model": "claude-sonnet-5"}


# --- 서비스 경계 ---------------------------------------------------------


def test_service_still_accepts_an_injected_extractor():
    """환경변수와 무관하게 주입이 이긴다. 평가 하네스와 테스트가 이것에 의존한다."""
    from app.services.compliance import run_policy_check

    results = run_policy_check(
        {
            "analysis_id": "SEL-001",
            "controller": {"controller_id": "ctrl-001", "name": "테스트"},
            "policy_text": "합성 테스트 문서입니다.",
        },
        extractor=MockPoC1Extractor(),
    )
    assert {item.rule_id for item in results} == {
        "P1-R01", "P1-R02", "P1-R03", "P1-R04", "P1-R06", "P1-R07", "P1-R08",
        "P1-R09", "P1-R10", "P1-R11", "P1-R12",
    }

"""PoC1 처리방침 Fact Extractor (P01-002 / P01-003 / P01-004).

LLM은 Fact의 값과 근거 문장만 만든다. offset은 이 모듈이 원문에서 직접 찾는다.
원문에서 찾지 못한 인용은 환각으로 보고 그 Fact를 버린다 (NFR-07).

Rule 판정은 하지 않는다. 산출물은 Fact Envelope 목록이며, 검증(COM-002)과
Ontology Mapping(COM-004)은 app.facts가 맡는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.extractors.prompts import (
    PASS1_SYSTEM,
    PASS2_SYSTEM,
    RIGHTS_SYSTEM,
    pass1_user_message,
    pass2_user_message,
)
from app.facts.models import FACT_SCHEMA_VERSION

DEFAULT_MODEL = "claude-opus-5"
MAX_TOKENS = 16000

# --- LLM 응답 스키마 (structured outputs) --------------------------------


class IdentifiedActivity(BaseModel):
    activity_id: str = Field(description="act-collection-001 형식의 처리행위 ID")
    ontology_class: str = Field(description="CollectionAndUse 등 Ontology Class 이름")
    heading: str = Field(description="원문에서 이 처리행위를 특정하는 짧은 인용구")


class ActivityList(BaseModel):
    activities: list[IdentifiedActivity]


class ExtractedFact(BaseModel):
    fact_id: str = Field(description="F1-02 등 Fact Dictionary ID")
    activity_id: str | None = Field(description="처리행위 ID. 권리 Fact는 null")
    ontology_property: str | None
    value: Any | None
    value_state: str = Field(description="confirmed | unknown | absent")
    evidence_text: list[str] = Field(description="원문 그대로의 인용. 배열 값은 원소별로 제공")


class FactList(BaseModel):
    facts: list[ExtractedFact]


# --- 결과 ---------------------------------------------------------------


@dataclass
class RejectedFact:
    fact_id: str
    activity_id: str | None
    reason: str
    quote: str | None = None


@dataclass
class ExtractionResult:
    facts: list[dict] = field(default_factory=list)
    activities: list[IdentifiedActivity] = field(default_factory=list)
    rejected: list[RejectedFact] = field(default_factory=list)

    @property
    def hallucination_rate(self) -> float:
        """근거를 원문에서 찾지 못해 버려진 Fact의 비율."""
        total = len(self.facts) + len(self.rejected)
        return len(self.rejected) / total if total else 0.0


class MessagesClient(Protocol):
    """anthropic.Anthropic().messages가 만족하는 최소 인터페이스.

    테스트에서 스텁을 끼울 수 있도록 Protocol로 둔다.
    """

    def parse(self, **kwargs) -> Any: ...


# --- Extractor ----------------------------------------------------------


class PoC1Extractor:
    def __init__(
        self,
        messages: MessagesClient,
        *,
        model: str = DEFAULT_MODEL,
        cache_document: bool = True,
    ) -> None:
        self.messages = messages
        self.model = model
        self.cache_document = cache_document

    # -- LLM 호출 --------------------------------------------------------

    def _system_blocks(self, instructions: str, document: str) -> list[dict]:
        """system 프롬프트를 지침 + 원문으로 구성한다.

        Pass 2는 처리행위 수만큼 호출되는데 원문은 매번 같다. 원문 블록에
        cache_control을 걸어 두면 두 번째 호출부터 캐시에서 읽는다.
        지침을 먼저, 원문을 나중에 두어야 캐시 prefix가 안정적이다.
        """
        blocks: list[dict] = [{"type": "text", "text": instructions}]
        document_block: dict = {
            "type": "text",
            "text": f"<처리방침>\n{document}\n</처리방침>",
        }
        if self.cache_document:
            document_block["cache_control"] = {"type": "ephemeral"}
        blocks.append(document_block)
        return blocks

    def _parse(self, system: list[dict], user: str, output_format: type[BaseModel]):
        response = self.messages.parse(
            model=self.model,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=output_format,
        )
        if getattr(response, "stop_reason", None) == "refusal":
            raise RuntimeError(f"모델이 요청을 거부했습니다: {response.stop_details}")
        return response.parsed_output

    # -- Pass 1 ----------------------------------------------------------

    def identify_activities(self, document: str) -> ActivityList:
        return self._parse(
            [{"type": "text", "text": PASS1_SYSTEM}],
            pass1_user_message(document),
            ActivityList,
        )

    # -- Pass 2 ----------------------------------------------------------

    def extract_activity_facts(
        self, document: str, activity: IdentifiedActivity
    ) -> list[ExtractedFact]:
        parsed: FactList = self._parse(
            self._system_blocks(PASS2_SYSTEM, document),
            pass2_user_message(activity.activity_id, activity.ontology_class, activity.heading),
            FactList,
        )
        return parsed.facts

    def extract_rights_facts(self, document: str) -> list[ExtractedFact]:
        parsed: FactList = self._parse(
            self._system_blocks(RIGHTS_SYSTEM, document),
            "이 처리방침의 정보주체 권리와 행사절차를 추출하십시오.",
            FactList,
        )
        return parsed.facts

    # -- 전체 ------------------------------------------------------------

    def extract(self, document: str) -> ExtractionResult:
        result = ExtractionResult()
        pass1 = self.identify_activities(document)
        result.activities = pass1.activities

        for activity in result.activities:
            # Pass 1의 heading도 원문 인용이어야 한다. 아니면 그 처리행위를 신뢰할 수 없다.
            if activity.heading not in document:
                result.rejected.append(RejectedFact(
                    fact_id="F1-01",
                    activity_id=activity.activity_id,
                    reason="Pass 1이 반환한 heading이 원문에 없습니다.",
                    quote=activity.heading,
                ))
                continue

            for raw in self.extract_activity_facts(document, activity):
                self._collect(result, raw, document, expected_activity=activity)

        for raw in self.extract_rights_facts(document):
            self._collect(result, raw, document, expected_activity=None)

        return result

    # -- 후처리 ----------------------------------------------------------

    def _collect(
        self,
        result: ExtractionResult,
        raw: ExtractedFact,
        document: str,
        expected_activity: IdentifiedActivity | None,
    ) -> None:
        activity_id = expected_activity.activity_id if expected_activity else None

        # COM-003: 모델이 다른 처리행위의 ID를 붙여 보내면 버린다.
        if expected_activity is not None and raw.activity_id != activity_id:
            result.rejected.append(RejectedFact(
                raw.fact_id,
                raw.activity_id,
                f"요청한 처리행위({activity_id})가 아닌 activity_id를 반환했습니다.",
            ))
            return

        if raw.value_state not in {"confirmed", "unknown", "absent"}:
            result.rejected.append(RejectedFact(
                raw.fact_id, raw.activity_id, f"알 수 없는 value_state: {raw.value_state!r}"
            ))
            return

        if not raw.evidence_text:
            result.rejected.append(RejectedFact(
                raw.fact_id, raw.activity_id, "근거 인용이 없습니다."
            ))
            return

        evidence, missing = locate_quotes(document, raw.evidence_text)
        if missing is not None:
            # NFR-07: 원문에 없는 문장을 인용했다면 그 Fact 전체를 신뢰할 수 없다.
            result.rejected.append(RejectedFact(
                raw.fact_id,
                raw.activity_id,
                "근거 인용을 원문에서 찾지 못했습니다.",
                quote=missing,
            ))
            return

        subject_id, ontology_class = self._subject_for(raw, expected_activity)

        result.facts.append({
            "fact_id": self._unique_fact_id(result, raw.fact_id, subject_id),
            "subject_id": subject_id,
            "activity_id": raw.activity_id,
            "ontology_class": ontology_class,
            "ontology_property": raw.ontology_property,
            "value": raw.value if raw.value_state == "confirmed" else None,
            "value_state": raw.value_state,
            "source_type": "policy_text",
            "evidence": evidence,
            "schema_version": FACT_SCHEMA_VERSION,
        })

    @staticmethod
    def _unique_fact_id(result: ExtractionResult, fact_type: str, subject_id: str) -> str:
        """같은 subject에 같은 유형 Fact가 여러 개 나와도 fact_id가 겹치지 않게 한다.

        P1-R07이 대표적이다. 엔진은 모든 DataSubjectRight에 행사절차를 요구하므로
        F1-12는 권리 수만큼 나오는데, 셋 다 subject가 정보주체 하나다. 접미사가
        없으면 정본 검증이 "중복 fact_id"로 전부 거부한다.

        번호는 추출 순서에서 결정론적으로 정해진다 (NFR-03).
        """
        base = f"{fact_type}:{subject_id}"
        seen = sum(
            1 for item in result.facts
            if item["fact_id"] == base or item["fact_id"].startswith(f"{base}#")
        )
        return base if seen == 0 else f"{base}#{seen + 1}"

    @staticmethod
    def _subject_for(
        raw: ExtractedFact, activity: IdentifiedActivity | None
    ) -> tuple[str, str]:
        """Fact의 subject와 그 Class를 정한다.

        Fact Dictionary 3장의 Ontology Mapping은 화살표로 경로를 적지만, Fact의
        subject는 그 경로의 **출발 Class**다. F1-09
        (EntrustedProcessing.hasProcessor -> EntrustedProcessor.hasName)의 subject는
        처리행위이고, 수탁자 개체는 매퍼가 만든다. 정본 레지스트리의 subject_class가
        이 규약을 고정한다 (app/mapping/mapping_registry.py).
        """
        if activity is None:
            # 3장: F1-11은 DataSubject.hasRight, F1-12는
            # DataSubjectRight.hasExerciseProcedure다. subject Class가 다르다.
            if raw.fact_id == "F1-12":
                return "subj-001", "DataSubjectRight"
            return "subj-001", "DataSubject"
        if raw.fact_id in {"F1-03", "F1-04"}:
            # 보유 Fact는 상위 클래스로 단언한다 (3장 PersonalInformationProcessing)
            return activity.activity_id, "PersonalInformationProcessing"
        return activity.activity_id, activity.ontology_class


def locate_quotes(
    document: str, quotes: list[str]
) -> tuple[list[dict], str | None]:
    """인용문들의 원문 offset을 찾는다.

    같은 문자열이 여러 번 나오면 앞에서부터 순서대로 배정해, 배열 값의 원소별 근거가
    서로 다른 위치를 가리키게 한다. 하나라도 못 찾으면 (빈 목록, 못 찾은 인용)을 돌려준다.
    """
    evidence: list[dict] = []
    cursor: dict[str, int] = {}

    for quote in quotes:
        start = document.find(quote, cursor.get(quote, 0))
        if start == -1:
            # 앞선 원소가 이미 소비했을 수 있으니 문서 처음부터 한 번 더 본다.
            start = document.find(quote)
            if start == -1:
                return [], quote
        cursor[quote] = start + 1
        evidence.append({
            "text": quote,
            "start_offset": start,
            "end_offset": start + len(quote),
        })

    return evidence, None

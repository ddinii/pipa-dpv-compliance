"""PoC1 처리방침 Fact Extractor (P01-002 / P01-003 / P01-004).

LLM은 Fact의 값과 근거 문장만 만든다. offset은 이 모듈이 원문에서 직접 찾는다.
원문에서 찾지 못한 인용은 환각으로 보고 그 Fact를 버린다 (NFR-07).

Rule 판정은 하지 않는다. 산출물은 Fact Envelope 목록이며, 검증(COM-002)과
Ontology Mapping(COM-004)은 app.facts가 맡는다.
"""

from __future__ import annotations

import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from app.extractors.prompts import (
    PASS1_SYSTEM,
    PASS2_SYSTEM,
    RIGHTS_SYSTEM,
    pass1_user_message,
    pass2_user_message,
)
from app.extractors.usage import Usage
from app.facts.models import FACT_SCHEMA_VERSION
from app.mapping.presence_metadata import activity_presence_metadata

DEFAULT_MODEL = "claude-sonnet-5"
MAX_TOKENS = 16000

# --- LLM 응답 스키마 (structured outputs) --------------------------------


class IdentifiedActivity(BaseModel):
    activity_id: str = Field(description="act-collection-001 형식의 처리행위 ID")
    ontology_class: str = Field(description="CollectionAndUse 등 Ontology Class 이름")
    heading: str = Field(description="원문에서 이 처리행위를 특정하는 짧은 인용구")


# activity presence metadata를 받는 PoC1 유형 (app/mapping/presence_metadata.py).
# P1-R03, P1-R06, P1-R09(v1.1)만 "처리행위가 없음"을 N/A로 본다.
PresenceType = Literal["ThirdPartyProvision", "EntrustedProcessing", "CrossBorderTransfer"]


class DeclaredAbsence(BaseModel):
    activity_type: PresenceType = Field(description="하지 않는다고 명시된 처리행위 유형")
    quote: str = Field(description="그 유형을 하지 않는다고 말한 원문 문장 그대로")


class ActivityList(BaseModel):
    activities: list[IdentifiedActivity]
    declared_absent: list[DeclaredAbsence] = Field(
        default_factory=list,
        description="원문이 '하지 않는다'고 명시한 처리행위 유형. 언급이 없으면 비워 둔다",
    )


class RightProcedure(BaseModel):
    right: str = Field(description="F1-11에 담은 권리 문구")
    procedure: str = Field(description="그 권리의 행사절차")


class OfficerIdentity(BaseModel):
    # 두 필드 모두 필수(null 허용)다. 선택 필드로 두면 RightProcedure 값도 이 모델로
    # 검증을 통과해 버려 union에서 둘을 가를 수 없다.
    name: str | None = Field(description="보호책임자 성명. 적히지 않았으면 null")
    department: str | None = Field(description="보호책임자 부서 명칭. 적히지 않았으면 null")


# structured outputs는 타입 없는 필드(Any)를 받지 않는다. 3장의 값 타입만 나열한다.
Poc1Value = str | list[str] | RightProcedure | OfficerIdentity | None


# structured outputs의 enum으로 묶는다. 자유 문자열이면 모델이 "F1-12-1"처럼 번호를
# 붙여 내고, 그러면 F1-12로 인식되지 않아 잘못된 subject class가 붙고 매퍼가 문서
# 전체의 Fact를 거부한다 (실측: held-out h1에서 6개 Rule 결과가 통째로 사라짐).
Poc1FactId = Literal[
    "F1-01", "F1-02", "F1-03", "F1-04", "F1-05", "F1-06",
    "F1-07", "F1-08", "F1-09", "F1-10", "F1-11", "F1-12",
    # v1.1 국외 이전 기재 / 개인정보 보호책임자 기재
    "F1-13", "F1-14", "F1-15", "F1-16", "F1-17", "F1-18", "F1-19",
    "F1-20", "F1-21", "F1-22", "F1-23", "F1-24", "F1-25",
]

# 처리행위가 아니라 문서에 귀속되는 Fact의 subject (정본 레지스트리의 subject_class와 같다)
_DOCUMENT_SUBJECTS = {
    "F1-11": ("subj-001", "DataSubject"),
    "F1-12": ("subj-001", "DataSubjectRight"),
    "F1-20": ("privacy-officer", "PersonalInformationController"),
    "F1-21": ("privacy-officer", "PrivacyOfficer"),
    "F1-23": ("automatic-collection", "PersonalInformationController"),
    "F1-24": ("automatic-collection", "PersonalInformationController"),
    "F1-25": ("automatic-collection", "PersonalInformationController"),
}


class ExtractedFact(BaseModel):
    fact_id: Poc1FactId = Field(description="Fact Dictionary ID. 번호를 덧붙이지 않는다")
    activity_id: str | None = Field(description="처리행위 ID. 권리 Fact는 null")
    ontology_property: str | None
    value: Poc1Value
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
    usage: Usage = field(default_factory=Usage)
    # activity presence metadata. Fact가 아니다 (Fact Dictionary 35개에 더하지 않는다).
    system_metadata: list[dict] = field(default_factory=list)

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
        max_concurrency: int = 1,
    ) -> None:
        self.messages = messages
        self.model = model
        self.cache_document = cache_document
        # Pass 2(처리행위별)와 권리 pass를 동시에 보낼 수. 1이면 순서대로 부른다.
        # 기본값이 1인 이유: 호출 순서대로 응답을 돌려주는 테스트 스텁이 그대로 동작한다.
        self.max_concurrency = max(1, max_concurrency)
        # 호출 하나하나의 usage를 여기에 쌓고 extract()가 결과에 실어 보낸다.
        self.usage = Usage()
        self._usage_lock = threading.Lock()

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
        with self._usage_lock:  # 동시 호출에서 합계가 어긋나지 않게
            self.usage.record(response)
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
            "이 처리방침의 정보주체 권리와 행사절차, 개인정보 보호책임자를 추출하십시오.",
            FactList,
        )
        return parsed.facts

    # -- 전체 ------------------------------------------------------------

    def extract(self, document: str) -> ExtractionResult:
        result = ExtractionResult()
        self.usage = Usage()  # 호출마다 새로 센다
        pass1 = self.identify_activities(document)
        result.activities = pass1.activities

        grounded: list[IdentifiedActivity] = []
        for activity in result.activities:
            # Pass 1의 heading도 원문에 근거해야 한다. 아니면 그 처리행위를 신뢰할 수 없다.
            if not heading_is_grounded(document, activity.heading):
                result.rejected.append(RejectedFact(
                    fact_id="F1-01",
                    activity_id=activity.activity_id,
                    reason="Pass 1이 반환한 heading이 원문에 없습니다.",
                    quote=activity.heading,
                ))
                continue
            grounded.append(activity)

        *per_activity, rights = self._run_after_pass1(document, grounded)
        # 응답이 도착한 순서가 아니라 처리행위 순서대로 모은다. fact_id 채번이 결정적이다.
        for activity, raw_facts in zip(grounded, per_activity):
            for raw in raw_facts:
                self._collect(result, raw, document, expected_activity=activity)

        for raw in rights:
            self._collect(result, raw, document, expected_activity=None)

        result.system_metadata = self._declared_absences(result, pass1, document)
        result.usage = self.usage
        return result

    def _run_after_pass1(
        self, document: str, activities: list[IdentifiedActivity]
    ) -> list[list[ExtractedFact]]:
        """처리행위별 Pass 2와 권리 pass를 부른다. 결과는 [처리행위..., 권리] 순서다.

        이 호출들은 서로 독립이라 동시에 보낼 수 있다. 순서대로 부르면 PoC1 문서
        하나에 약 14회 호출이 줄지어 90초 가까이 걸렸다 (실측 88초).

        첫 Pass 2는 혼자 먼저 보낸다. Pass 2들은 원문 캐시를 공유하는데, 캐시는 첫
        응답이 만들어진 뒤에야 읽힌다. 전부 동시에 보내면 모든 호출이 캐시 쓰기
        (입력 단가의 1.25배)가 되어 캐시 읽기(0.1배)를 잃는다.
        """
        jobs = [partial(self.extract_activity_facts, document, a) for a in activities]
        jobs.append(partial(self.extract_rights_facts, document))
        if self.max_concurrency == 1:
            return [job() for job in jobs]

        warmed: list[list[ExtractedFact]] = []
        if activities and self.cache_document:
            warmed.append(jobs.pop(0)())
        with ThreadPoolExecutor(max_workers=self.max_concurrency) as pool:
            return warmed + list(pool.map(lambda job: job(), jobs))

    @staticmethod
    def _declared_absences(
        result: ExtractionResult, pass1: ActivityList, document: str
    ) -> list[dict]:
        """원문이 '하지 않는다'고 명시한 처리행위 유형을 presence metadata로 바꾼다.

        확신이 없으면 내지 않는다. confirmed_false는 조건부 Rule을 N/A로 만들어
        판정 대상에서 빼므로, 잘못 내면 문제가 있는 처리행위를 가리게 된다.
          - 인용이 원문에 없으면 버린다 (NFR-07)
          - 같은 유형의 처리행위를 Pass 1이 함께 식별했으면 모순이므로 버린다.
            그 처리행위는 평소대로 평가된다
        """
        present = {activity.ontology_class for activity in pass1.activities}
        metadata: list[dict] = []
        seen: set[str] = set()
        for item in pass1.declared_absent:
            label = f"presence:{item.activity_type}"
            if item.activity_type in seen:
                continue
            if item.activity_type in present:
                result.rejected.append(RejectedFact(
                    label, None,
                    "부재를 명시했다면서 같은 유형의 처리행위도 식별했습니다. 부재 선언을 버립니다.",
                    quote=item.quote,
                ))
                continue
            evidence, missing = locate_quotes(document, [item.quote])
            if missing is not None:
                result.rejected.append(RejectedFact(
                    label, None, "부재 선언의 인용을 원문에서 찾지 못했습니다.", quote=missing,
                ))
                continue
            metadata.append(activity_presence_metadata(
                item.activity_type, "confirmed_false",
                source_type="policy_text", evidence=evidence,
            ))
            seen.add(item.activity_type)
        return metadata

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
            "value": raw.model_dump()["value"] if raw.value_state == "confirmed" else None,
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
            # v1.1 F1-20/F1-21도 문서 단위다 (보호책임자 개체는 매퍼가 만든다).
            return _DOCUMENT_SUBJECTS.get(raw.fact_id, _DOCUMENT_SUBJECTS["F1-11"])
        if raw.fact_id in {"F1-03", "F1-04"}:
            # 보유 Fact는 상위 클래스로 단언한다 (3장 PersonalInformationProcessing)
            return activity.activity_id, "PersonalInformationProcessing"
        if raw.fact_id == "F1-17":
            # 이전받는 자의 연락처. subject는 그 처리행위의 이전받는 자 개체다
            return activity.activity_id, "OverseasRecipient"
        return activity.activity_id, activity.ontology_class


# Pass 1이 여러 줄을 한 heading으로 이어 붙일 때 쓰는 구분자
_HEADING_SEPARATORS = re.compile(r"\s*(?:\n|, | - | / | \| )\s*")


def _collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def heading_is_grounded(document: str, heading: str) -> bool:
    """Pass 1 heading이 원문에 근거하는지 본다.

    heading은 Pass 2에 주는 위치 단서일 뿐 Fact의 근거가 아니다. Pass 2의 Fact는 각자
    원문 그대로 인용해야 살아남는다. 그래서 공백 차이와, 서로 다른 줄을 구분자로 이어
    붙인 경우("수탁자: A, 위탁업무: B")는 허용한다. 조각마다 원문에 있어야 한다.

    이것을 엄격하게 두면 안 되는 이유: heading 하나가 어긋나면 처리행위 전체가 빠지고,
    문제 있는 처리행위가 빠지면 판정은 GREEN 쪽으로만 움직인다 (실측: v4에서
    '추후 선정 예정' 수탁자가 빠져 P1-R06이 YELLOW -> GREEN).
    """
    if heading in document:
        return True
    collapsed = _collapse_whitespace(document)
    parts = [part for part in _HEADING_SEPARATORS.split(heading.strip()) if part.strip()]
    return bool(parts) and all(_collapse_whitespace(part) in collapsed for part in parts)


def locate_quotes(
    document: str, quotes: list[str]
) -> tuple[list[dict], str | None]:
    """인용문들의 원문 offset을 찾는다.

    같은 문자열이 여러 번 나오면 앞에서부터 순서대로 배정해, 배열 값의 원소별 근거가
    서로 다른 위치를 가리키게 한다. 하나라도 못 찾으면 (빈 목록, 못 찾은 인용)을 돌려준다.

    공백만 다른 인용도 찾는다. 원문에서 줄이 바뀐 문장을 모델이 한 줄로 이어 인용하는
    일이 실제로 있었다 (PoC2 v1: F2-01 거부 -> P2-R08 YELLOW). 이때 근거의 text에는
    **모델의 인용이 아니라 원문의 해당 구간**을 담으므로 offset은 항상 원문을 가리키고,
    공백이 아닌 글자는 모두 일치해야 한다 (NFR-07 유지). 모델 인용에 공백이 있는
    자리에만 원문의 공백 차이를 허용한다. 공백이 없는 자리에 원문 공백을 끼워 맞추지 않는다.
    """
    evidence: list[dict] = []
    cursor: dict[str, int] = {}

    for quote in quotes:
        found = _find_quote(document, quote, cursor.get(quote, 0))
        if found is None:
            # 앞선 원소가 이미 소비했을 수 있으니 문서 처음부터 한 번 더 본다.
            found = _find_quote(document, quote, 0)
            if found is None:
                return [], quote
        start, end = found
        cursor[quote] = start + 1
        evidence.append({
            "text": document[start:end],
            "start_offset": start,
            "end_offset": end,
        })

    return evidence, None


def _find_quote(document: str, quote: str, offset: int) -> tuple[int, int] | None:
    """정확히 일치하는 곳을 먼저, 없으면 공백만 다른 곳을 찾는다."""
    start = document.find(quote, offset)
    if start != -1:
        return start, start + len(quote)
    tokens = quote.split()
    if not tokens:
        return None
    pattern = re.compile(r"\s+".join(re.escape(token) for token in tokens))
    match = pattern.search(document, offset)
    return (match.start(), match.end()) if match else None

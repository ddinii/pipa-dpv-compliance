"""PoC2 침해사고/통지문 Fact Extractor.

사고 기록과 통지문을 각각 별도 호출로 처리한다. 프롬프트 경계가 곧 사고/통지
경계가 되어 둘이 섞이는 것을 구조적으로 막는다 (기능명세서 P02-003 · TST-006 ·
Fact Dictionary 8장).

offset은 LLM에게 시키지 않는다. 인용만 받아 코드가 해당 문서에서 위치를 찾고,
찾지 못한 인용은 그 Fact를 버린다 (NFR-07).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.extractors.poc1 import (
    DEFAULT_MODEL,
    MAX_TOKENS,
    MessagesClient,
    RejectedFact,
    locate_quotes,
)
from app.extractors.prompts_poc2 import (
    INCIDENT_FACT_IDS,
    INCIDENT_SYSTEM,
    MEASURE_ROLES,
    NOTICE_FACT_IDS,
    NOTICE_SYSTEM,
    incident_user_message,
    notice_user_message,
)
from app.extractors.usage import Usage
from app.facts.models import FACT_SCHEMA_VERSION

# v1은 요청 하나가 사고 하나를 뜻한다 (EXTRACTOR_DECISIONS #4).
INCIDENT_ID = "breach-incident"
NOTICE_ID = "breach-notice"

# 날짜·시간 Fact. 매퍼가 xsd:dateTime으로 싣으므로 ISO 8601이어야 한다.
DATETIME_FACT_IDS = {"F2-05", "F2-06", "F2-07", "F2-08"}
# 원문에 시간대가 없으면 한국 표준시로 본다 (팀 결정).
KST = timezone(timedelta(hours=9))


def normalize_datetime(value: Any) -> str | None:
    """ISO 8601 날짜·시간을 초 단위 KST 표기로 맞춘다. 해석할 수 없으면 None.

    값을 추정하지 않는다. 날짜만 있으면 00:00으로, 시간대가 없으면 KST로 볼 뿐이며,
    ISO로 읽히지 않는 문자열("2026년 9월 5일")은 변환하지 않고 None을 돌려준다.
    """
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed.isoformat(timespec="seconds")


# incident / notification dict에서 본문을 찾을 키. 앞에서부터 처음 채워진 것을 쓴다.
INCIDENT_TEXT_KEYS = ("record", "description", "text", "incident_text", "summary")
NOTICE_TEXT_KEYS = ("notice_text", "text", "body", "content")

# 통지문이 아예 제공되지 않았을 때 명시적 부재로 남길 Fact
# (handoff 5장 · EXTRACTOR_DECISIONS #6). F2-10은 사고 쪽에서 나오므로 빠진다.
NOTICE_ABSENCE_SHAPE: dict[str, tuple[str, str, str | None]] = {
    "F2-03": (INCIDENT_ID, "DataBreachIncident", "hasNotificationNotice"),
    "F2-04": (NOTICE_ID, "NotificationNotice", "mentionsPersonalInformation"),
    "F2-07": (INCIDENT_ID, "DataBreachIncident", "notificationDate"),
    "F2-08": (NOTICE_ID, "NotificationNotice", None),
    "F2-09": (NOTICE_ID, "NotificationNotice", "hasIncidentCircumstances"),
}

# Fact ID -> (subject_id, ontology_class). Fact Dictionary 4장 매핑의 출발 Class다.
FACT_SUBJECT: dict[str, tuple[str, str]] = {
    "F2-01": (INCIDENT_ID, "DataBreachIncident"),
    "F2-02": (INCIDENT_ID, "DataBreachIncident"),
    "F2-03": (INCIDENT_ID, "DataBreachIncident"),
    "F2-04": (NOTICE_ID, "NotificationNotice"),
    "F2-05": (INCIDENT_ID, "DataBreachIncident"),
    "F2-06": (INCIDENT_ID, "DataBreachIncident"),
    "F2-07": (INCIDENT_ID, "DataBreachIncident"),
    "F2-08": (NOTICE_ID, "NotificationNotice"),
    "F2-09": (NOTICE_ID, "NotificationNotice"),
    "F2-10": (INCIDENT_ID, "DataBreachIncident"),
}

# F2-10만 notification_notice 계열이라 사고 쪽에서 낼 때 derived를 쓴다
# (app/mapping/fact_schema.py POC2_NOTICE_FACTS).
INCIDENT_DERIVED_FACT_IDS = {"F2-10"}


class ResponseMeasure(BaseModel):
    measure_role: str = Field(description="MEASURE_ROLES 넷 중 하나")
    text: str = Field(description="사고 기록에 적힌 조치 내용")


class NoticeRef(BaseModel):
    notice_id: str = Field(description="통지문을 식별하는 짧은 문구나 ID")


# structured outputs는 타입 없는 필드(Any)를 받지 않는다. 4장의 값 타입만 나열한다.
Poc2Value = str | list[str] | list[ResponseMeasure] | NoticeRef | None


class ExtractedPoc2Fact(BaseModel):
    fact_id: str = Field(description="F2-02 등 Fact Dictionary ID")
    ontology_property: str | None
    value: Poc2Value
    value_state: str = Field(description="confirmed | unknown | absent")
    evidence_text: list[str] = Field(description="원문 그대로의 인용. 배열 값은 원소별로 제공")


class Poc2FactList(BaseModel):
    facts: list[ExtractedPoc2Fact]


class Poc2InputError(ValueError):
    """사고 기록이나 통지문에서 읽을 본문을 찾지 못했을 때."""


@dataclass
class Poc2ExtractionResult:
    facts: list[dict] = field(default_factory=list)
    rejected: list[RejectedFact] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)

    @property
    def hallucination_rate(self) -> float:
        total = len(self.facts) + len(self.rejected)
        return len(self.rejected) / total if total else 0.0


def pick_text(payload: dict[str, Any], keys: tuple[str, ...], label: str) -> str:
    """dict에서 본문을 고른다. 없으면 지어내지 않고 실패한다."""
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise Poc2InputError(
        f"{label}에서 본문을 찾지 못했습니다. 다음 중 하나가 필요합니다: {list(keys)}"
    )


class PoC2Extractor:
    """사고 기록과 통지문에서 F2-01~F2-10 Fact를 추출한다."""

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
        self.usage = Usage()

    # -- LLM 호출 --------------------------------------------------------

    def _system_blocks(self, instructions: str, document: str, tag: str) -> list[dict]:
        blocks: list[dict] = [{"type": "text", "text": instructions}]
        document_block: dict = {"type": "text", "text": f"<{tag}>\n{document}\n</{tag}>"}
        if self.cache_document:
            document_block["cache_control"] = {"type": "ephemeral"}
        blocks.append(document_block)
        return blocks

    def _parse(self, system: list[dict], user: str) -> Poc2FactList:
        response = self.messages.parse(
            model=self.model,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=Poc2FactList,
        )
        self.usage.record(response)
        if getattr(response, "stop_reason", None) == "refusal":
            raise RuntimeError(f"모델이 요청을 거부했습니다: {response.stop_details}")
        return response.parsed_output

    # -- 각 pass ---------------------------------------------------------

    def extract_incident_facts(self, record: str) -> list[ExtractedPoc2Fact]:
        parsed = self._parse(
            self._system_blocks(INCIDENT_SYSTEM, record, "사고기록"),
            incident_user_message(record),
        )
        return parsed.facts

    def extract_notice_facts(self, notice: str) -> list[ExtractedPoc2Fact]:
        parsed = self._parse(
            self._system_blocks(NOTICE_SYSTEM, notice, "통지문"),
            notice_user_message(notice),
        )
        return parsed.facts

    # -- 전체 ------------------------------------------------------------

    def extract(
        self, incident: dict[str, Any], notification: dict[str, Any] | None
    ) -> Poc2ExtractionResult:
        result = Poc2ExtractionResult()
        self.usage = Usage()  # 호출마다 새로 센다

        record = pick_text(incident, INCIDENT_TEXT_KEYS, "incident")
        for raw in self.extract_incident_facts(record):
            self._collect(result, raw, record, allowed=INCIDENT_FACT_IDS, side="incident")

        if notification is None:
            # 통지문이 제공되지 않았다. 통지문을 지어내지 않고 명시적 부재로 남긴다
            # (EXTRACTOR_DECISIONS #6). 인용할 문서가 없으므로 source_type은 derived다.
            result.facts.extend(self._notice_absence_facts())
            result.usage = self.usage
            return result

        notice = pick_text(notification, NOTICE_TEXT_KEYS, "notification")
        for raw in self.extract_notice_facts(notice):
            self._collect(result, raw, notice, allowed=NOTICE_FACT_IDS, side="notice")

        result.usage = self.usage
        return result

    # -- 후처리 ----------------------------------------------------------

    def _collect(
        self,
        result: Poc2ExtractionResult,
        raw: ExtractedPoc2Fact,
        document: str,
        *,
        allowed: list[str],
        side: str,
    ) -> None:
        def reject(reason: str, quote: str | None = None) -> None:
            result.rejected.append(RejectedFact(raw.fact_id, None, reason, quote=quote))

        # 사고 pass가 통지문 Fact를 내거나 그 반대인 경우. 둘을 섞지 않는다.
        if raw.fact_id not in allowed:
            reject(f"{side} pass에서 낼 수 없는 Fact입니다. 허용: {allowed}")
            return

        if raw.value_state not in {"confirmed", "unknown", "absent"}:
            reject(f"알 수 없는 value_state: {raw.value_state!r}")
            return

        if not raw.evidence_text:
            reject("근거 인용이 없습니다.")
            return

        evidence, missing = locate_quotes(document, raw.evidence_text)
        if missing is not None:
            # NFR-07: 원문에 없는 문장을 인용했다면 그 Fact 전체를 신뢰할 수 없다.
            reject("근거 인용을 원문에서 찾지 못했습니다.", quote=missing)
            return

        value = raw.model_dump()["value"] if raw.value_state == "confirmed" else None
        if raw.fact_id == "F2-03" and raw.value_state == "confirmed":
            # notice_id는 매퍼가 통지문 노드 ID로 쓴다. 원문 문구를 쓰면 F2-04/F2-08이
            # 붙은 NOTICE_ID 노드와 갈라져 P2-R02/P2-R03이 빈 통지문을 보게 된다.
            # activity_id처럼 시스템이 정하는 식별자이므로 모델 값을 쓰지 않는다.
            value = {"notice_id": NOTICE_ID}
        if raw.fact_id in DATETIME_FACT_IDS and raw.value_state == "confirmed":
            normalized = normalize_datetime(value)
            if normalized is None:
                # 그대로 실으면 xsd:dateTime으로 해석되지 않는 리터럴이 그래프에 들어간다
                reject(f"ISO 8601 날짜·시간이 아닙니다: {value!r}")
                return
            value = normalized
        if raw.fact_id == "F2-10" and raw.value_state == "confirmed":
            problem = self._measure_problem(value)
            if problem is not None:
                reject(problem)
                return

        subject_id, ontology_class = FACT_SUBJECT[raw.fact_id]
        source_type = (
            "derived"
            if raw.fact_id in INCIDENT_DERIVED_FACT_IDS
            else ("incident_record" if side == "incident" else "notification_notice")
        )

        result.facts.append({
            "fact_id": self._unique_fact_id(result, raw.fact_id, subject_id),
            "subject_id": subject_id,
            # 사고/통지 Fact는 같은 사고 그룹에 묶인다 (Fact Dictionary 2장 activity_id)
            "activity_id": INCIDENT_ID,
            "ontology_class": ontology_class,
            "ontology_property": raw.ontology_property,
            "value": value,
            "value_state": raw.value_state,
            "source_type": source_type,
            "evidence": evidence,
            "schema_version": FACT_SCHEMA_VERSION,
        })

    @staticmethod
    def _measure_problem(value: Any) -> str | None:
        """F2-10의 measure_role을 4장 enum으로 제한한다."""
        if not isinstance(value, list) or not value:
            return "F2-10의 값은 비어 있지 않은 객체 배열이어야 합니다."
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, dict):
                return "F2-10의 원소는 객체여야 합니다."
            role = item.get("measure_role") or item.get("role")
            text = item.get("text") or item.get("description")
            if not role or not text:
                return "F2-10의 원소에는 measure_role과 text가 필요합니다."
            if role not in MEASURE_ROLES:
                return f"v1에 없는 measure_role입니다: {role!r}"
            if role in seen:
                return f"중복 measure_role입니다: {role!r}"
            seen.add(role)
        return None

    @staticmethod
    def _unique_fact_id(
        result: Poc2ExtractionResult, fact_type: str, subject_id: str
    ) -> str:
        """같은 subject에 같은 유형 Fact가 여러 개여도 fact_id가 겹치지 않게 한다."""
        base = f"{fact_type}:{subject_id}"
        seen = sum(
            1 for item in result.facts
            if item["fact_id"] == base or item["fact_id"].startswith(f"{base}#")
        )
        return base if seen == 0 else f"{base}#{seen + 1}"

    @staticmethod
    def _notice_absence_facts() -> list[dict]:
        facts = []
        for fact_id, (subject_id, ontology_class, prop) in NOTICE_ABSENCE_SHAPE.items():
            facts.append({
                "fact_id": f"{fact_id}:{subject_id}",
                "subject_id": subject_id,
                "activity_id": INCIDENT_ID,
                "ontology_class": ontology_class,
                "ontology_property": prop,
                "value": None,
                "value_state": "absent",
                "source_type": "derived",
                "evidence": [{"field_path": "notification"}],
                "schema_version": FACT_SCHEMA_VERSION,
            })
        return facts

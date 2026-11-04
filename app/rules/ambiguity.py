"""Field-specific concreteness checks for PoC3 design phrases.

A deliberately limited, deterministic static check: a phrase is *generic-only*
when every token belongs to a closed, per-field list of generic words.  One
token outside the list (a concrete noun, a number, a stray letter) makes the
phrase count as specific.  Substring search is never used.

This does not verify legal adequacy; it only flags phrases that state nothing
specific.  Vocabulary is centrally managed here: when adding a word, add one
phrase that must be flagged and one that must stay unflagged to
tests/test_poc3_ambiguity.py.
"""

from __future__ import annotations

import re
import unicodedata

GENERIC_ONLY = "generic_only"
PROCESSOR_UNDETERMINED = "processor_undetermined"
PROCESSOR_UNSPECIFIC = "processor_unspecific"

_COMMON = frozenset({
    "기타", "그외", "등", "관련", "각종", "다양한", "필요한", "필요", "적절한", "적정한",
    "일반", "일반적인", "여러", "모든", "해당", "각", "위해", "위한", "대한",
})

# Per-field closed lists.  Words that name a real trigger or action
# (달성, 삭제, 파기, ...) are intentionally NOT generic.
_VOCAB: dict[str, frozenset[str]] = {
    "purpose": _COMMON | {"서비스", "업무", "목적", "용도", "정보", "운영", "제공", "이용", "사업", "관리", "활용"},
    "item_name": _COMMON | {"개인정보", "정보", "항목", "사항", "내용", "서비스"},
    "end_condition": _COMMON | {"필요시", "시", "때", "경우"},
    "destruction_method": _COMMON | {"정보", "개인정보", "방법", "방식", "처리", "조치", "안전한"},
    "rationale": _COMMON | {"서비스", "업무", "목적", "정보", "개인정보", "운영", "수집", "이용", "사용", "제공", "활용"},
    "task": _COMMON | {"서비스", "업무", "위탁", "운영", "처리", "제공", "관리", "지원"},
}

# "적절한 방법으로 파기": evaluative modifier + only generic words/verbs.
# "해당 정보 삭제" has no modifier and stays specific (Frozen acceptance input).
_DESTRUCTION_MODIFIERS = frozenset({"적절한", "적정한", "안전한", "알맞은", "필요한"})
_DESTRUCTION_VERBS = frozenset({"파기", "폐기", "삭제"})

_PROCESSOR_NOUNS = frozenset({
    "수탁업체", "수탁자", "수탁사", "업체", "회사", "외부", "외부업체", "협력사", "협력업체",
    "위탁업체", "위탁사", "별도", "제3자",
})

_PARTICLES = re.compile(r"(으로|에서|에게|로서|로|을|를|의|에|은|는|이|가|도|과|와)$")
_EDGE_PUNCT = " .,;:!?()[]{}\"'·-–—~"

_BOUNDARY_L = r"(?<![0-9A-Za-z가-힣])"
_BOUNDARY_R = r"(?:입니다|이다|임)?(?![0-9A-Za-z가-힣])"
_UNDETERMINED = re.compile(
    _BOUNDARY_L
    + r"(?:미정|미확정|TBD|협의\s*중|선정\s*중|검토\s*중|추후\s*(?:결정|확정|지정)|결정\s*예정|협의\s*예정)"
    + _BOUNDARY_R,
    re.IGNORECASE,
)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text))
    return re.sub(r"\s+", " ", text).strip(_EDGE_PUNCT)


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[\s,/·]+", normalize(text)) if t]


def _stem(token: str) -> str:
    return _PARTICLES.sub("", token) or token


def _stems(text: str) -> list[str]:
    return [_stem(t) for t in _tokens(text)]


def is_generic_only(text: str, kind: str) -> bool:
    stems = _stems(text)
    if not stems:
        return False
    vocab = _VOCAB.get(kind, frozenset())
    if all(s in vocab for s in stems):
        return True
    if kind == "destruction_method":
        return any(s in _DESTRUCTION_MODIFIERS for s in stems) and all(
            s in vocab or s in _DESTRUCTION_VERBS for s in stems
        )
    return False


def is_processor_undetermined(text: str) -> bool:
    return bool(_UNDETERMINED.search(normalize(text)))


def is_processor_unspecific(text: str) -> bool:
    stems = _stems(text)
    return bool(stems) and all(s in _PROCESSOR_NOUNS for s in stems)


def classify(text: str, kind: str) -> str | None:
    """Reason code if ``text`` is not concrete for ``kind``, else None."""
    if not isinstance(text, str) or not text.strip():
        return None
    if kind == "processor":
        if is_processor_undetermined(text):
            return PROCESSOR_UNDETERMINED
        if is_processor_unspecific(text):
            return PROCESSOR_UNSPECIFIC
        return None
    return GENERIC_ONLY if is_generic_only(text, kind) else None

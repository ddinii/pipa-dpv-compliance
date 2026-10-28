"""Shared deterministic vocabulary for selected PoC1 rights inventory checks.

Does not claim to enumerate every legal right. Text comes from F1-11 only.
"""

import re

RIGHTS_CHECKS = ("열람", "정정", "삭제", "처리정지", "동의 철회")

# Legacy hand-authored Protege RDF sometimes lacks labels on known IRIs.
# Never infer names from the opaque right_<hash> identifiers produced by Mapper.
LEGACY_RIGHT_IRI_ALIASES = {
    "RightAccess": "열람",
    "RightCorrectionDeletion": "정정·삭제",
    "RightSuspension": "처리정지",
    "RightWithdraw": "동의 철회",
}


# Parenthetical caveats ("(다른 법령에서 … 삭제 불가)") qualify a right; they do
# not negate it. Drop them before matching so one caveat word cannot erase the
# right it qualifies. A right is negated only when the main text says so.
_CAVEAT = re.compile(r"[(（\[][^)）\]]*[)）\]]")


def recognized_rights(label: str) -> set[str]:
    """Map an extracted F1-11 label to selected categories (never legal advice)."""
    compact = re.sub(r"[\s·ㆍ_\-]", "", _CAVEAT.sub("", label)).casefold()
    # A negative notice is not a grant of the mentioned right.
    if any(token in compact for token in ("불가", "금지", "불허", "할수없", "제한됨")):
        return set()
    result: set[str] = set()
    if "열람" in compact:
        result.add("열람")
    if "정정" in compact or "수정요구" in compact:
        result.add("정정")
    if "삭제" in compact:
        result.add("삭제")
    # "처리정지"는 "처리의 정지", "처리 중지/중단"으로도 쓴다
    if re.search(r"처리(?:의)?(?:정지|중지|중단)", compact):
        result.add("처리정지")
    if re.search(r"동의(?:를|의)?철회", compact) or "동의취소" in compact:
        result.add("동의 철회")
    return result

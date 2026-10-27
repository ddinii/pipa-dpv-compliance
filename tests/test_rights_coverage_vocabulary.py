"""Pre-flight vocabulary tests for P1-R08 without enabling the rule."""

import pytest

from app.rules.rights_coverage import RIGHTS_CHECKS, LEGACY_RIGHT_IRI_ALIASES, recognized_rights


@pytest.mark.parametrize("text, expected", [
    ("개인정보 열람 요구", {"열람"}),
    ("정정·삭제 요구", {"정정", "삭제"}),
    ("처리정지 요구", {"처리정지"}),
    ("동의 철회", {"동의 철회"}),
    ("동의를 철회", {"동의 철회"}),
    ("처리 중지 요구", {"처리정지"}),
    ("열람 불가", set()),
    ("삭제할 수 없음", set()),
    ("마케팅 수신 안내", set()),
])
def test_recognized_rights(text, expected):
    assert recognized_rights(text) == expected


def test_selected_rights_scope_is_explicit():
    assert RIGHTS_CHECKS == ("열람", "정정", "삭제", "처리정지", "동의 철회")
    assert LEGACY_RIGHT_IRI_ALIASES["RightCorrectionDeletion"] == "정정·삭제"

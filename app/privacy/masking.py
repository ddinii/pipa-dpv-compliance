"""화면·API 출력용 개인정보 마스킹 (표시제한).

근거: 개인정보 보호법은 몇 자리를 가릴지 정하지 않는다. 「개인정보의 안전성 확보조치
기준」 제12조는 출력·화면 표시 시 항목을 최소화하라는 원칙만 둔다. 아래 자릿수는 그
원칙에 따른 **실무 관행 기준**이며, 이메일은 관행 기준이 없어 팀이 정한 것이다
(2026-10-28 결정).

| 항목       | 기준                     | 예                      |
|------------|--------------------------|-------------------------|
| 주민등록번호 | 뒷 6자리               | 900101-1******          |
| 전화번호    | 가운데 국번              | 010-****-5678           |
| 카드번호    | 가운데 8자리             | 1234-****-****-3456     |
| 성명        | 가운데 글자 (2자면 끝 글자) | 홍*동, 홍*            |
| 이메일 (팀 기준) | 아이디 앞 3자리 외 (3자리 이하면 첫 글자 외) | pri****@example.com, a**@x.com |

마스킹은 **출력 경계**에서만 한다. 내부 Fact는 원문 그대로 둔다. 근거 offset 검증과
환각 검사가 원문 문자열을 그대로 비교하기 때문이다.

자유 텍스트에서는 형식으로 식별되는 번호·이메일만 가린다. 성명은 형식으로 찾을 수
없으므로 이름이 들어 있다고 알려진 필드에만 mask_name()을 쓴다.
"""

from __future__ import annotations

import re
from typing import Any

# 숫자가 영문자·숫자·밑줄에 붙어 있으면 번호로 보지 않는다. 내부 ID(right_0123456789ab 같은
# 해시)의 숫자열이 전화번호로 잘못 가려지는 것을 막는다.
_B = r"(?<![A-Za-z0-9_])"
_E = r"(?![A-Za-z0-9_])"

# 주민등록번호: 앞 6자리 + 성별 1자리는 남기고 뒤 6자리를 가린다.
_RRN = re.compile(_B + r"(\d{6})[-\s]?([1-8])(\d{6})" + _E)

# 카드번호: 4-4-4-4 (구분자 - 또는 공백 또는 없음). 가운데 8자리를 가린다.
_CARD = re.compile(_B + r"(\d{4})([-\s]?)(\d{4})\2(\d{4})\2(\d{4})" + _E)

# 전화번호: 0으로 시작하는 지역·이동통신 번호만. 1588-0000 같은 기업 대표번호와
# 2026-09-05 같은 날짜는 0으로 시작하지 않아 걸리지 않는다.
_PHONE = re.compile(_B + r"(0\d{1,2})([-.\s]?)(\d{3,4})\2(\d{4})" + _E)

_EMAIL = re.compile(r"(?<![\w.+-])([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def mask_rrn(text: str) -> str:
    return _RRN.sub(lambda m: f"{m.group(1)}-{m.group(2)}******", text)


def mask_card(text: str) -> str:
    def repl(m: re.Match) -> str:
        sep = m.group(2) or "-"
        return sep.join([m.group(1), "****", "****", m.group(5)])

    return _CARD.sub(repl, text)


def mask_phone(text: str) -> str:
    def repl(m: re.Match) -> str:
        sep = m.group(2) or "-"
        return sep.join([m.group(1), "*" * len(m.group(3)), m.group(4)])

    return _PHONE.sub(repl, text)


def mask_email(text: str) -> str:
    """아이디(@ 앞) 앞 3자리만 보이고 나머지는 가린다. 3자리 이하면 첫 글자만 보인다 (팀 기준)."""

    def repl(m: re.Match) -> str:
        local = m.group(1)
        visible = local[:3] if len(local) > 3 else local[:1]
        return f"{visible}{'*' * (len(local) - len(visible))}@{m.group(2)}"

    return _EMAIL.sub(repl, text)


def mask_name(name: str) -> str:
    """성명 필드 전용. 가운데 글자를 가린다 (2자면 끝 글자)."""
    name = name.strip()
    if len(name) <= 1:
        return name
    if len(name) == 2:
        return name[0] + "*"
    return name[0] + "*" * (len(name) - 2) + name[-1]


def mask_text(text: str) -> str:
    """자유 텍스트의 주민번호·카드번호·전화번호·이메일을 가린다.

    주민번호와 카드번호를 전화번호보다 먼저 가린다. 순서를 바꾸면 긴 번호의 일부가
    전화번호로 잘못 잡힌다.
    """
    for mask in (mask_rrn, mask_card, mask_phone, mask_email):
        text = mask(text)
    return text


def mask_payload(value: Any) -> Any:
    """API 응답 같은 중첩 구조의 모든 문자열에 mask_text를 적용한다. 키는 바꾸지 않는다."""
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, list):
        return [mask_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: mask_payload(item) for key, item in value.items()}
    return value

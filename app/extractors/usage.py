"""LLM 호출량 집계.

추출 품질만 재고 비용을 재지 않으면 모델 선택을 할 수 없다. 캐시가 실제로
먹는지도 응답의 usage를 봐야 알 수 있다 — 프롬프트에 cache_control을 걸었다는
사실만으로는 캐시 prefix가 맞았는지 알 수 없기 때문이다.

Extractor가 응답 객체를 버리지 않고 여기에 누적한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Anthropic usage 객체에서 읽는 필드
TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


@dataclass
class Usage:
    """한 번의 추출에서 발생한 호출량."""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    def record(self, response: Any) -> None:
        """응답 하나의 usage를 더한다.

        스텁 응답에는 usage가 없다. 그 경우 호출 수만 센다 — 테스트가 usage를
        흉내 내도록 강요하면 스텁이 실제 SDK 모양을 따라다녀야 해서 깨지기 쉽다.
        """
        self.calls += 1
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        for field in TOKEN_FIELDS:
            value = getattr(usage, field, None)
            if isinstance(value, int):
                setattr(self, field, getattr(self, field) + value)

    def merge(self, other: "Usage") -> None:
        self.calls += other.calls
        for field in TOKEN_FIELDS:
            setattr(self, field, getattr(self, field) + getattr(other, field))

    @property
    def total_input_tokens(self) -> int:
        """캐시 쓰기·읽기를 포함한 입력 토큰 총량."""
        return (
            self.input_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
        )

    @property
    def cache_hit_rate(self) -> float:
        """입력 토큰 중 캐시에서 읽은 비율.

        0이면 cache_control을 걸어도 prefix가 어긋나 캐시가 전혀 안 먹은 것이다.
        """
        total = self.total_input_tokens
        return self.cache_read_input_tokens / total if total else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            **{field: getattr(self, field) for field in TOKEN_FIELDS},
            "total_input_tokens": self.total_input_tokens,
            "cache_hit_rate": round(self.cache_hit_rate, 4),
        }


def format_usage(usage: Usage) -> str:
    if usage.calls == 0:
        return "호출 없음"
    if usage.total_input_tokens == 0:
        # 스텁으로 돌린 경우. 토큰을 모른다고 분명히 말한다.
        return f"호출 {usage.calls}회 · 토큰 정보 없음"
    return (
        f"호출 {usage.calls}회 · 입력 {usage.total_input_tokens:,} "
        f"(캐시 읽기 {usage.cache_read_input_tokens:,} · 쓰기 "
        f"{usage.cache_creation_input_tokens:,}) · 출력 {usage.output_tokens:,} "
        f"· 캐시 적중률 {usage.cache_hit_rate:.0%}"
    )

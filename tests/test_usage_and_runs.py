"""호출량 집계와 실행 간 비교.

추출 품질만 재고 비용을 재지 않으면 모델 선택을 할 수 없다. 그리고 실행 결과가
서로 덮어쓰이면 비교 자체가 불가능하다. 둘 다 첫 실제 실행에서만 얻을 수 있는
정보라 미리 갖춰 둔다.
"""

import json

import pytest

from app.extractors.poc1 import IdentifiedActivity, PoC1Extractor
from app.extractors.poc2 import PoC2Extractor
from app.extractors.usage import Usage, format_usage
from evals.compare_runs import best_and_worst, dig, load_runs, table


class FakeUsage:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class StubMessages:
    """usage를 실어 보내는 스텁."""

    def __init__(self, responses: list, usage: FakeUsage | None = None):
        self.responses = list(responses)
        self.usage = usage

    def parse(self, **kwargs):
        payload = self.responses.pop(0)
        return type(
            "Response", (),
            {"parsed_output": payload, "stop_reason": "end_turn", "usage": self.usage},
        )()


def fact_list(*facts):
    return type("FactList", (), {"facts": list(facts)})()


# --- Usage ---------------------------------------------------------------


def test_record_counts_calls_even_without_usage():
    """스텁 응답에는 usage가 없다. 그래도 호출 수는 세야 한다."""
    usage = Usage()
    usage.record(type("R", (), {})())
    assert usage.calls == 1
    assert usage.total_input_tokens == 0


def test_record_accumulates_every_token_field():
    usage = Usage()
    for _ in range(2):
        usage.record(type("R", (), {"usage": FakeUsage(
            input_tokens=100, output_tokens=50,
            cache_creation_input_tokens=10, cache_read_input_tokens=400,
        )})())
    assert usage.calls == 2
    assert usage.input_tokens == 200
    assert usage.output_tokens == 100
    assert usage.cache_creation_input_tokens == 20
    assert usage.cache_read_input_tokens == 800


def test_total_input_includes_cache_write_and_read():
    """캐시 쓰기와 읽기도 입력 토큰이다. 빼먹으면 비용을 과소평가한다."""
    usage = Usage(input_tokens=100, cache_creation_input_tokens=10,
                  cache_read_input_tokens=400)
    assert usage.total_input_tokens == 510


def test_cache_hit_rate_is_zero_when_the_prefix_never_matched():
    """cache_control을 걸어도 prefix가 어긋나면 적중률이 0이다.

    프롬프트에 캐시를 걸었다는 사실만으로는 캐시가 먹었는지 알 수 없다.
    이 값이 0이면 지침 블록이 pass마다 달라 prefix가 처음부터 어긋난 것이다.
    """
    assert Usage(input_tokens=1000).cache_hit_rate == 0.0
    assert Usage(input_tokens=200, cache_read_input_tokens=800).cache_hit_rate == 0.8


def test_merge_adds_two_runs():
    total = Usage(calls=1, input_tokens=10)
    total.merge(Usage(calls=2, input_tokens=5, output_tokens=7))
    assert (total.calls, total.input_tokens, total.output_tokens) == (3, 15, 7)


def test_format_says_so_when_tokens_are_unknown():
    """스텁 실행 결과를 실제 측정치처럼 보이게 하면 안 된다."""
    assert "토큰 정보 없음" in format_usage(Usage(calls=3))
    assert format_usage(Usage()) == "호출 없음"


def test_as_dict_is_json_serializable():
    payload = Usage(calls=1, input_tokens=2, cache_read_input_tokens=8).as_dict()
    assert json.loads(json.dumps(payload))["cache_hit_rate"] == 0.8


# --- Extractor가 usage를 실어 보내는가 -----------------------------------


def test_poc1_extractor_reports_usage():
    from app.extractors.poc1 import ActivityList

    activity = IdentifiedActivity(
        activity_id="act-collection-001",
        ontology_class="CollectionAndUse",
        heading="회원 가입",
    )
    stub = StubMessages(
        [ActivityList(activities=[activity]), fact_list(), fact_list()],
        usage=FakeUsage(input_tokens=1000, output_tokens=200,
                        cache_creation_input_tokens=0, cache_read_input_tokens=0),
    )
    result = PoC1Extractor(stub).extract("회원 가입 안내 문서입니다.")
    # Pass 1 + 처리행위 1개 + 권리 = 3회
    assert result.usage.calls == 3
    assert result.usage.input_tokens == 3000
    assert result.usage.output_tokens == 600


def test_poc2_extractor_reports_two_calls():
    stub = StubMessages(
        [fact_list(), fact_list()],
        usage=FakeUsage(input_tokens=500, output_tokens=100,
                        cache_creation_input_tokens=0, cache_read_input_tokens=0),
    )
    result = PoC2Extractor(stub).extract(
        {"record": "사고 기록입니다."}, {"notice_text": "통지문입니다."}
    )
    assert result.usage.calls == 2
    assert result.usage.input_tokens == 1000


def test_usage_resets_between_extractions():
    """같은 Extractor로 여러 케이스를 돌려도 케이스별로 따로 세야 한다."""
    from app.extractors.poc1 import ActivityList

    usage = FakeUsage(input_tokens=100, output_tokens=10,
                      cache_creation_input_tokens=0, cache_read_input_tokens=0)
    extractor = PoC1Extractor(StubMessages([ActivityList(activities=[]), fact_list()],
                                           usage=usage))
    first = extractor.extract("문서")
    extractor.messages = StubMessages([ActivityList(activities=[]), fact_list()],
                                      usage=usage)
    second = extractor.extract("문서")
    assert first.usage.calls == second.usage.calls == 2


# --- 실행 간 비교 ---------------------------------------------------------


@pytest.fixture
def runs_dir(tmp_path):
    directory = tmp_path / "runs"
    directory.mkdir()
    for label, f1, false_green in (
        ("poc1-opus-cache", 0.91, 0.04),
        ("poc1-sonnet-cache", 0.84, 0.12),
    ):
        (directory / f"{label}.json").write_text(json.dumps({
            "label": label,
            "usage": {"calls": 109, "total_input_tokens": 402000,
                      "output_tokens": 150000, "cache_hit_rate": 0.48},
            "fact_level": {"f1": f1, "precision": f1, "recall": f1,
                           "value_accuracy": 0.9, "hallucination_rate": 0.02,
                           "activity_leak_rate": 0.0},
            "rule_level": {"agreement": 0.95, "false_green_rate": false_green},
        }, ensure_ascii=False), encoding="utf-8")
    return directory


def test_runs_are_loaded_and_labelled(runs_dir):
    runs = load_runs(runs_dir)
    assert {run["label"] for run in runs} == {"poc1-opus-cache", "poc1-sonnet-cache"}


def test_ranking_uses_false_green_rate_not_f1(runs_dir):
    """헤드라인 지표는 F1이 아니라 위험 오판율이다.

    Fact를 몇 개 맞췄는지보다 "추출 오류가 판정을 뒤집는가"가 실무 영향이다.
    여기서 F1으로 줄을 세우면 평가 설계의 요점이 무너진다.
    """
    ranking = best_and_worst(load_runs(runs_dir))
    opus = ranking.index("poc1-opus-cache")
    sonnet = ranking.index("poc1-sonnet-cache")
    assert opus < sonnet, "위험 오판율이 낮은 실행이 위에 와야 한다"


def test_missing_metric_renders_as_dash(tmp_path):
    """옛 실행 결과에 새 지표가 없어도 표가 깨지지 않아야 한다."""
    directory = tmp_path / "runs"
    directory.mkdir()
    (directory / "old.json").write_text(json.dumps({"label": "old"}), encoding="utf-8")
    rendered = table(load_runs(directory), [("F1", ("fact_level", "f1"), ".3f", True)])
    assert "-" in rendered


def test_dig_returns_none_for_a_missing_path():
    assert dig({"a": {"b": 1}}, ("a", "b")) == 1
    assert dig({"a": {"b": 1}}, ("a", "c")) is None
    assert dig({}, ("a", "b")) is None

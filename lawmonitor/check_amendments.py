"""
국내 개인정보보호법 개정 추적 (PoC)

backend/rules/rule_engine.py 가 인용하는 조문(개인정보 보호법 제30조·제28조의8·
제22조의2, 시행령 제31조)이 국가법령정보센터(law.go.kr) 기준으로 바뀌었는지
주기적으로 확인하기 위한 수동 실행 스크립트입니다.

실행:
    python -m lawmonitor.check_amendments

필요 설정:
    .env 에 LAW_GO_KR_OC (국가법령정보센터 Open API 키, 이메일 아이디 형식) 설정.
    미설정 시 안내만 하고 정상 종료합니다 (ANTHROPIC_API_KEY/MockExtractor와 동일한 폴백 패턴).
    신청: https://open.law.go.kr/LSO/openApi/cuAskList.do (승인까지 1~2일 소요)

⚠️ 중요 — 이 스크립트는 실제 API 응답으로 검증되지 않았습니다.
    국가법령정보센터 Open API의 정확한 XML 스키마(조문단위/조문번호/조문내용 등의
    태그명)는 공식 문서에서 확인 가능한 요청 URL 패턴을 기반으로 일반적인 관례를
    따라 작성했습니다. OC 키를 발급받아 처음 실행했을 때 조문을 못 찾는다는 오류가
    나면, 아래 fetch_law_articles()의 XML 파싱 부분을 실제 응답 구조에 맞게
    조정해야 합니다.

⚠️ 이 스크립트는 수동 실행 PoC입니다. 실제 운영 환경에서는 GitHub Actions
    스케줄 워크플로우나 Windows 작업 스케줄러로 주기 실행하는 것을 권장합니다.
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

LAW_SERVICE_URL = "https://www.law.go.kr/DRF/lawService.do"

# rule_engine.py 가 실제로 인용하는 조문만 추적 대상으로 삼는다.
TARGET_ARTICLES: dict[str, list[str]] = {
    "개인정보 보호법": ["제30조", "제28조의8", "제22조의2"],
    "개인정보 보호법 시행령": ["제31조"],
}

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "data" / "law_snapshots"


@dataclass
class LawSnapshot:
    checked_at: str
    articles: dict[str, str] = field(default_factory=dict)  # "개인정보 보호법 제30조" -> 조문 텍스트

    def to_json(self) -> dict:
        return {"checked_at": self.checked_at, "articles": self.articles}

    @classmethod
    def from_json(cls, data: dict) -> "LawSnapshot":
        return cls(checked_at=data["checked_at"], articles=data["articles"])


def _article_id(조문번호: str, 조문가지번호: str) -> str:
    """법령정보센터의 조문번호/조문가지번호를 '제30조', '제28조의8' 형식으로 변환"""
    base = f"제{조문번호}조"
    if 조문가지번호 and 조문가지번호 not in ("0", ""):
        base += f"의{조문가지번호}"
    return base


def fetch_law_articles(law_name: str, target_articles: list[str], oc: str) -> dict[str, str]:
    """국가법령정보센터 법령 본문 조회 API를 호출해 지정한 조문들의 텍스트를 가져온다.

    응답 XML 안에서 조문번호/조문가지번호/조문내용(또는 항내용) 태그를 이름 기반으로
    찾는다 — 정확한 스키마 확인 전이라, 고정된 XPath 대신 iter()로 유연하게 탐색한다.
    """
    resp = httpx.get(
        LAW_SERVICE_URL,
        params={"OC": oc, "target": "law", "type": "XML", "LM": law_name},
        timeout=30,
    )
    resp.raise_for_status()

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        raise RuntimeError(
            f"'{law_name}' 응답을 XML로 파싱하지 못했습니다. OC 키가 유효한지, "
            f"법령명이 정확한지 확인하세요. (원본 오류: {e})"
        ) from e

    found: dict[str, str] = {}
    for unit in root.iter("조문단위"):
        no_el = unit.find("조문번호")
        gaji_el = unit.find("조문가지번호")
        if no_el is None or not (no_el.text or "").strip():
            continue
        article_id = _article_id((no_el.text or "").strip(), (gaji_el.text if gaji_el is not None else "0") or "0")
        if article_id not in target_articles:
            continue

        content_el = unit.find("조문내용")
        text_parts = [content_el.text or ""] if content_el is not None else []
        for hang in unit.iter("항내용"):
            text_parts.append(hang.text or "")
        for ho in unit.iter("호내용"):
            text_parts.append(ho.text or "")

        text = re.sub(r"\s+", " ", " ".join(text_parts)).strip()
        if text:
            found[f"{law_name} {article_id}"] = text

    missing = [f"{law_name} {a}" for a in target_articles if f"{law_name} {a}" not in found]
    if missing:
        raise RuntimeError(
            f"다음 조문을 응답에서 찾지 못했습니다: {missing}. "
            "국가법령정보센터 API의 실제 XML 스키마가 이 스크립트가 가정한 것과 "
            "다를 수 있습니다 — check_amendments.py의 fetch_law_articles()를 "
            "실제 응답을 보고 조정하세요."
        )
    return found


def build_snapshot(oc: str) -> LawSnapshot:
    articles: dict[str, str] = {}
    for law_name, target_articles in TARGET_ARTICLES.items():
        articles.update(fetch_law_articles(law_name, target_articles, oc))
    return LawSnapshot(checked_at=datetime.now(timezone.utc).isoformat(), articles=articles)


def find_latest_snapshot(directory: Path = SNAPSHOT_DIR) -> Path | None:
    if not directory.is_dir():
        return None
    snapshots = sorted(directory.glob("pipa_snapshot_*.json"))
    return snapshots[-1] if snapshots else None


def save_snapshot(snapshot: LawSnapshot, directory: Path = SNAPSHOT_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"pipa_snapshot_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
    path = directory / filename
    path.write_text(json.dumps(snapshot.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def diff_snapshots(old: LawSnapshot, new: LawSnapshot) -> list[str]:
    """바뀌었거나(내용 변경) 새로 생긴/사라진 조문 id 목록을 반환"""
    changed = []
    all_keys = set(old.articles) | set(new.articles)
    for key in sorted(all_keys):
        if old.articles.get(key) != new.articles.get(key):
            changed.append(key)
    return changed


def main() -> int:
    oc = os.environ.get("LAW_GO_KR_OC", "").strip()
    if not oc:
        print(
            "[lawmonitor] LAW_GO_KR_OC가 설정되지 않아 건너뜁니다.\n"
            "  신청: https://open.law.go.kr/LSO/openApi/cuAskList.do (승인 1~2일 소요)\n"
            "  발급 후 .env 에 LAW_GO_KR_OC=<이메일 아이디> 를 추가하세요."
        )
        return 0

    try:
        new_snapshot = build_snapshot(oc)
    except (httpx.HTTPError, RuntimeError) as e:
        print(f"[lawmonitor] 법령 조회 실패: {e}")
        return 1

    latest_path = find_latest_snapshot()
    if latest_path is None:
        print("[lawmonitor] 이전 스냅샷이 없어 최초 스냅샷을 저장합니다.")
    else:
        old_snapshot = LawSnapshot.from_json(json.loads(latest_path.read_text(encoding="utf-8")))
        changed = diff_snapshots(old_snapshot, new_snapshot)
        if changed:
            print("[lawmonitor] ⚠️ 조문 변경이 감지되었습니다:")
            for key in changed:
                print(f"  - {key}")
            print(
                "  backend/rules/rule_engine.py 상단의 검증일(2026-08-26) 이후 개정 사항입니다. "
                "legal_basis와 판정 로직을 재검토하세요."
            )
        else:
            print("[lawmonitor] 변경 없음.")

    saved_path = save_snapshot(new_snapshot)
    print(f"[lawmonitor] 스냅샷 저장: {saved_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

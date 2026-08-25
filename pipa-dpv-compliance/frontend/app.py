"""
PIPA-DPV Compliance Checker — Streamlit 데모 UI

실행:
    streamlit run frontend/app.py

백엔드(backend/main.py, 기본 http://localhost:8000)가 먼저 실행되어 있어야 합니다.
"""

import os
import httpx
import streamlit as st

API_BASE = os.environ.get("PIPA_DPV_API_BASE", "http://localhost:8000")

VERDICT_COLOR = {"GREEN": "🟢", "RED": "🔴", "AMBER": "🟡"}

st.set_page_config(page_title="PIPA-DPV Compliance Checker", layout="wide")

st.title("PIPA-DPV 개인정보 처리방침 자동 점검 (PoC)")
st.caption(
    "W3C DPV 기반 한국 개인정보보호법 기계판독 규칙체계 — 데모용 프로토타입. "
    "판정 결과는 참고용이며 법적 적법성을 확정하지 않습니다."
)

sample_dir = os.path.join(os.path.dirname(__file__), "..", "data", "sample_policies")
sample_files = sorted(os.listdir(sample_dir)) if os.path.isdir(sample_dir) else []

col_input, col_result = st.columns([1, 1.3])

with col_input:
    st.subheader("1. 처리방침 입력")
    selected_sample = st.selectbox("샘플 불러오기 (선택)", ["직접 입력"] + sample_files)

    default_text = ""
    if selected_sample != "직접 입력":
        with open(os.path.join(sample_dir, selected_sample), encoding="utf-8") as f:
            default_text = f.read()

    policy_text = st.text_area("처리방침 원문", value=default_text, height=420)
    run_button = st.button("점검 실행", type="primary")

with col_result:
    st.subheader("2. 판정 결과")
    if run_button:
        if not policy_text.strip():
            st.warning("처리방침 텍스트를 입력해주세요.")
        else:
            with st.spinner("추출 및 판정 중..."):
                try:
                    resp = httpx.post(
                        f"{API_BASE}/compliance-check/text",
                        json={"text": policy_text},
                        timeout=60,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError as e:
                    st.error(f"API 호출 실패: {e}")
                    data = None

            if data:
                report = data["report"]
                overall = report["overall_verdict"]
                st.markdown(f"### 종합 판정: {VERDICT_COLOR[overall]} **{overall}**")

                c1, c2, c3 = st.columns(3)
                c1.metric("GREEN", report["green_count"])
                c2.metric("RED", report["red_count"])
                c3.metric("AMBER", report["amber_count"])

                st.divider()
                for r in report["results"]:
                    icon = VERDICT_COLOR[r["verdict"]]
                    with st.expander(f"{icon} [{r['rule_id']}] {r['rule_name']}"):
                        st.write(f"**판정**: {r['verdict']}")
                        st.write(f"**근거 조문**: {r['legal_basis']}")
                        st.write(f"**판정 근거**: {r['rationale']}")

                st.caption(data.get("disclaimer", ""))
    else:
        st.info("왼쪽에 처리방침을 입력하고 '점검 실행'을 눌러주세요.")

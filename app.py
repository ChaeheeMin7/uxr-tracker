"""
app.py  ── 3단계: Streamlit 웹 대시보드
────────────────────────────────────────
로컬 실행:   streamlit run app.py
Streamlit Cloud 배포: GitHub에 push 후 share.streamlit.io 에서 연결
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import anthropic
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="UXR Career Tracker",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 커스텀 CSS (깔끔한 포트폴리오 느낌) ──────────────────────────────────────
st.markdown("""
<style>
  /* 폰트 & 전체 배경 */
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

  /* 메인 헤더 */
  .main-title {
    font-size: 2rem;
    font-weight: 700;
    color: #0e4d92;
    margin-bottom: 0;
  }
  .sub-title {
    font-size: 0.9rem;
    color: #888;
    margin-top: 0;
  }

  /* 메트릭 카드 */
  [data-testid="metric-container"] {
    background: #f8faff;
    border: 1px solid #e0e8f5;
    border-radius: 10px;
    padding: 12px 16px;
  }

  /* 섹션 헤더 */
  .section-header {
    font-size: 1rem;
    font-weight: 700;
    color: #333;
    border-left: 4px solid #0e4d92;
    padding-left: 10px;
    margin: 24px 0 12px;
  }

  /* 갭 카드 */
  .gap-card {
    background: #fffbf0;
    border: 1px solid #ffe0a0;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 10px;
  }
  .gap-card-title { font-weight: 700; color: #b35c00; font-size: 0.9rem; }
  .gap-card-body  { color: #555; font-size: 0.85rem; margin-top: 4px; }

  /* 서사 박스 */
  .narrative-box {
    background: linear-gradient(135deg, #f0f7ff, #f8fff4);
    border: 1px solid #b0d4f1;
    border-radius: 10px;
    padding: 16px 20px;
    font-style: italic;
    color: #1a3a5c;
    font-size: 0.95rem;
    line-height: 1.8;
  }

  /* 하단 여백 */
  footer { display: none; }
</style>
""", unsafe_allow_html=True)


# ── 데이터 로드 ───────────────────────────────────────────────────────────────
MARKET_CSV   = Path("data/market.csv")
PERSONAL_CSV = Path("data/personal.csv")

@st.cache_data(ttl=300)  # 5분 캐시 (Streamlit Cloud에서 자동 갱신)
def load_market() -> pd.DataFrame:
    if not MARKET_CSV.exists():
        # 샘플 데이터 (첫 실행 시 빈 화면 방지)
        return pd.DataFrame({
            "date":          [date.today().isoformat()],
            "week":          [date.today().strftime("%Y-W%W")],
            "source":        ["샘플"],
            "title":         ["수집 데이터 없음 — collect.py 를 먼저 실행하세요"],
            "keywords_found":["사용자 인터뷰|정성조사"],
            "keyword_count": [2],
            "hiring_mode":   ["BUILD"],
            "raw_snippet":   [""],
        })
    df = pd.read_csv(MARKET_CSV)
    df["date"] = pd.to_datetime(df["date"])
    return df

@st.cache_data(ttl=60)
def load_personal() -> pd.DataFrame:
    if not PERSONAL_CSV.exists():
        return pd.DataFrame(columns=["month","skill","score","activity"])
    return pd.read_csv(PERSONAL_CSV)


# ── 사이드바 ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 UXR Career Tracker")
    st.caption("UX 리서처 취업 시장 × 나의 성장 추적기")
    st.divider()

    page = st.radio(
        "페이지",
        ["📊 시장 트렌드", "📈 내 성장 기록", "🤖 AI 갭 분석", "📝 로그 입력"],
        label_visibility="collapsed",
    )

    st.divider()

    # 기간 필터
    df_all = load_market()
    if not df_all.empty and "date" in df_all.columns:
        min_date = df_all["date"].min().date()
        max_date = df_all["date"].max().date()
    else:
        min_date = max_date = date.today()

    date_range = st.date_input(
        "기간 필터",
        value=(max(min_date, date.today() - timedelta(days=90)), max_date),
        min_value=min_date,
        max_value=max_date,
    )

    st.divider()
    st.caption(f"마지막 수집: {max_date}")
    st.caption(f"총 수집: {len(df_all):,}건")


# ── 데이터 필터링 ─────────────────────────────────────────────────────────────
df = load_market()
if len(date_range) == 2:
    start, end = date_range
    mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
    df = df[mask]


# ══════════════════════════════════════════════════════════════════════════════
# 페이지 1: 시장 트렌드
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 시장 트렌드":
    st.markdown('<div class="main-title">📊 UX 리서처 채용 시장 트렌드</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">수집 기간: {df["date"].min().date()} ~ {df["date"].max().date()} | {len(df):,}건</div>', unsafe_allow_html=True)

    # ── 요약 메트릭 ──────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    all_kws: list[str] = []
    for row in df["keywords_found"].dropna():
        all_kws.extend([k for k in row.split("|") if k])

    kw_freq = Counter(all_kws)
    top_kw  = kw_freq.most_common(1)[0][0] if kw_freq else "—"
    weeks   = df["week"].nunique() if "week" in df.columns else 0
    build_pct = round(len(df[df["hiring_mode"]=="BUILD"]) / max(len(df),1) * 100)

    with col1: st.metric("수집 공고 수",      f"{len(df):,}건")
    with col2: st.metric("추적 주차",         f"{weeks}주")
    with col3: st.metric("🔥 1위 키워드",     top_kw)
    with col4: st.metric("신규세팅(BUILD) 비율", f"{build_pct}%")

    st.markdown("")

    # ── 키워드 트렌드 차트 ────────────────────────────────────────────────────
    st.markdown('<div class="section-header">키워드 주별 빈도 추이</div>', unsafe_allow_html=True)

    # 주별 × 키워드 집계
    rows_expanded = []
    for _, r in df.iterrows():
        for kw in str(r.get("keywords_found","")).split("|"):
            kw = kw.strip()
            if kw:
                rows_expanded.append({"week": r["week"], "keyword": kw})

    if rows_expanded:
        kw_df = pd.DataFrame(rows_expanded)
        top15 = [k for k, _ in Counter(kw_df["keyword"].tolist()).most_common(15)]

        selected_kws = st.multiselect(
            "키워드 선택 (최대 6개)",
            options=top15,
            default=top15[:6],
            max_selections=6,
        )

        if selected_kws:
            pivot = (
                kw_df[kw_df["keyword"].isin(selected_kws)]
                .groupby(["week","keyword"])
                .size()
                .reset_index(name="count")
                .pivot(index="week", columns="keyword", values="count")
                .fillna(0)
                .sort_index()
            )
            fig_trend = px.line(
                pivot, x=pivot.index, y=pivot.columns,
                markers=True,
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Set2,
                labels={"value": "언급 횟수", "week": "주차", "variable": "키워드"},
            )
            fig_trend.update_layout(
                height=350,
                font=dict(family="Noto Sans KR", size=12),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                margin=dict(l=0, r=0, t=30, b=0),
            )
            st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("수집된 데이터가 없습니다. collect.py 를 먼저 실행하세요.")

    # ── 키워드 랭킹 + 채용 모드 ──────────────────────────────────────────────
    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown('<div class="section-header">전체 키워드 랭킹</div>', unsafe_allow_html=True)
        if kw_freq:
            kw_rank = pd.DataFrame(
                kw_freq.most_common(20), columns=["키워드", "언급 횟수"]
            )
            fig_bar = px.bar(
                kw_rank, x="언급 횟수", y="키워드", orientation="h",
                color="언급 횟수",
                color_continuous_scale=["#cce5ff", "#0e4d92"],
                template="plotly_white",
            )
            fig_bar.update_layout(
                height=420, showlegend=False,
                font=dict(family="Noto Sans KR", size=11),
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis={"categoryorder":"total ascending"},
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">채용 모드 분포</div>', unsafe_allow_html=True)
        if "hiring_mode" in df.columns:
            mode_labels = {
                "BUILD":    "🏗 신규 세팅",
                "MAINTAIN": "🔧 공석 충원",
                "SCALE_UP": "🚀 사업 확장",
                "UNKNOWN":  "❓ 불명확",
            }
            mode_cnt = df["hiring_mode"].value_counts().rename(index=mode_labels)
            fig_pie = px.pie(
                values=mode_cnt.values, names=mode_cnt.index,
                color_discrete_sequence=["#4a90d9","#52c27e","#ffb347","#bbb"],
                template="plotly_white",
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(
                height=280, showlegend=False,
                font=dict(family="Noto Sans KR", size=12),
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

            st.caption("BUILD = 팀 신규 세팅 · MAINTAIN = 공석 충원 · SCALE_UP = 사업 확장")

    # ── 최근 수집 원문 ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">최근 수집 공고/기사</div>', unsafe_allow_html=True)
    recent = df.sort_values("date", ascending=False).head(10)[
        ["date","source","title","keyword_count","hiring_mode"]
    ]
    recent.columns = ["날짜","출처","제목","키워드 수","채용 모드"]
    st.dataframe(recent, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# 페이지 2: 내 성장 기록
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 내 성장 기록":
    st.markdown('<div class="main-title">📈 나의 역량 성장 기록</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">매달 업데이트되는 나만의 성장 데이터</div>', unsafe_allow_html=True)

    personal = load_personal()

    if personal.empty:
        st.info("아직 성장 로그가 없어요. **📝 로그 입력** 탭에서 기록을 시작하세요!")
        st.stop()

    # 최신 점수
    st.markdown('<div class="section-header">현재 역량 현황</div>', unsafe_allow_html=True)
    latest = (
        personal.sort_values("month")
        .groupby("skill")
        .last()
        .reset_index()[["skill","score"]]
        .sort_values("score", ascending=False)
    )

    def score_color(s: int) -> str:
        if s >= 70: return "#27ae60"
        if s >= 40: return "#2980b9"
        return "#e67e22"

    cols = st.columns(min(len(latest), 4))
    for i, (_, row) in enumerate(latest.iterrows()):
        with cols[i % 4]:
            color = score_color(int(row["score"]))
            st.markdown(f"""
            <div style="text-align:center;background:#f8faff;border:1px solid #e0e8f5;
              border-radius:10px;padding:14px 8px;margin-bottom:10px">
              <div style="font-size:2rem;font-weight:700;color:{color}">{int(row['score'])}</div>
              <div style="font-size:0.75rem;color:#666;margin-top:4px">{row['skill'][:14]}</div>
            </div>
            """, unsafe_allow_html=True)

    # 성장 곡선
    st.markdown('<div class="section-header">역량 성장 곡선</div>', unsafe_allow_html=True)
    skills_list = personal["skill"].unique().tolist()
    sel_skills  = st.multiselect("역량 선택", skills_list, default=skills_list[:5])

    filtered = personal[personal["skill"].isin(sel_skills)]
    if not filtered.empty:
        fig_growth = px.line(
            filtered, x="month", y="score", color="skill",
            markers=True,
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Set2,
            labels={"month":"월", "score":"점수 (0-100)", "skill":"역량"},
            range_y=[0, 105],
        )
        fig_growth.update_layout(
            height=360,
            font=dict(family="Noto Sans KR", size=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(l=0, r=0, t=30, b=0),
        )
        st.plotly_chart(fig_growth, use_container_width=True)

    # 전체 로그 테이블
    st.markdown('<div class="section-header">전체 기록</div>', unsafe_allow_html=True)
    st.dataframe(
        personal.sort_values("month", ascending=False),
        use_container_width=True, hide_index=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 페이지 3: AI 갭 분석
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 AI 갭 분석":
    st.markdown('<div class="main-title">🤖 AI 갭 분석</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">시장 트렌드 × 내 역량 → Claude가 성장 전략을 제시합니다</div>', unsafe_allow_html=True)

    personal = load_personal()

    col_info, col_btn = st.columns([4,1])
    with col_info:
        st.info("분석에 약 20-30초 소요됩니다. API 요금이 발생합니다 (약 $0.01/회)")
    with col_btn:
        run_gap = st.button("⚡ 분석 실행", type="primary", use_container_width=True)

    if run_gap:
        # 데이터 준비
        all_kws_list: list[str] = []
        for row in df["keywords_found"].dropna():
            all_kws_list.extend([k for k in row.split("|") if k])
        top20 = Counter(all_kws_list).most_common(20)

        my_skills_dict: dict = {}
        if not personal.empty:
            for _, r in (
                personal.sort_values("month")
                .groupby("skill")
                .last()
                .reset_index()
                .iterrows()
            ):
                my_skills_dict[r["skill"]] = int(r["score"])

        sys_prompt = """당신은 UX 리서처 커리어 코치입니다.
시장 키워드 빈도 데이터와 개인 역량 점수를 비교해 성장 전략을 제시합니다.
반드시 유효한 JSON만 출력하세요. 마크다운 없이 순수 JSON."""

        user_prompt = f"""
## 최근 시장 키워드 TOP 20 (언급 횟수)
{json.dumps(top20, ensure_ascii=False)}

## 내 역량 점수 (0-100)
{json.dumps(my_skills_dict, ensure_ascii=False)}

## 분석 지시
다음 JSON 구조로 출력:
{{
  "readiness": <0-100 시장 준비도>,
  "strengths": ["<강점1>", "<강점2>"],
  "gaps": [
    {{
      "skill": "<역량명>",
      "market_demand": "<시장 수요 설명>",
      "my_level": <내 점수 또는 null>,
      "action": "<구체적 행동>"
    }}
  ],
  "monthly_focus": "<이번 달 집중할 한 가지>",
  "plan": ["<이번 달 행동1>", "<행동2>", "<행동3>"],
  "narrative": "<2-3년 후 면접에서 쓸 수 있는 데이터 기반 커리어 서사 초안 2문장>"
}}"""

        with st.spinner("Claude가 분석 중입니다..."):
            try:
                client = anthropic.Anthropic()
                msg = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    system=sys_prompt,
                    messages=[{"role":"user","content":user_prompt}],
                )
                raw  = msg.content[0].text.strip()
                raw  = raw.lstrip("```json").rstrip("```").strip()
                data = json.loads(raw)
                st.session_state["gap_result"] = data
            except Exception as e:
                st.error(f"분석 실패: {e}")
                st.stop()

    # 결과 표시
    if "gap_result" in st.session_state:
        data = st.session_state["gap_result"]

        # 준비도 게이지
        readiness = data.get("readiness", 0)
        col_gauge, col_str = st.columns([1, 2])

        with col_gauge:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=readiness,
                domain={"x":[0,1],"y":[0,1]},
                gauge={
                    "axis": {"range":[0,100],"tickwidth":1,"tickcolor":"#333"},
                    "bar":  {"color":"#0e4d92"},
                    "bgcolor":"white",
                    "steps":[
                        {"range":[0,40],  "color":"#ffeaea"},
                        {"range":[40,70], "color":"#fff8e0"},
                        {"range":[70,100],"color":"#e8fff0"},
                    ],
                    "threshold":{
                        "line":{"color":"#0e4d92","width":3},
                        "thickness":0.75,"value":readiness,
                    },
                },
                title={"text":"시장 준비도","font":{"size":14}},
                number={"suffix":"/100","font":{"size":28,"color":"#0e4d92"}},
            ))
            fig_gauge.update_layout(
                height=200, margin=dict(l=20,r=20,t=40,b=10),
                font=dict(family="Noto Sans KR"),
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

        with col_str:
            st.markdown('<div class="section-header">강점</div>', unsafe_allow_html=True)
            for s in data.get("strengths",[]):
                st.markdown(f"✅ {s}")

        # 핵심 갭
        st.markdown('<div class="section-header">핵심 갭 & 행동 계획</div>', unsafe_allow_html=True)
        for g in data.get("gaps",[]):
            lvl = g.get("my_level")
            lvl_str = f"{lvl}점" if lvl is not None else "미측정"
            st.markdown(f"""
            <div class="gap-card">
              <div class="gap-card-title">⚡ {g.get('skill','')} — 현재 {lvl_str}</div>
              <div class="gap-card-body">
                <b>시장 수요:</b> {g.get('market_demand','')}<br>
                <b>행동:</b> {g.get('action','')}
              </div>
            </div>
            """, unsafe_allow_html=True)

        # 이번 달 플랜
        st.markdown('<div class="section-header">이번 달 플랜</div>', unsafe_allow_html=True)
        focus = data.get("monthly_focus","")
        if focus:
            st.markdown(f"**집중 역량:** `{focus}`")
        for action in data.get("plan",[]):
            st.checkbox(action, key=action)

        # 커리어 서사
        st.markdown('<div class="section-header">2-3년 후 면접 서사 초안</div>', unsafe_allow_html=True)
        narrative = data.get("narrative","")
        if narrative:
            st.markdown(f'<div class="narrative-box">"{narrative}"</div>', unsafe_allow_html=True)
            st.caption("💡 이 서사는 데이터를 더 쌓을수록 더 강력해집니다")


# ══════════════════════════════════════════════════════════════════════════════
# 페이지 4: 로그 입력
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📝 로그 입력":
    st.markdown('<div class="main-title">📝 이번 달 성장 로그</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">매달 말, 5분 투자로 3년치 성장 데이터를 쌓아보세요</div>', unsafe_allow_html=True)

    SKILL_OPTIONS = [
        "사용자 인터뷰",
        "정성 리서치",
        "정량 리서치 / 통계",
        "데이터 분석 (Python/SQL)",
        "Figma / 프로토타이핑",
        "리서치 거버넌스",
        "프로덕트 전략 커뮤니케이션",
        "AI/LLM 활용",
        "영어 커뮤니케이션",
        "프로젝트 리더십",
    ]

    with st.form("log_form"):
        col1, col2 = st.columns(2)

        with col1:
            month  = st.text_input("월 (YYYY-MM)", value=date.today().strftime("%Y-%m"))
            skill  = st.selectbox("역량", SKILL_OPTIONS)
            score  = st.slider("현재 점수 (0-100)", 0, 100, 30)

        with col2:
            activity = st.text_area(
                "이번 달 학습/활동 내용",
                placeholder="예: 통계 수업에서 선형 회귀 모델 학습\n    C++ 기말 프로젝트 완수",
                height=100,
            )
            evidence = st.text_input(
                "증거 (선택)",
                placeholder="GitHub 링크, 프로젝트명, 수료증 등",
            )

        submitted = st.form_submit_button("💾 저장", type="primary", use_container_width=True)

    if submitted:
        if not activity.strip():
            st.error("활동 내용을 입력해주세요")
        else:
            new_row = pd.DataFrame([{
                "month": month, "skill": skill,
                "score": score, "activity": activity.strip(),
                "evidence": evidence.strip(),
            }])
            if PERSONAL_CSV.exists():
                existing = pd.read_csv(PERSONAL_CSV)
                combined = pd.concat([existing, new_row], ignore_index=True)
            else:
                PERSONAL_CSV.parent.mkdir(exist_ok=True)
                combined = new_row

            combined.to_csv(PERSONAL_CSV, index=False)
            st.success(f"✅ [{skill}] {score}점 기록 완료!")
            st.cache_data.clear()

    # 현재까지 기록
    personal = load_personal()
    if not personal.empty:
        st.markdown('<div class="section-header">지금까지 기록</div>', unsafe_allow_html=True)
        st.dataframe(
            personal.sort_values(["month","skill"], ascending=[False,True]),
            use_container_width=True, hide_index=True,
        )
        st.caption(f"총 {len(personal)}개 기록 · {personal['skill'].nunique()}개 역량 추적 중")

# 🔍 UXR Career Tracker

> UX 리서처 취업 시장을 데이터로 추적하는 나만의 커리어 시스템
> **지금 시작 → 2-3년 후 독보적인 포트폴리오**

---

## 📁 파일 구조

```
uxr-tracker/
├── collect.py              ← 1단계: 데이터 수집기
├── app.py                  ← 3단계: Streamlit 웹 대시보드
├── requirements.txt        ← 설치할 라이브러리 목록
├── .streamlit/
│   └── secrets.toml        ← API 키 (GitHub에 올리지 말 것!)
├── .github/
│   └── workflows/
│       └── daily_collect.yml  ← 2단계: 매일 자동 수집 설정
└── data/                   ← 수집된 데이터 저장 폴더
    ├── market.csv          ← 시장 데이터 (자동 생성)
    └── personal.csv        ← 내 성장 기록 (앱에서 입력)
```

---

## 🚀 시작하기 (3단계)

### 1단계 — 로컬에서 먼저 테스트

```bash
# 라이브러리 설치
pip install -r requirements.txt

# API 키 설정 (터미널에서)
export ANTHROPIC_API_KEY=sk-ant-여기에-키-입력

# 수집 한 번 실행해보기
python collect.py

# 대시보드 실행
streamlit run app.py
# → 브라우저가 자동으로 열립니다 (http://localhost:8501)
```

---

### 2단계 — GitHub에 올리기

```bash
# 저장소 초기화 (처음 한 번만)
git init
git add .
git commit -m "첫 커밋: UXR Career Tracker"

# GitHub에서 새 저장소 만들고 연결
git remote add origin https://github.com/채희님아이디/uxr-tracker.git
git push -u origin main
```

> ⚠️ `.gitignore` 덕분에 `secrets.toml` 은 자동으로 제외됩니다

---

### 3단계 — 자동화 설정

**GitHub Actions (매일 자동 수집):**

1. GitHub 저장소 → `Settings` → `Secrets and variables` → `Actions`
2. `New repository secret` 클릭
3. Name: `ANTHROPIC_API_KEY`, Value: `sk-ant-...` 입력
4. 완료! 이제 매일 오전 9시에 자동 수집됩니다.

수동 실행: `Actions` 탭 → `Daily UXR Data Collect` → `Run workflow`

---

**Streamlit Cloud (무료 배포):**

1. [share.streamlit.io](https://share.streamlit.io) 접속 → GitHub 로그인
2. `New app` → 내 저장소 선택
3. Main file path: `app.py`
4. `Advanced settings` → Secrets 탭에 아래 입력:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-여기에-키-입력"
   ```
5. `Deploy!` → 링크 복사해서 공유 가능!

---

## 📅 채희님 추천 루틴

| 시점 | 할 일 | 시간 |
|------|-------|------|
| **지금** | 1-3단계 완료 | 1시간 |
| **매달 말** | 앱 → 📝 로그 입력 탭에서 역량 기록 | 5분 |
| **격월** | 🤖 AI 갭 분석 실행 | 1분 |
| **2-3년 후** | 면접에서 데이터 포트폴리오 공개 | 🎯 |

---

## 💡 주가 예측 프로젝트와 연결하기

나중에 `app.py` 에 페이지를 추가하면 됩니다:

```python
# app.py 상단 page 라디오에 추가
page = st.radio("페이지", [
    "📊 시장 트렌드",
    "📈 내 성장 기록",
    "🤖 AI 갭 분석",
    "📝 로그 입력",
    "📉 주가 예측 모델",  # ← 이것만 추가!
])
```

하나의 Streamlit 앱이 **채희님의 전체 포트폴리오 사이트**가 됩니다.

---

## ❓ 자주 하는 실수

| 문제 | 해결 |
|------|------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` 다시 실행 |
| `ANTHROPIC_API_KEY not set` | `export ANTHROPIC_API_KEY=sk-ant-...` 실행 |
| GitHub Actions 실패 | Secrets에 API 키가 등록되어 있는지 확인 |
| Streamlit에서 데이터 안 보임 | `data/market.csv` 가 저장소에 있는지 확인 |

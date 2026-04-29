"""
collect.py  ── 1단계: 데이터 수집기
────────────────────────────────────
매일 자동 실행(GitHub Actions)되어
UX 리서처 채용 공고 키워드 + 뉴스를 수집 → data/market.csv 에 추가 저장

실행:  python collect.py
"""

import csv
import json
import os
import re
import time
from datetime import date, datetime
from pathlib import Path

import anthropic
import feedparser
import requests
from bs4 import BeautifulSoup


# ── 설정 ──────────────────────────────────────────────────────────────────────
DATA_DIR  = Path("data")
MARKET_CSV = DATA_DIR / "market.csv"
DATA_DIR.mkdir(exist_ok=True)

# 추적할 UX 리서처 핵심 키워드
TRACK_KEYWORDS = [
    "사용자 인터뷰", "심층 인터뷰", "사용성 테스트", "다이어리 스터디",
    "정성조사", "정량조사", "A/B 테스트", "설문조사",
    "Figma", "Dovetail", "UserTesting",
    "Python", "SQL", "데이터 분석", "통계",
    "리서치 거버넌스", "리서치 오퍼레이션", "리서치 로드맵",
    "생성형 AI", "LLM", "AI 경험",
    "시니어", "리드", "5년 이상", "7년 이상",
    "프로덕트 전략", "스테이크홀더",
]

CSV_FIELDS = [
    "date", "week", "source", "title", "company",
    "keywords_found", "keyword_count",
    "hiring_mode", "raw_snippet",
]


# ── Google News RSS 수집 ──────────────────────────────────────────────────────

def fetch_news(query: str, max_items: int = 8) -> list[dict]:
    """Google News RSS에서 기사 목록 가져오기"""
    url = (
        "https://news.google.com/rss/search"
        f"?q={requests.utils.quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
    )
    results = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:max_items]:
            snippet = BeautifulSoup(
                entry.get("summary", ""), "html.parser"
            ).get_text()[:400]
            results.append({
                "source": "Google News",
                "title":  entry.get("title", ""),
                "snippet": snippet,
                "url":    entry.get("link", ""),
            })
            time.sleep(0.1)
    except Exception as e:
        print(f"  ⚠️  뉴스 수집 오류 ({query}): {e}")
    return results


# ── 키워드 추출 ───────────────────────────────────────────────────────────────

def extract_keywords(text: str) -> list[str]:
    found = []
    t = text.lower()
    for kw in TRACK_KEYWORDS:
        if kw.lower() in t or kw in text:
            found.append(kw)
    return list(set(found))


# ── Claude로 채용 모드 추론 ───────────────────────────────────────────────────

def infer_hiring_mode(text: str, client: anthropic.Anthropic) -> str:
    """텍스트에서 BUILD / MAINTAIN / SCALE_UP 추론 (짧은 호출)"""
    sys = "채용 공고 분석가. 텍스트를 보고 BUILD, MAINTAIN, SCALE_UP 셋 중 하나만 답하세요. 다른 말은 하지 마세요."
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",   # 빠르고 저렴한 모델
            max_tokens=10,
            system=sys,
            messages=[{"role": "user", "content": text[:800]}],
        )
        return msg.content[0].text.strip()
    except Exception:
        return "UNKNOWN"


# ── CSV 저장 ──────────────────────────────────────────────────────────────────

def append_to_csv(rows: list[dict]):
    is_new = not MARKET_CSV.exists()
    with open(MARKET_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if is_new:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})
    print(f"  → {MARKET_CSV} 에 {len(rows)}행 추가 (총 누적)")


# ── 메인 수집 로직 ────────────────────────────────────────────────────────────

def run():
    today    = date.today().isoformat()           # "2025-04-29"
    week     = date.today().strftime("%Y-W%W")    # "2025-W18"
    now_time = datetime.now().strftime("%H:%M")

    print(f"\n{'='*50}")
    print(f"  UXR Tracker — 수집 시작  {today} {now_time}")
    print(f"{'='*50}\n")

    # Claude 클라이언트 (ANTHROPIC_API_KEY 환경변수 자동 사용)
    client = anthropic.Anthropic()

    new_rows: list[dict] = []

    queries = [
        "UX 리서처 채용",
        "UX Researcher 공고",
        "사용자 리서치 채용 2025",
        "원티드 UX 리서처",
        "사람인 UX 리서처",
    ]

    for q in queries:
        print(f"[수집] {q}")
        articles = fetch_news(q, max_items=5)

        for art in articles:
            combined = art["title"] + " " + art["snippet"]
            kws      = extract_keywords(combined)
            mode     = infer_hiring_mode(combined, client) if kws else "UNKNOWN"

            new_rows.append({
                "date":          today,
                "week":          week,
                "source":        art["source"],
                "title":         art["title"][:120],
                "company":       "",             # 공고 직접 파싱 시 채움
                "keywords_found": "|".join(kws),
                "keyword_count": len(kws),
                "hiring_mode":   mode,
                "raw_snippet":   art["snippet"][:300],
            })
            print(f"  ✓ {art['title'][:50]}... ({len(kws)}개 키워드, {mode})")
            time.sleep(0.3)

        time.sleep(0.5)

    if new_rows:
        append_to_csv(new_rows)
        print(f"\n✅ 오늘 {len(new_rows)}건 수집 완료")
    else:
        print("\n⚠️  수집된 데이터 없음")

    # 요약 로그
    log_path = DATA_DIR / "collect_log.txt"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{today} {now_time} — {len(new_rows)}건 수집\n")

    print(f"\n{'='*50}\n")


if __name__ == "__main__":
    run()

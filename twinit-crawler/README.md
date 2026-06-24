# Twinit 리서치 크롤러

Twinit 공식 웹사이트의 공개 페이지를 수집해 경쟁사 기능 분석 데이터셋을 생성하는 도구다.
발표·기획서에서 "트위닛 vs 우리 프로젝트" 비교 분석에 사용한다.

---

## 실행 방법

```bash
# 의존성 설치 (최초 1회)
npm install
npx playwright install chromium

# 1단계: 크롤링
node src/crawl.js

# 2단계: feature matrix 생성
node src/feature-matrix.js

# 한 번에 실행
npm run all
```

---

## 수집 범위

| 페이지 | URL | 우선순위 |
| --- | --- | --- |
| Real Texture AR Simulation | /real-texture-ar-simulation-ai-agent | 1 |
| Facial Zone Makeup Lab | /facial-zone-makeup-lab-ai-agent | 2 |
| AI Personal Color Profiling | /ai-personal-color-profiling-ai-agent | 3 |
| PBV Identity Analysis Engine | /pbv-identity-analysis-engine-ai-agent | 4 |
| Skin Profiling | /skin-profiling-ai-agent | 5 |
| Case Study (Blog) | /blog + 개별 글 | 6 |
| Homepage | / | 7 |
| Customized Skincare Tutorial | /customized-skincare-tutorial-ai-agent | - |
| Aging Preview | /aging-preview-ai-agent | - |
| Contact Us | /contact-us | - |

sitemap(`pages-sitemap.xml`, `blog-posts-sitemap.xml`)을 자동 파싱해 개별 도입사례 글까지 포함한다.

---

## 결과물 구조

```
data/
  raw_html/          — 렌더링된 HTML 원본
  screenshots/       — full-page PNG 스크린샷
  markdown/          — 분석용 Markdown 본문
  jsonl/
    pages.jsonl      — 페이지별 메타데이터 (1행 1페이지)
    links.jsonl      — 내부/외부 링크 목록
    images.jsonl     — 이미지 메타데이터
    errors.jsonl     — 에러 로그
  csv/
    feature_matrix.csv   — 기능 비교 (수치 자동 채움, 나머지는 아래 참고)
    page_inventory.csv   — 전체 페이지 인벤토리
  logs/
    crawl.log        — 실행 로그
  research/          — 관련 학술 논문 (수동 추가)
```

### pages.jsonl 스키마

```json
{
  "url": "https://www.twinit.ai/real-texture-ar-simulation-ai-agent",
  "slug": "real-texture-ar-simulation-ai-agent",
  "title": "Real Texture AR Simulation 리얼 텍스처 AR 시뮬레이션",
  "crawled_at": "2026-06-24T00:00:00.000Z",
  "language": "ko",
  "depth": 0,
  "status": 200,
  "metrics": ["+14%", "×3"],
  "image_count": 12,
  "content_hash": "sha256..."
}
```

---

## feature_matrix.csv 작성 방법 (2단계)

| 단계 | 담당 | 내용 |
| --- | --- | --- |
| 6-A 기계 | `feature-matrix.js` | 빈 골격 생성 + 수치 지표(`+14%`, `×3`) 자동 추출 |
| 6-B 해석 | LLM 또는 사람 | `feature`, `input_data`, `ai_claim`, `ar_claim`, `relevance_to_our_project` 채움 |

`relevance_to_our_project` 같은 주관 컬럼은 사람이 검수 후 최종 확정한다.

---

## 관련 학술 연구 (§16)

트위닛 주장과 대응되는 피어리뷰 논문 4편이 `TWINIT_DATA_PLAN.md` §16.2에 정리되어 있다.
수집 결과를 `data/research/papers.jsonl`에 추가한다.

| 트위닛 주장 | 논문 |
| --- | --- |
| 리얼 텍스처 AR (실시간, 모바일) | Kips et al. 2022, CGF 41(2). DOI:10.1111/cgf.14456 |
| 색 재현 정확도 | Kim & Lee 2020, Color Res. Appl. 45(6). DOI:10.1002/col.22549 |
| 피부 톤·질감 기반 색 재현 | Jang et al. 2013, ETRI J. 35(6). DOI:10.4218/etrij.13.2013.0079 |
| 메이크업 추천·전이 | Scherbaum et al. 2011, CGF 30(2). DOI:10.1111/j.1467-8659.2011.01874.x |

---

## 주의사항

- **robots.txt 준수**: `?lightbox=`, `/_partials*`, `/pro-gallery-webapp/*` 경로는 수집하지 않는다.
- **외부 링크 follow 금지**: 외부 뉴스·도메인은 링크 정보만 기록하고 본문은 수집하지 않는다.
- **재현 가능**: 재실행 시 동일 slug 파일을 덮어쓴다. jsonl은 append 방식이므로 재실행 전 `data/jsonl/*.jsonl`을 삭제하면 중복이 없다.
- **저작권**: 수집 원본(HTML·이미지)은 팀 내부 연구용으로만 사용하고 공개 재배포하지 않는다.

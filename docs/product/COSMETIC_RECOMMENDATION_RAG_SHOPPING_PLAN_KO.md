# 화장품 추천 RAG + 쇼핑 링크 기능 전체 계획

작성일: 2026-06-29 KST

상태: 제품/기술 계획. 현재 active E7 AR 구현 계약을 대체하지 않는다.

## 0. 한 줄 결론

화장품 추천 기능은 `AI가 웹을 마음대로 뒤져서 추천하는 기능`이 아니라, **정규화된 제품 catalog + Bedrock RAG + live 쇼핑 API + 추천 에이전트**를 결합한 제품 모듈로 만든다.

가장 중요한 구조는 아래다.

```txt
느리게 변하는 제품 지식
-> 수집/정규화
-> Product Catalog DB
-> Bedrock Knowledge Base / vector index

자주 변하는 가격/판매 링크
-> Naver Shopping API / 허가된 쇼핑 API
-> 요청 시 live 확인

추천 판단
-> catalog filter + 색상/질감 matching + RAG retrieval + rerank
-> Bedrock agent가 설명과 링크 카드 생성
```

즉 RAG는 `제품 지식과 추천 근거`를 찾고, 구매 링크/가격/판매처는 RAG에서 꺼내지 않고 쇼핑 API로 확인한다.

## 1. 배경

기획서의 핵심 방향은 아래 루프다.

```txt
얼굴/취향 분석
-> 메이크업 룩 / MakeupRecipe 추천
-> AR 적용
-> 사용자 편집
-> 저장
-> 실제 화장 피드백
-> 다음 추천 개선
-> 추천 recipe와 유사한 실제 제품 연결
```

이번 문서는 그중 `추천 recipe와 유사한 실제 화장품 제품을 찾고 쇼핑 링크까지 제공하는 기능`을 별도 모듈로 정리한다.

현재 repo의 active 구현은 `lip / blush / brow / eyeliner` region Generate와 RN/Unity AR 적용 준비다. 이 추천 모듈은 바로 active AR 구현을 변경하는 지시가 아니라, 이후 backend/AI scope가 명시적으로 열릴 때 사용할 제품 계획이다.

## 2. 제품 목표

사용자가 원하는 결과는 단순한 상품 검색이 아니다.

사용자는 이렇게 묻는다.

```txt
내 얼굴에 지금 만든 데일리 립 색이랑 비슷한 올리브영/네이버쇼핑 제품 찾아줘.
쿨톤이고 너무 진한 건 싫어. 2만원 이하로.
AR에서 저장한 블러셔 느낌이랑 비슷한 제품 추천해줘.
면접용으로 단정하고 자연스러운 메이크업 제품 조합 알려줘.
```

따라서 추천 기능의 목표는 네 가지다.

1. AR/AI가 만든 `MakeupRecipe`를 실제 제품 후보로 연결한다.
2. 사용자의 취향, 피부 타입, 예산, 구매 채널 제약을 반영한다.
3. 추천 이유와 근거를 보여준다.
4. 현재 구매 가능한 링크는 live API로 확인한다.

## 3. 비목표

초기 구현에서 아래는 하지 않는다.

```txt
- 허가되지 않은 쇼핑몰 대량 HTML 크롤링
- 가격/재고/할인 정보를 RAG에 장기 저장
- AI가 catalog 밖 제품을 상상해서 추천
- 얼굴 원본 사진을 추천 서버에 기본 업로드
- 제품별 실제 발색을 완전 재현한다고 주장
- 대규모 사용자 후기 기반 협업 필터링을 처음부터 구현
- 의학적/피부질환 치료성 추천
```

민감성 피부, 알러지, 트러블 관련 문구는 `의학 조언`이 아니라 `성분 주의/사용자 확인 필요`로 제한한다.

## 4. 핵심 원칙

### 4.1 API 우선, 크롤링 최소화

네이버쇼핑처럼 공식 API가 있으면 HTML 크롤링하지 않는다.

```txt
상품 발견 / 가격 / 판매처 / 구매 링크
-> Naver Shopping API

정적인 제품 설명 / 색조 / 질감 / 성분 / 호수
-> 공식 API, 제휴 feed, 브랜드 제공 데이터, 수동 curated catalog, 허용된 정적 수집

HTML 직접 크롤링
-> 공식 API/feed가 없고, 약관/robots/rate limit/저장 범위가 확인된 경우의 마지막 수단
```

### 4.2 RAG는 지식, API는 최신성

RAG에 넣을 것:

```txt
브랜드명
제품명
제품 라인 설명
색상명/호수
공식 색조 설명
질감/finish
커버력
성분 정보
사용감 키워드
리뷰 요약
추천/비추천 맥락
source URL
수집 시점
```

RAG에 넣지 않거나 TTL을 짧게 둘 것:

```txt
현재 가격
재고
할인율
배송비
랭킹
광고 순위
품절 여부
```

이 정보는 사용자가 추천 결과를 볼 때 live 쇼핑 API로 확인한다.

### 4.3 AI는 최종 심판이 아니라 설명자와 조율자

추천 결정은 아래 계층을 거친다.

```txt
1. DB filter
2. 색상/질감 수치 matching
3. vector retrieval
4. rerank
5. live offer check
6. agent explanation
```

AI 모델이 직접 "아무 제품이나" 추천하지 않는다. 없는 제품, 지원하지 않는 texture, 확인되지 않은 구매 링크를 생성하면 실패다.

## 5. 전체 서비스 흐름

### 5.1 첫 추천 흐름

```txt
1. 사용자가 AR에서 makeup look 또는 특정 부위 recipe를 저장한다.
2. 사용자가 "비슷한 제품 찾기"를 누른다.
3. 앱이 추천 요청에 아래 정보를 담아 backend로 보낸다.
   - MakeupRecipe
   - 사용자 취향/피부 타입/피부톤 요약
   - 예산
   - 구매 채널 선호
   - 제외 조건
4. backend가 조건을 구조화한다.
5. Product Catalog DB에서 1차 후보를 filter한다.
6. 색상/질감 matching으로 후보를 좁힌다.
7. Bedrock Knowledge Base에서 제품 설명/리뷰 요약 근거를 retrieve한다.
8. rerank로 질문과 후보의 관련도를 재정렬한다.
9. Naver Shopping API로 현재 구매 링크, 가격, 판매처를 확인한다.
10. agent가 최종 추천 카드 3-5개와 이유를 만든다.
11. 앱이 추천 카드, 근거, 링크, 주의사항을 보여준다.
12. 사용자의 클릭/저장/숨김/피드백을 기록한다.
```

### 5.2 대화형 흐름

에이전트는 바로 추천하지 않고 필요한 정보가 빠졌을 때만 짧게 되묻는다.

```txt
사용자: 이 립이랑 비슷한 제품 추천해줘.
Agent: 예산이나 선호 finish가 있나요? 없으면 올리브영/네이버쇼핑에서 자연스러운 데일리 기준으로 찾을게요.
사용자: 2만원 이하, 너무 매트하지 않게.
Agent: 후보 5개를 찾고 현재 구매 링크를 확인한다.
```

질문은 최대 1-2개까지만 한다. 모르는 값은 `unknown`으로 두고, 추천 결과에 제한을 명시한다.

### 5.3 AR 연동 흐름

AR에서 생성된 recipe는 제품 추천의 가장 강한 입력이다.

```json
{
  "recipeId": "look-20260629-001",
  "lookGoal": "daily_natural",
  "layers": [
    {
      "region": "lip",
      "colorHex": "#D94B74",
      "finish": "soft_gloss",
      "opacity": 0.62,
      "coverage": 0.72,
      "texture": "tint_gloss",
      "userAdjustment": {
        "cornerReach": 0.1,
        "verticalOffset": -0.05
      }
    }
  ]
}
```

추천 시스템은 이 recipe를 실제 제품 속성으로 변환한다.

```txt
colorHex / Lab color -> 색조 근접도
finish -> 제품 finish 필터
texture -> tint / balm / lipstick / gloss 분류
opacity / coverage -> 발색 강도 후보
lookGoal -> 분위기/rerank query
```

## 6. 데이터 설계

### 6.1 ProductCatalog

제품의 정답 원본은 vector store가 아니라 DB다.

```ts
type ProductCatalogItem = {
  productId: string;
  sourceProductId?: string;
  sourceType: "manual" | "naver_api" | "brand_feed" | "partner_feed" | "allowed_static_collect";
  dataPermission: "owned" | "api_allowed" | "partner_allowed" | "manual_reviewed" | "unknown_blocked";
  brand: string;
  productName: string;
  variantName?: string;
  category: "lip" | "blush" | "eyeliner" | "eyeshadow" | "base" | "contour" | "highlighter" | "other";
  subcategory?: string;
  shadeName?: string;
  shadeCode?: string;
  colorHex?: string;
  colorLab?: {
    l: number;
    a: number;
    b: number;
  };
  undertone?: "warm" | "cool" | "neutral" | "unknown";
  finish?: "matte" | "velvet" | "gloss" | "dewy" | "shimmer" | "glitter" | "satin" | "unknown";
  texture?: "tint" | "balm" | "cream" | "powder" | "pencil" | "liquid" | "stick" | "unknown";
  coverage?: "sheer" | "medium" | "full" | "buildable" | "unknown";
  skinTypeTags?: string[];
  ingredientHighlights?: string[];
  cautionTags?: string[];
  officialDescription?: string;
  reviewSummary?: string;
  sourceUrls: string[];
  createdAt: string;
  updatedAt: string;
  lastKnowledgeIndexedAt?: string;
};
```

### 6.2 ProductKnowledgeDocument

Bedrock Knowledge Base에는 DB row 자체를 그대로 넣기보다 검색용 문서로 변환해 넣는다.

```ts
type ProductKnowledgeDocument = {
  docId: string;
  productId: string;
  locale: "ko-KR";
  title: string;
  text: string;
  metadata: {
    brand: string;
    category: string;
    finish?: string;
    texture?: string;
    undertone?: string;
    shadeName?: string;
    sourceType: string;
    dataPermission: string;
    updatedAt: string;
  };
};
```

예시 text:

```txt
브랜드: romand
제품: Glasting Color Gloss
호수: 01 Peony Ballet
카테고리: lip gloss
색조: 밝은 핑크, 쿨톤, 맑은 채도
질감: 투명 광택, 글로시, 가벼운 발림
추천 맥락: 데일리, 쿨톤, 맑은 립, 진한 매트 립을 싫어하는 사용자
주의: 고발색 매트 제형을 찾는 사용자에게는 부적합
```

### 6.3 LiveOffer

구매 링크는 별도 live offer로 둔다.

```ts
type LiveOffer = {
  offerId: string;
  productId?: string;
  source: "naver_shopping" | "oliveyoung_partner" | "brand_store" | "other_allowed_api";
  sourceProductId?: string;
  title: string;
  link: string;
  image?: string;
  mallName?: string;
  lprice?: number;
  hprice?: number;
  brand?: string;
  maker?: string;
  categoryPath?: string[];
  productType?: number;
  fetchedAt: string;
  ttlSeconds: number;
};
```

`LiveOffer`는 RAG의 근거가 아니라 현재 구매 가능성 확인이다.

## 7. 수집 설계

### 7.1 수집 대상

수집 대상은 세 그룹으로 나눈다.

```txt
Group A: 공식/제휴 데이터
  - 브랜드 feed
  - 파트너 product feed
  - 공식 API
  - 사용 허가가 확인된 데이터

Group B: 쇼핑 검색 API
  - Naver Shopping API
  - 현재 가격/판매처/링크 확인
  - catalog 후보 발견 보조

Group C: 수동 curated catalog
  - 초기 300-1000개 핵심 색조 제품
  - 팀이 직접 shade/finish/texture 정규화
  - 품질 기준의 기준 데이터
```

Group C는 반드시 필요하다. 자동 수집만으로는 `쿨톤`, `뮤트`, `맑은`, `벨벳`, `속광`, `물먹`, `채도 낮음` 같은 뷰티 표현이 안정적으로 정규화되지 않는다.

### 7.2 네이버 쇼핑 API 역할

전제: 네이버 쇼핑 API는 현재 사용 가능한 상태다.

Naver Shopping API는 아래 역할로 쓴다.

```txt
- 제품 후보 발견
- 현재 구매 링크 확인
- 최저가/판매처/이미지 확인
- productId 기반 중복 정리 보조
- 네이버페이 필터나 중고/렌탈/해외직구 제외 같은 검색 조건 적용
```

제한:

```txt
- 색조/질감/finish 정답으로 쓰지 않는다.
- 리뷰 요약 원천으로 쓰지 않는다.
- 가격/판매처를 장기 RAG 지식으로 저장하지 않는다.
- 검색 결과 title만 믿고 shade를 확정하지 않는다.
```

### 7.3 정적 정보 수집 정책

변하지 않는 정보도 무조건 크롤링하지 않는다.

허용 순서:

```txt
1. 공식 API / 제휴 feed
2. 브랜드가 공개 배포한 제품 자료
3. 수동 curated 입력
4. 허용 범위가 확인된 정적 페이지 수집
```

HTML 수집이 필요한 경우 저장 필드는 제한한다.

```txt
허용 후보:
- 제품명
- 브랜드명
- 호수명
- 공식 설명 일부 요약
- 성분 목록
- source URL
- 수집 시점

비허용 또는 별도 검토:
- 상세 이미지 원본 저장
- 리뷰 전문 대량 저장
- 가격/할인/재고 장기 저장
- 약관상 재사용 금지된 콘텐츠
```

## 8. 추천 알고리즘

### 8.1 전체 ranking pipeline

```txt
Input
  userProfile
  MakeupRecipe
  userQuery
  constraints

Step 1. Query understanding
  category, finish, price, tone, mood, excluded brands, skin constraints 추출

Step 2. Hard filter
  category, price range, availability source, blocked ingredients, excluded brands

Step 3. Color matching
  recipe colorHex/Lab와 product colorLab의 Delta E 계산

Step 4. Texture / finish matching
  finish, texture, coverage, opacity goal 비교

Step 5. RAG retrieval
  제품 설명/리뷰 요약/사용 맥락 문서 검색

Step 6. Rerank
  사용자 질의와 후보 문서 관련도 재정렬

Step 7. Live offer check
  Naver Shopping API로 현재 링크/가격/판매처 확인

Step 8. Final explanation
  agent가 추천 이유, tradeoff, 주의사항, 링크 카드 생성
```

### 8.2 점수식 초안

초기 점수는 rule 기반으로 둔다. 이후 feedback data가 쌓이면 learning-to-rank를 검토한다.

```txt
finalScore =
  0.25 * colorScore
  + 0.20 * finishTextureScore
  + 0.15 * userPreferenceScore
  + 0.15 * ragRelevanceScore
  + 0.10 * liveOfferScore
  + 0.10 * popularityOrReviewScore
  + 0.05 * diversityScore
```

차단 조건:

```txt
- dataPermission이 unknown_blocked
- category mismatch
- 사용자가 제외한 브랜드
- live offer 없음, 단 사용자가 "단종/비슷한 제품도 보기"를 선택한 경우 제외
- 알러지/민감성 warning이 사용자 hard constraint와 충돌
- catalog에 없는 제품을 AI가 새로 생성
```

### 8.3 추천 카드

최종 UI card는 아래 필드를 가진다.

```ts
type RecommendationCard = {
  recommendationId: string;
  productId: string;
  displayName: string;
  brand: string;
  shadeName?: string;
  image?: string;
  priceText?: string;
  mallName?: string;
  shoppingUrl?: string;
  matchSummary: string;
  reasons: string[];
  tradeoffs: string[];
  sourceEvidence: {
    catalogFields: string[];
    ragDocIds: string[];
    liveOfferFetchedAt?: string;
  };
  confidence: "high" | "medium" | "low";
};
```

사용자에게는 과장 없이 보여준다.

```txt
이 제품이 맞는 이유:
- AR 립 색상과 색상군이 가깝습니다.
- 사용자가 원한 글로시한 마무리에 가깝습니다.
- 너무 진한 매트 립을 피하려는 조건과 맞습니다.

확인 필요:
- 실제 발색은 입술 원래 색과 조명에 따라 달라질 수 있습니다.
- 현재 링크/가격은 네이버쇼핑 API 조회 시점 기준입니다.
```

## 9. AI/Bedrock 구성

### 9.1 권장 모델 조합

```txt
Embedding:
  Cohere Embed v4
  modelId: cohere.embed-v4:0
  이유: text/image/mixed content embedding을 한 모델에서 처리할 수 있어 제품 설명과 swatch/이미지 검색 확장에 유리함.

Rerank:
  Cohere Rerank 3.5
  이유: vector retrieval 후보를 사용자 질의와 더 맞게 재정렬해 비용/latency를 줄이고 관련도를 높임.

Main recommendation agent:
  Claude Sonnet 4.5 on Bedrock
  modelId: anthropic.claude-sonnet-4-5-20250929-v1:0
  이유: 긴 context, tool orchestration, 추천 이유 생성, 제약 조건 정리에 적합함.

Bulk extraction / normalization:
  Claude Haiku 4.5 on Bedrock
  modelId: anthropic.claude-haiku-4-5-20251001-v1:0
  이유: 제품 설명 정규화, 리뷰 요약, 태그 생성 같은 대량 처리에 비용/속도 면에서 적합함.
```

모델은 고정 상수가 아니라 운영 config로 둔다.

```ts
type AiModelConfig = {
  embeddingModelId: string;
  rerankModelId: string;
  recommendationModelId: string;
  extractionModelId: string;
  region: string;
  updatedAt: string;
};
```

### 9.2 Bedrock Knowledge Base

Knowledge Base는 제품 지식 검색에만 사용한다.

용도:

```txt
- 제품 설명 검색
- 유사 질감/무드 검색
- 추천 이유 근거 검색
- citation/source doc 추적
- agent workflow 안에서 knowledge retrieval
```

비용/품질 관리:

```txt
- category별 metadata filter 필수
- topK는 20-50에서 시작
- rerank 후 최종 5-10개만 agent context로 전달
- source URL과 indexedAt을 응답 근거에 포함
- retrieval 결과가 약하면 추천하지 않고 "후보 부족" 처리
```

### 9.3 Agent tool 설계

Agent는 직접 DB를 임의 조회하지 않고, 제한된 tool만 호출한다.

```ts
type RecommendationTools = {
  getUserPreferenceSummary(userId: string): Promise<UserPreferenceSummary>;
  searchCatalog(input: CatalogSearchInput): Promise<CatalogCandidate[]>;
  retrieveProductKnowledge(input: KnowledgeQueryInput): Promise<KnowledgeHit[]>;
  rerankCandidates(input: RerankInput): Promise<RerankedCandidate[]>;
  checkNaverShoppingOffers(input: OfferSearchInput): Promise<LiveOffer[]>;
  buildRecommendationCards(input: CardBuildInput): Promise<RecommendationCard[]>;
  recordRecommendationFeedback(input: FeedbackInput): Promise<void>;
};
```

Tool guardrails:

```txt
- tool은 productId/sourceId 기반으로만 조회한다.
- live offer URL은 API 응답 또는 허용된 partner source에서만 온다.
- agent가 URL을 직접 생성하지 않는다.
- agent가 catalog에 없는 제품명을 추천하지 않는다.
- source evidence 없는 이유는 "추론"으로 라벨링한다.
```

## 10. Backend/API 설계

### 10.1 주요 API

```txt
POST /recommendations/products
  목적: recipe/user query 기반 제품 추천

GET /recommendations/{recommendationId}
  목적: 추천 결과 재조회

POST /recommendations/{recommendationId}/feedback
  목적: 클릭/저장/숨김/구매 의향/불만 기록

POST /catalog/import/naver-shopping
  목적: 네이버쇼핑 API 기반 후보 발견 및 matching 보조
  주의: admin/internal only

POST /catalog/items
  목적: curated 제품 등록
  주의: admin/internal only

POST /catalog/items/{productId}/index
  목적: ProductKnowledgeDocument 생성 및 KB sync queue 등록
```

### 10.2 추천 요청

```json
{
  "userId": "user_123",
  "source": "ar_recipe",
  "query": "이 립이랑 비슷한 글로시 제품 찾아줘. 2만원 이하.",
  "makeupRecipe": {
    "recipeId": "look-20260629-001",
    "layers": [
      {
        "region": "lip",
        "colorHex": "#D94B74",
        "finish": "soft_gloss",
        "texture": "tint_gloss",
        "opacity": 0.62
      }
    ]
  },
  "constraints": {
    "maxPriceKrw": 20000,
    "preferredStores": ["naver_shopping"],
    "excludeUsed": true,
    "excludeOverseasProxy": true
  }
}
```

### 10.3 추천 응답

```json
{
  "recommendationId": "rec_20260629_001",
  "status": "ready",
  "summary": "AR 립 색상과 가까운 글로시/틴트 계열 제품을 우선 추천했습니다.",
  "cards": [
    {
      "productId": "prod_001",
      "displayName": "Example Brand Gloss Tint 01",
      "brand": "Example Brand",
      "shadeName": "01 Rose",
      "priceText": "18,900원",
      "mallName": "네이버쇼핑",
      "shoppingUrl": "https://...",
      "matchSummary": "색상군과 글로시 finish가 현재 AR 립과 가깝습니다.",
      "reasons": [
        "AR recipe의 rose 계열 색상과 유사합니다.",
        "사용자가 요청한 너무 매트하지 않은 finish와 맞습니다."
      ],
      "tradeoffs": [
        "실제 발색은 입술 원래 색과 조명에 따라 달라질 수 있습니다."
      ],
      "confidence": "medium"
    }
  ],
  "limitations": [
    "가격과 링크는 조회 시점 기준입니다.",
    "제품별 실제 발색 완전 재현은 보장하지 않습니다."
  ]
}
```

## 11. Frontend UX

### 11.1 진입점

추천 기능은 아래 위치에서 진입한다.

```txt
1. AR look 저장 완료 화면
2. 특정 부위 조정 화면
3. 저장한 MakeupRecipe 상세 화면
4. 온보딩 취향 기반 추천 화면
5. 실제 화장 피드백 후 "다음 제품 추천" 화면
```

### 11.2 화면 구성

추천 결과 화면:

```txt
상단:
  추천 기준 요약
  예: "AR 립 색상 + 글로시 + 2만원 이하"

중단:
  추천 제품 카드 3-5개
  제품 이미지, 브랜드, 제품명, 호수, 가격, 판매처, 링크 버튼

하단:
  왜 추천했는지
  확인 필요/주의사항
  조건 수정 버튼
  마음에 들어요 / 별로예요 / 숨기기
```

사용자에게 내부 용어를 노출하지 않는다.

```txt
노출하지 않음:
  RAG, embedding, vector, rerank, provider, productId

노출 가능:
  색감이 비슷함
  질감이 비슷함
  지금 구매 가능
  가격 확인됨
  실제 발색은 다를 수 있음
```

## 12. Admin/운영 도구

Admin에는 제품 추천 품질을 관리하는 화면이 필요하다.

```txt
Product Catalog
  - 제품 목록
  - 브랜드/카테고리/호수/색상/질감 수정
  - dataPermission 확인
  - source URL 확인

Ingestion Jobs
  - 네이버쇼핑 API query 실행 이력
  - partner feed import 이력
  - 실패/중복/차단 항목

Knowledge Index
  - KB sync 상태
  - 문서 chunk 수
  - indexedAt
  - retrieval preview

Recommendation QA
  - 고정 eval query 결과
  - 추천 카드 diff
  - hallucination 여부
  - live offer 실패율

Feedback
  - 클릭
  - 저장
  - 숨김
  - 사용자가 별로라고 한 이유
  - 추천 정확도 피드백
```

## 13. 개인정보/보안

### 13.1 얼굴 데이터 경계

추천 서버에는 원본 얼굴 프레임을 기본 전송하지 않는다.

추천에 전달 가능한 값:

```txt
- MakeupRecipe
- 낮은 해상도의 얼굴 feature summary
- 피부톤/피부 타입 설문값
- 사용자가 직접 입력한 취향
- 저장/수정 이력 요약
```

민감한 값:

```txt
- 원본 얼굴 사진
- ARFace mesh 전체
- raw camera frame
- 세밀한 landmark 전체
```

민감한 값은 별도 동의, 목적, 보관 기간, 삭제 기능이 정해지기 전에는 추천 API 입력으로 쓰지 않는다.

### 13.2 API key와 로그

```txt
- Naver API key는 client 앱에 넣지 않는다.
- Bedrock credential은 backend/IAM 역할 또는 secret manager로 관리한다.
- 추천 로그에는 원본 얼굴 이미지, raw frame, API secret, full shopping response를 남기지 않는다.
- 사용자의 health/skin concern은 민감정보에 준해 최소 저장한다.
```

## 14. 개발 단계

### Phase 0. 계약 고정

목표:

```txt
- ProductCatalog schema
- ProductKnowledgeDocument schema
- RecommendationRequest/Response schema
- MakeupRecipe -> product matching field map
- Naver Shopping API 사용 정책
- dataPermission 정책
```

완료 기준:

```txt
- 20개 샘플 제품을 수동 catalog로 등록 가능
- 5개 샘플 recipe를 추천 request로 표현 가능
- 추천 응답 JSON schema validation 통과
```

### Phase 1. 수동 catalog + local retrieval baseline

목표:

```txt
- 100-300개 핵심 색조 제품 curated catalog 구축
- 색상/질감/finish taxonomy 고정
- SQL/JSON 기반 baseline 추천 구현
```

완료 기준:

```txt
- "쿨톤 글로시 립 2만원 이하" 같은 query 20개에 후보 반환
- catalog 밖 제품 추천 0건
- 색상/finish 필터가 deterministic하게 동작
```

### Phase 2. Naver Shopping API 연결

목표:

```txt
- backend에서 Naver Shopping API 호출
- live offer mapping
- 중고/렌탈/구매대행 제외 옵션
- API quota/rate limit/cache 적용
```

완료 기준:

```txt
- catalog product 50개에 대해 live offer 후보 조회
- price/link/mallName 표시
- 실패 시 recommendation card가 "현재 링크 확인 실패"로 graceful degrade
```

### Phase 3. Bedrock Knowledge Base 구축

목표:

```txt
- ProductKnowledgeDocument 생성
- Cohere Embed v4 기반 embedding/index
- category/finish/texture metadata filter
- retrieval smoke test
```

완료 기준:

```txt
- 고정 query 30개에서 관련 제품 문서 topK 반환
- source URL/docId 추적 가능
- stale/unknown permission 문서 제외 가능
```

### Phase 4. Rerank + hybrid ranking

목표:

```txt
- vector retrieval 결과에 rerank 적용
- 색상 Delta E 점수와 RAG relevance 결합
- score breakdown 저장
```

완료 기준:

```txt
- fixed eval set에서 baseline 대비 top3 relevance 개선
- 추천 이유가 score breakdown과 충돌하지 않음
- 결과 latency 목표 초안 충족
```

### Phase 5. Agent orchestration

목표:

```txt
- Bedrock agent 또는 backend-owned agent layer 구현
- searchCatalog / retrieveKnowledge / checkNaverOffer tool 연결
- 최종 카드 설명 생성
- missing constraint 질문 정책 구현
```

완료 기준:

```txt
- agent가 tool 없이 URL/제품을 생성하지 않음
- catalog 없는 제품 추천 0건
- live offer 없는 제품은 링크 버튼 비활성 또는 대체 후보 제공
- 추천 이유에 근거 doc/source가 연결됨
```

### Phase 6. 앱 UX 연결

목표:

```txt
- AR recipe 저장 후 "비슷한 제품 찾기"
- 추천 카드 UI
- 조건 수정
- 저장/숨김/피드백
```

완료 기준:

```txt
- 사용자가 AR look에서 추천 결과까지 끊김 없이 이동
- 추천 결과가 내부 AI 용어 없이 표시됨
- 링크 클릭/저장/숨김 이벤트 기록
```

### Phase 7. Admin/QA

목표:

```txt
- catalog 관리
- ingestion job 관리
- retrieval eval
- 추천 결과 QA
- 피드백 리뷰
```

완료 기준:

```txt
- 운영자가 잘못된 색상/질감 태그 수정 가능
- fixed eval set을 반복 실행 가능
- 추천 품질 regression을 확인 가능
```

## 15. 품질 평가

### 15.1 Fixed eval set

처음부터 고정 평가셋을 만든다.

예시:

```txt
1. 쿨톤 여름, 맑은 핑크 글로시 립, 2만원 이하
2. 웜톤 가을, 채도 낮은 벽돌 립, 매트하지 않게
3. 면접용 자연스러운 블러셔, 너무 붉지 않게
4. 아이라인이 번지는 편, 또렷하지만 과하지 않은 펜슬/리퀴드
5. AR recipe의 #D94B74 립과 비슷한 네이버쇼핑 구매 가능 제품
6. 민감성 피부라 향료/자극 표현이 많은 제품은 제외
7. 촉촉한 립밤 같은 색조, 고발색 제외
8. 글리터 강한 아이섀도우 말고 은은한 쉬머
```

### 15.2 지표

```txt
Retrieval:
  recall@20
  precision@5
  nDCG@10

Recommendation:
  catalog hallucination count = 0
  unsupported texture count = 0
  blocked product leakage = 0
  live offer success rate
  user save/click/hide rate

UX:
  time to recommendation
  condition edit completion
  link click success

Safety:
  raw face upload count = 0 unless explicit consent flow exists
  API secret leak count = 0
  unknown dataPermission recommendation count = 0
```

## 16. 실패 모드와 대응

| 실패 | 원인 | 대응 |
| --- | --- | --- |
| 제품은 추천됐지만 링크가 죽음 | 가격/재고/링크 최신성 문제 | live offer TTL 짧게, 링크 실패 시 재조회 |
| AI가 없는 제품을 추천 | agent 자유 생성 | productId 기반 tool 결과만 카드화 |
| 색은 비슷한데 질감이 다름 | vector relevance 과신 | finish/texture hard filter와 score 가중치 강화 |
| 쇼핑 API 결과가 엉뚱함 | title query 불안정 | brand/product/shade query template과 productId mapping |
| 리뷰 요약이 과장됨 | 리뷰 원문/표본 불명확 | source count, summary confidence, 수동 검수 |
| 사용자 피부 고민에 위험한 표현 | 의료/성분 판단 과장 | "확인 필요" 라벨, 성분 hard claim 금지 |
| RAG 결과가 오래됨 | 제품 리뉴얼/단종 | indexedAt, sourceUpdatedAt, refresh queue |
| 추천 결과가 매번 비슷함 | popularity bias | diversityScore와 사용자 숨김 feedback 반영 |

## 17. 운영 정책

### 17.1 Cache/TTL

```txt
ProductCatalog static fields:
  수동/공식 업데이트 전까지 유지

Knowledge document:
  catalog 업데이트 시 재생성/재색인

Naver Shopping live offer:
  1-24시간 TTL 후보
  가격/재고성 문구는 조회 시점 표시

Recommendation result:
  카드와 근거는 저장 가능
  live offer는 재진입 시 재확인
```

### 17.2 동의와 삭제

```txt
- 추천 개인화 저장 동의
- 피부/취향 정보 저장 동의
- 추천 이력 삭제
- 피드백 이력 삭제
- 얼굴 원본/사진을 쓰는 기능은 별도 동의 전까지 제외
```

## 18. 최종 아키텍처

```txt
Mobile App
  AR MakeupRecipe
  User Preferences
  Recommendation UI
        |
        v
Recommendation Backend
  Request normalization
  Catalog filter
  Color/texture matcher
  Bedrock KB retrieval
  Rerank
  Agent explanation
  Feedback logging
        |
        +--> Product Catalog DB
        +--> Bedrock Knowledge Base
        +--> Naver Shopping API
        +--> Admin/QA tools
```

## 19. 첫 구현 순서 제안

한 번에 전체 기능을 만들더라도, merge 가능한 순서는 아래처럼 나눠야 한다.

```txt
1. Schema and contracts
2. Curated catalog seed
3. Naver Shopping API adapter
4. Product matching baseline
5. Bedrock KB ingestion
6. Rerank and evaluation
7. Agent final response
8. Recommendation UI
9. Feedback and admin QA
10. Privacy/security hardening
```

이 순서를 지키면 중간에 AI 품질이 부족해도 최소한 `catalog + live link 추천`은 동작하고, RAG/agent 품질은 독립적으로 개선할 수 있다.

## 20. 공식 참고 링크

- Naver Shopping Search API: https://developers.naver.com/docs/serviceapi/search/shopping/shopping.md
- Amazon Bedrock Knowledge Bases: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html
- Amazon Bedrock Agents: https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
- Cohere Embed v4 on Bedrock: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-cohere-embed-v4.html
- Bedrock reranking: https://docs.aws.amazon.com/bedrock/latest/userguide/rerank.html
- Claude Sonnet 4.5 on Bedrock: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-4-5.html
- Claude Haiku 4.5 on Bedrock: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html

## 21. 현재 repo와의 경계

이 문서는 제품 추천 모듈 계획이다. 현재 active E7 AR 구현에서 아래를 바로 시작한다는 뜻은 아니다.

```txt
- backend upload
- AI model inference
- 추천 API 구현
- product DB 전체 구축
- 얼굴 원본 사진 서버 저장
- 쇼핑몰 크롤링
```

위 작업은 별도 implementation plan과 개인정보/데이터 권리 검토가 열린 뒤 진행한다.


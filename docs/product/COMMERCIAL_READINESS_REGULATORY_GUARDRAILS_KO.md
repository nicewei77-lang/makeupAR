# Commercial Readiness Regulatory Guardrails

검토일: 2026-06-25 KST

이 문서는 AR makeup / beauty AI 서비스를 상용 레벨까지 완성하기 위한 규제·플랫폼 준비 기준이다. 작업을 막기 위한 문서가 아니라 product-ready로 가기 위한 체크리스트이며, 출시 전에는 관할 지역과 실제 데이터 흐름 기준으로 법무 검토가 필요하다.

## 기본 원칙

- 기본 시장은 한국으로 본다. 미국, EU, Android, 글로벌 캠페인은 해당 범위가 명시될 때 추가 규제를 적용한다.
- 상용 레벨은 시각 품질만 뜻하지 않는다. 개인정보, 얼굴/피부 데이터, AI 설명/표시, 화장품 표시·광고, 결제/환불, 앱스토어 심사까지 통과 가능한 상태를 뜻한다.
- 얼굴 이미지, ARFace mesh, face feature snapshot, 피부/색상 분석값, 추천 결과는 원본 저장 여부와 무관하게 얼굴 유래 데이터로 취급한다.
- 기본 아키텍처는 on-device first, data-minimization, no raw frame retention이다. 업로드, 장기 저장, 모델 학습, 외부 SDK 전송은 별도 계획과 동의/고지 없이는 금지한다.

## 상용 릴리즈 게이트

상용 준비 완료 또는 product-ready라고 기록하려면 아래가 모두 필요하다.

- 제품 증거: 실제 기기 시나리오, 성능, 오류/복구, 접근성, 사용자 플로우가 상용 기준으로 검증되어야 한다.
- 개인정보 맵: 수집/생성/저장/전송/삭제되는 데이터와 제3자 SDK 흐름을 표로 기록해야 한다.
- 동의/고지: 카메라, 얼굴 유래 데이터, AI 분석, 추천, 마케팅, 제3자 제공, 국외 이전 여부를 사용자에게 분리 고지해야 한다.
- 보안: 전송/저장 암호화, 접근 권한, 로그 마스킹, 삭제 요청, 보존 기간, 침해 대응 경로가 있어야 한다.
- 표시·광고: 피부 진단, 치료, 의학적 효능, 기능성 화장품 효능, 보정 전후 비교, 추천 정확도 주장은 증빙과 법무 검토가 있어야 한다.
- 스토어 제출: Apple App Privacy, privacy manifest, App Review notes 또는 Google Play Data safety가 실제 코드/SDK 동작과 일치해야 한다.

## 한국 규제 체크

| 영역 | 적용 가능성 | 작업 가드 |
| --- | --- | --- |
| 개인정보 보호법 / 시행령 | 카메라, 얼굴/피부 유래 데이터, 계정, 구매, 로그, 추천 기록 | 목적 제한, 최소 수집, 분리 동의, 보존/삭제, 위탁/제3자 제공, 국외 이전, 안전조치, 개인정보처리방침을 설계에 포함한다. 식별 목적 생체정보 또는 민감정보에 가까운 처리는 더 엄격하게 본다. |
| AI 기본법 | AI 추천, 분석, 생성형 설명/이미지, 자동화된 사용자 영향 판단 | AI 사용 사실, 생성/변형 콘텐츠 표시, 설명 가능성, 고영향 AI 해당성 사전 분류를 기록한다. 뷰티 추천은 기본적으로 고영향이 아닐 수 있으나 피부 건강/의료·채용·금융처럼 확장하면 재분류한다. |
| 화장품법 | 실제 화장품 판매, 기능성 화장품 표현, 효능/효과 주장 | 의약품 오인, 치료/진단 표현, 승인 없는 기능성 표현을 피한다. AR 발색/피부표현은 시뮬레이션임을 명확히 한다. |
| 표시·광고의 공정화에 관한 법률 | 추천 정확도, 전후 비교, 성능 수치, 협찬/제휴, 경쟁사 비교 | 거짓·과장·기만·부당 비교 주장을 금지한다. 수치와 비교표는 근거 자료와 산정 방식을 남긴다. |
| 전자상거래 소비자보호법 / 약관규제법 | 앱 내 결제, 구독, 제품 판매, 쿠폰, 환불 | 판매자 정보, 가격, 청약철회/환불, 정기결제 고지, 약관 동의와 변경 고지를 제품 플로우에 포함한다. |
| 정보통신망법 / 위치정보법 | 광고성 메시지, 푸시, 위치 기반 매장 추천 | 광고성 정보 수신 동의, 수신 거부, 위치정보 동의/철회/파기 요건을 별도로 검토한다. |

## 얼굴/피부 데이터 설계 규칙

- raw camera frame, screen recording, face mesh export, UV atlas, snapshot example은 기본적으로 로컬/증거용으로만 다룬다.
- 서버 업로드가 필요하면 업로드 목적, 데이터 필드, 보존 기간, 삭제 API, 암호화, 접근 권한, 위탁사, 국외 이전 여부를 먼저 문서화한다.
- 사용자를 식별하거나 재식별할 수 있는 face embedding, face template, biometric identifier는 만들지 않는다. 필요해지는 순간 별도 민감정보/생체정보 검토가 필요하다.
- 디버그 로그에는 얼굴 좌표 원문, 이미지 경로, 계정 식별자, 구매 식별자, 원본 프롬프트를 그대로 남기지 않는다.
- 모델 학습/평가 데이터셋은 수집 동의, 저작권/초상권, 삭제 가능성, train/eval 분리, 외부 공유 범위를 기록하기 전에는 만들지 않는다.

## 표시·광고 문구 규칙

- 허용 방향: "AR 시뮬레이션", "가상 발색 미리보기", "개인화 추천 후보", "사용자 선택을 돕는 참고 정보".
- 법무 검토 전 금지 방향: "피부 질환 진단", "치료", "의학적 개선", "100% 정확", "전문가 확정 진단", "식약처/미국 FDA 승인" 같은 미확인 주장.
- 전후 이미지는 조명, 보정, 필터, AI 생성/합성 여부를 숨기지 않는다.
- 협찬, 제휴, 체험단, 인플루언서 콘텐츠는 광고 관계가 즉시 보이도록 표시한다.

## 해외/플랫폼 확장 체크

- EU 사용자 또는 EU 출시: GDPR과 EU AI Act 적용 가능성을 별도 검토한다. 얼굴 생체식별, profiling, automated decision, 생성/변형 콘텐츠 표시는 고위험 또는 특별범주 이슈가 될 수 있다.
- 미국 사용자 또는 광고: FTC endorsement/advertising guidance 기준으로 협찬 관계와 실증이 필요한 효능 주장을 관리한다.
- iOS 출시: Apple App Review Guidelines, App Privacy Details, Privacy Manifest가 실제 데이터/SDK 동작과 일치해야 한다.
- Android 출시: Google Play Data safety와 User Data policy 기준으로 수집/공유/보안/삭제 응답을 실제 동작과 일치시킨다.

## 현재 프로젝트 적용 상태

- 현재 검증 앱은 상용 앱이 아니라 validation/prototype 상태다.
- 상용 완성/제품 준비는 다음 작업 목표다. 다만 product-ready 표시는 위 릴리즈 게이트를 통과한 뒤에만 쓴다.
- 기존 E3/E4/E7 증거는 기술적 가능성 증거이며, 생산 수준 segmentation, cosmetic fidelity, privacy compliance, advertising compliance를 증명하지 않는다.

## 출처

- 개인정보 보호법: https://www.law.go.kr/법령/개인정보보호법
- 개인정보 보호법 시행령: https://www.law.go.kr/법령/개인정보보호법시행령
- 인공지능 발전과 신뢰 기반 조성 등에 관한 기본법: https://www.law.go.kr/법령/인공지능발전과신뢰기반조성등에관한기본법
- 화장품법: https://www.law.go.kr/법령/화장품법
- 표시·광고의 공정화에 관한 법률: https://www.law.go.kr/법령/표시ㆍ광고의공정화에관한법률
- 전자상거래 등에서의 소비자보호에 관한 법률: https://www.law.go.kr/법령/전자상거래등에서의소비자보호에관한법률
- 약관의 규제에 관한 법률: https://www.law.go.kr/법령/약관의규제에관한법률
- 정보통신망 이용촉진 및 정보보호 등에 관한 법률: https://www.law.go.kr/법령/정보통신망이용촉진및정보보호등에관한법률
- 위치정보의 보호 및 이용 등에 관한 법률: https://www.law.go.kr/법령/위치정보의보호및이용등에관한법률
- EU AI Act: https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- GDPR: https://eur-lex.europa.eu/eli/reg/2016/679/oj
- Apple App Review Guidelines: https://developer.apple.com/app-store/review/guidelines/
- Apple App Privacy Details: https://developer.apple.com/app-store/app-privacy-details/
- Apple Privacy Manifest Files: https://developer.apple.com/documentation/bundleresources/privacy-manifest-files
- Google Play Data safety: https://support.google.com/googleplay/android-developer/answer/10787469
- FTC Disclosures 101 for Social Media Influencers: https://www.ftc.gov/business-guidance/resources/disclosures-101-social-media-influencers
- FTC Health Products Compliance Guidance: https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance

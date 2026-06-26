# E7 Lip Generate Evidence Runbook

이 문서는 E7 개인 맞춤 립 Generate의 buildless 웹 베타 evidence를 남기는 절차다.

## 목적

앱 빌드 전에 아래 네 가지가 실제로 되는지 확인한다.

```txt
1. Vision fixture mask 생성
2. MediaPipe fixture mask 생성
3. 2D mask -> ARFace UV texture 생성
4. UV texture -> screen round-trip overlay 생성
```

웹 UI만 있고 마스크 생성이 없으면 gate 실패다.

## 로컬 서버

```bash
cd /Users/wiseungcheol/Desktop/makeupAR
./.venv/bin/python local-tools/lip-generate-server/server.py --host 127.0.0.1 --port 8791
```

서버 원칙:

- `127.0.0.1` 로컬 전용.
- 업로드 없음.
- raw frame 신규 장기 저장 없음.
- 원격 URL 입력 없음.
- 결과 artifact는 ignored evidence 경로에 생성.
- iPhone runtime evidence 전까지 `runtimeReady=false`.

## 웹 베타

```bash
cd /Users/wiseungcheol/Desktop/makeupAR
python3 -m http.server 8788 --bind 127.0.0.1
```

브라우저:

```txt
http://127.0.0.1:8788/web/lip-generate-beta/
```

확인:

- `Generate` 클릭.
- `Vision` / `MediaPipe` 전환.
- `UV Only` / `Blendshape Assist` 전환.
- `4-Way` 클릭.
- Frame, 2D Mask, UV Texture, Round-trip 이미지가 모두 표시되는지 확인.
- Payload에 `generatedMaskId`, `provider`, `expressionMode`, `adjustment`, `uvMaskTexture`, `roundTripPreview`, `runtimeApplyPayload`, `privacyFlags`가 들어있는지 확인.

## Smoke

```bash
cd /Users/wiseungcheol/Desktop/makeupAR
./.venv/bin/python local-tools/lip-generate-server/server.py --smoke
```

현재 smoke의 성공 의미:

```txt
status=partial
uvMaskReady=true
roundTripReady=true
runtimeApplyReady=false
```

`partial`인 이유:

- same-frame round-trip은 projection sanity이지 boundary quality proof가 아니다.
- coordinate-space audit과 triangle visibility/front-most 처리는 아직 완전하지 않다.
- MediaPipe는 GUI Terminal 성공 fixture를 사용한다. Codex shell 자동 실행은 GL/Metal context 문제로 gate가 아니다.
- iPhone runtime 적용 evidence가 없다.

## 완료 전 금지

- 이 web/server smoke만으로 `runtime ready`, `E7.3 Green`, `Lip Green`을 주장하지 않는다.
- OpenCV/scikit-image 보정을 Vision/MediaPipe 기본 비교에 끼워 넣지 않는다.
- 서버 제품 경로, 업로드, Android, 상용 SDK를 추가하지 않는다.

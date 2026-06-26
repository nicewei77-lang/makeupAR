# E7 Lip Generate Web Beta

Unity/ARKit 렌더링을 대체하는 앱이 아니라, 빌드 전에 서비스 흐름과 마스크 생성 로직을 확인하는 로컬 웹 베타다.

## 실행

터미널 1:

```bash
cd /Users/wiseungcheol/Desktop/makeupAR
./.venv/bin/python local-tools/lip-generate-server/server.py --host 127.0.0.1 --port 8791
```

터미널 2:

```bash
cd /Users/wiseungcheol/Desktop/makeupAR
cd web/lip-generate-beta
npm install
npm run dev
```

브라우저:

```txt
http://127.0.0.1:8789/
```

## 확인할 것

- `Generate`가 실제 local server를 호출한다.
- Vision / MediaPipe mask가 생성된다.
- UV texture와 round-trip overlay가 생성된다.
- `4-Way`가 Vision/MediaPipe x UV Only/Blendshape Assist 네 조합을 만든다.
- payload preview에 `generatedMaskId`, `provider`, `expressionMode`, `adjustment`, `uvMaskTexture`, `roundTripPreview`, `runtimeApplyPayload`, `privacyFlags`가 보인다.

## 제한

- 현재는 React/Vite + local fixture 기반 web beta다.
- iPhone AR runtime proof가 아니다.
- `runtimeReady=false`를 유지한다.
- MediaPipe는 GUI Terminal 성공 fixture를 사용한다. Codex shell 자동 실행은 GL/Metal context 문제로 gate가 아니다.

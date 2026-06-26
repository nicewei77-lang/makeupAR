# E7 Lip Generate Local Server

웹 베타에서 실제 마스크 생성과 UV round-trip을 검증하기 위한 로컬 전용 서버다.

```bash
cd /Users/wiseungcheol/Desktop/makeupAR
./.venv/bin/python local-tools/lip-generate-server/server.py --host 127.0.0.1 --port 8791
```

Smoke:

```bash
cd /Users/wiseungcheol/Desktop/makeupAR
./.venv/bin/python local-tools/lip-generate-server/server.py --smoke
```

원칙:

- `127.0.0.1`에만 바인딩한다.
- 원격 URL을 받지 않는다.
- raw frame을 새로 장기 저장하지 않는다.
- 결과는 ignored evidence 폴더에 파생 artifact로 남긴다.
- `runtimeReady=false`를 유지한다. iPhone runtime evidence 없이 ready를 주장하지 않는다.

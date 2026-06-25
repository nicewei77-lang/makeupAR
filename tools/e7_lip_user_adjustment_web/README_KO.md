# E7 Lip User Adjustment Review Web v0

M1 `User Adjustment` UI/로직 실험용 로컬 웹앱이다. UnityFramework, Xcode, iPhone build, live face parsing, upload를 실행하지 않는다.

## 실행

```bash
cd /Users/wiseungcheol/Desktop/makeupAR
python3 -m http.server 8787 --bind 127.0.0.1
```

브라우저에서 `http://127.0.0.1:8787/tools/e7_lip_user_adjustment_web/`를 연다.

현재 `/tmp/e7-user-adjustment-smoke` 샘플을 바로 보려면 다음 local-only symlink가 있으면 된다. 이 경로는 `.gitignore`로 제외된다.

```bash
mkdir -p tools/e7_lip_user_adjustment_web/local-assets
ln -s /private/tmp/e7-user-adjustment-smoke tools/e7_lip_user_adjustment_web/local-assets/e7-user-adjustment-smoke
```

## 입력

1. `샘플 자동 로드`: 현재 `/private/tmp/e7-user-adjustment-smoke` 샘플을 바로 불러온다.
2. `후보 JSON`: `user_adjustment_candidates.json`
3. `출력 폴더 선택`: 위 JSON과 같은 폴더 전체를 선택한다. 예: `/private/tmp/e7-user-adjustment-smoke`

개별 PNG 이미지를 하나 고르는 것이 아니다. 후보 생성 결과가 들어 있는 폴더 자체를 선택해야 한다.

## UI

- `cornerReach`, `upperLipTightness`, `lowerLipTightness`, `verticalOffset` 네 값을 슬라이더와 `-` / `+` 버튼으로 직접 조정한다.
- `-` / `+` 버튼은 `0.05` 단위로 움직인다.
- 후보 선택형과 문제별 조정형은 제거했다. 현재 앱 이식 후보는 이 슬라이더형 하나다.

## 출력 계약

앱으로 이식할 때도 같은 이름을 쓴다.

```json
{
  "schemaVersion": "e7-lip-user-adjustment-review-v0",
  "status": "user_confirmed",
  "confirmedByUser": true,
  "selectedCandidateId": "ua-web-slider-custom",
  "selectedMaskPath": "user_adjustment_candidate_ua-web-slider-custom_mask.png",
  "params": {
    "cornerReach": 0.25,
    "upperLipTightness": 0.2,
    "lowerLipTightness": 0.45,
    "verticalOffset": 0
  }
}
```

`user_adjustment_review.json`, `user_adjustment_candidates.json`, `user_adjustment_candidate_ua-web-slider-custom_mask.png` 세 파일을 같은 폴더에 저장해야 기존 `prepare_m1_lip_package.py --user-adjustment-review` 검증 경로가 그대로 동작한다.

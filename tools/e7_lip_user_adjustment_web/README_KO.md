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

1. `후보 JSON`: `user_adjustment_candidates.json`
2. `이미지 폴더`: 위 JSON과 같은 출력 폴더, 또는 `frame.png`, `lip-tight-auto-v0_mask.png`, `face_parsing_upper_lip_mask.png`, `face_parsing_lower_lip_mask.png`, `face_parsing_inner_mouth_mask.png`가 들어 있는 M1 패키지 폴더

## 세 가지 UI

- `후보 선택`: 기존 12개 후보 중 하나를 선택한다.
- `슬라이더`: `cornerReach`, `upperLipTightness`, `lowerLipTightness`, `verticalOffset` 네 값을 직접 조정한다.
- `문제별 조정`: “입꼬리 더 잡기”, “아랫입술 번짐 줄이기” 같은 문제 문장으로 같은 네 값을 조정한다.

## 출력 계약

앱으로 이식할 때도 같은 이름을 쓴다.

```json
{
  "schemaVersion": "e7-lip-user-adjustment-review-v0",
  "status": "user_confirmed",
  "confirmedByUser": true,
  "selectedCandidateId": "ua-11-balanced-observed",
  "selectedMaskPath": "user_adjustment_candidate_ua-11-balanced-observed_mask.png",
  "params": {
    "cornerReach": 0.25,
    "upperLipTightness": 0.2,
    "lowerLipTightness": 0.45,
    "verticalOffset": 0
  }
}
```

직접 조정 모드는 `user_adjustment_review.json`, `user_adjustment_candidates.json`, `user_adjustment_candidate_<candidateId>_mask.png` 세 파일을 같은 폴더에 저장해야 기존 `prepare_m1_lip_package.py --user-adjustment-review` 검증 경로가 그대로 동작한다.

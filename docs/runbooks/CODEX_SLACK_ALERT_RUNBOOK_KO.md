# Codex Slack 사용자 확인 알림 가이드

목적: Codex Goal 작업 중 빌드 승인, iPhone 잠금 해제, 카메라 권한, 실제 눈검수처럼 사용자의 판단이 필요한 순간을 Slack으로 바로 호출한다.

이 가이드는 제품 기능이 아니라 로컬 작업 운영용이다. Slack Webhook URL은 secret이므로 코드, 문서, PR, 스크린샷, 채팅에 노출하지 않는다.

## 1. 준비물

- Slack 워크스페이스 관리자 또는 앱 추가 권한.
- 알림을 받을 Slack 채널. 예: `#codex-alerts`
- 이 repo: `/Users/wiseungcheol/Desktop/makeupAR`
- Python 3
- repo 안의 알림 스크립트: `scripts/notify_slack_user_required.py`

## 2. Slack 채널 만들기

1. Slack에서 알림용 채널을 만든다. 예: `#codex-alerts`
2. 폰 Slack 앱에서 해당 채널 알림을 `모든 새 메시지`로 설정한다.
3. 푸시가 약하면 나중에 `CODEX_SLACK_MENTION="<@U...>"`를 추가한다.

## 3. Incoming Webhook URL 발급

1. Slack API 앱 페이지로 이동한다: <https://api.slack.com/apps>
2. `Create New App`을 누른다.
3. `From scratch`를 선택한다.
4. 앱 이름을 정한다. 예: `Codex User Check Alert`
5. 사용할 Slack workspace를 선택한다.
6. 왼쪽 메뉴에서 `Incoming Webhooks`로 이동한다.
7. `Activate Incoming Webhooks`를 `On`으로 켠다.
8. `Add New Webhook to Workspace`를 누른다.
9. 알림을 받을 채널을 선택한다. 예: `#codex-alerts`
10. `Allow`를 누른다.
11. `Webhook URLs for Your Workspace`에 생긴 URL을 복사한다.

주의: 복사한 URL은 `https://hooks.slack.com/services/...` 형태여야 한다. 이 URL은 비밀번호처럼 취급한다.

## 4. 로컬 `.env.local` 설정

repo root로 이동한다.

```bash
cd /Users/wiseungcheol/Desktop/makeupAR
```

Webhook URL을 터미널에서만 입력한다.

```bash
read -s SLACK_WEBHOOK_URL
printf 'SLACK_WEBHOOK_URL="%s"\n' "$SLACK_WEBHOOK_URL" > .env.local
chmod 600 .env.local
unset SLACK_WEBHOOK_URL
```

`read -s` 다음 줄에서 커서가 멈추면 Slack Webhook URL을 붙여넣고 Enter를 누른다.

선택 설정:

```bash
# 폰 푸시를 더 강하게 만들고 싶을 때
printf 'CODEX_SLACK_MENTION="<@UXXXXXXXX>"\n' >> .env.local

# Codex thread URL을 고정으로 같이 띄우고 싶을 때
printf 'CODEX_THREAD_URL="https://..."\n' >> .env.local
```

`.env.local`은 `.gitignore`의 `.env.*` 규칙으로 커밋되지 않아야 한다.

## 5. 설정 확인

secret을 출력하지 않고 설정만 확인한다.

```bash
python3 scripts/notify_slack_user_required.py --check-config
```

정상 예시:

```json
{
  "configured": true,
  "webhookHost": "hooks.slack.com",
  "mentionConfigured": false,
  "threadUrlConfigured": false,
  "repo": "makeupAR"
}
```

payload만 확인하고 Slack에는 보내지 않는다.

```bash
python3 scripts/notify_slack_user_required.py --dry-run --message "USER_INPUT_REQUIRED 테스트: payload 확인"
```

실제 Slack 전송 테스트:

```bash
python3 scripts/notify_slack_user_required.py --message "USER_INPUT_REQUIRED 테스트: Slack 알림 연결 확인"
```

성공하면 Slack 채널에 메시지가 도착하고 터미널에는 아래처럼 나온다.

```text
[slack-alert] sent USER_INPUT_REQUIRED to configured Slack webhook.
```

## 6. Goal 프롬프트에 넣을 문구

현재 Goal의 `진행 방식`에서 사용자 확인이 필요한 항목 바로 아래에 넣는다.

```md
사용자 확인이 필요한 순간에는 즉시 멈추고 Slack으로 호출한다.
- 스레드에 `USER_INPUT_REQUIRED:`로 시작하는 질문을 남긴다.
- 동시에 아래 명령을 실행한다.

  python3 scripts/notify_slack_user_required.py --message "<필요한 확인을 한 문장으로 요약>"

- Slack 전송이 실패해도 질문은 스레드에 남긴다.
- 사용자가 답하기 전까지 빌드, 기기 조작, 시각 판단, 선택/승인 사항을 임의로 진행하지 않는다.
- webhook URL은 `.env.local`에서만 읽고 절대 출력하지 않는다.
```

Goal 마지막 문장은 이렇게 바꾼다.

```md
목표 달성까지 계속 루프를 돌려라. 사용자 확인이 필요한 순간에는 `USER_INPUT_REQUIRED:`를 남기고 Slack으로 호출해라.
```

## 7. 실제 사용 예시

iPhone 빌드 승인:

```bash
python3 scripts/notify_slack_user_required.py --message "USER_INPUT_REQUIRED: Unity/RN iPhone build 승인 필요. Codex 스레드 확인해주세요."
```

눈검수 요청:

```bash
python3 scripts/notify_slack_user_required.py --message "USER_INPUT_REQUIRED: Vision/MediaPipe 립 마스크 4-way 결과 눈검수 필요."
```

iPhone 조작 요청:

```bash
python3 scripts/notify_slack_user_required.py --message "USER_INPUT_REQUIRED: iPhone 잠금 해제와 카메라 권한 확인이 필요합니다."
```

## 8. 문제 해결

- `configured: false`: `.env.local`이 repo root에 없거나 `SLACK_WEBHOOK_URL` 이름이 틀렸다.
- `Missing SLACK_WEBHOOK_URL`: `.env.local` 또는 환경변수에 webhook URL이 없다.
- `Slack webhook URL must use https`: Slack Incoming Webhook URL 형식이 아니다.
- `Could not reach Slack webhook`: 네트워크 또는 Codex sandbox 제한이다. 로컬 터미널에서 직접 실행하거나 네트워크 허용 후 재시도한다.
- Slack에는 왔는데 폰 푸시가 안 온다: 채널 알림을 `모든 새 메시지`로 바꾸거나 `CODEX_SLACK_MENTION`을 설정한다.
- URL이 노출됐다: Slack 앱 설정에서 기존 webhook을 revoke하고 새 URL을 발급한다.

## 9. 보안 원칙

- Webhook URL은 `.env.local`에만 둔다.
- URL을 Codex/ChatGPT/Slack 메시지/PR/문서/스크린샷에 붙이지 않는다.
- 프론트엔드, React Native 앱, Unity 코드에 URL을 넣지 않는다.
- 팀 공유는 이 문서와 스크립트만 공유하고, 각자 자기 workspace의 webhook URL을 발급해 `.env.local`에 넣는다.

## 10. 참고

- Slack 공식 Incoming Webhooks 문서: <https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/>
- Slack 앱 관리 페이지: <https://api.slack.com/apps>

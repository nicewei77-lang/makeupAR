#!/usr/bin/env python3
"""Send a local Slack alert when Codex needs user input.

Secrets are loaded from ignored local env files or process environment. This
script intentionally avoids third-party dependencies so it can be called from
Goal prompts without extra setup.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ALLOWED_WEBHOOK_HOSTS = {"hooks.slack.com", "hooks.slack-gov.com"}


def repo_root() -> Path:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if output:
            return Path(output)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return Path.cwd()


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]
        values[key] = value
    return values


def load_config(root: Path) -> dict[str, str]:
    config: dict[str, str] = {}
    for path in (
        root / ".env.local",
        root / ".env",
        root / "local-tools" / "slack-alert" / ".env",
    ):
        config.update(parse_env_file(path))

    for key in (
        "SLACK_WEBHOOK_URL",
        "CODEX_SLACK_MENTION",
        "CODEX_SLACK_ALERT_PREFIX",
        "CODEX_THREAD_URL",
    ):
        if os.environ.get(key):
            config[key] = os.environ[key]
    return config


def validate_webhook_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc not in ALLOWED_WEBHOOK_HOSTS:
        allowed = ", ".join(sorted(ALLOWED_WEBHOOK_HOSTS))
        raise ValueError(f"Slack webhook URL must use https and one of: {allowed}")
    if not parsed.path.startswith("/services/"):
        raise ValueError("Slack webhook URL path must start with /services/")


def git_value(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def build_payload(
    *,
    title: str,
    message: str,
    root: Path,
    config: dict[str, str],
) -> dict[str, object]:
    mention = config.get("CODEX_SLACK_MENTION", "").strip()
    prefix = config.get("CODEX_SLACK_ALERT_PREFIX", "Codex needs you").strip()
    thread_url = config.get("CODEX_THREAD_URL", "").strip()
    branch = git_value(["branch", "--show-current"]) or "(unknown branch)"
    commit = git_value(["rev-parse", "--short", "HEAD"]) or "(unknown commit)"

    text_parts = [mention, f"*{title}*", message]
    text = "\n".join(part for part in text_parts if part)

    fields: list[dict[str, str]] = [
        {"type": "mrkdwn", "text": f"*Repo*\n`{root.name}`"},
        {"type": "mrkdwn", "text": f"*Branch*\n`{branch}`"},
        {"type": "mrkdwn", "text": f"*Commit*\n`{commit}`"},
    ]
    if thread_url:
        fields.append({"type": "mrkdwn", "text": f"*Thread*\n<{thread_url}|Open Codex>"})

    return {
        "text": text,
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": prefix, "emoji": True},
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
            {"type": "section", "fields": fields},
        ],
    }


def post_to_slack(webhook_url: str, payload: dict[str, object]) -> None:
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"Slack returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Slack returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Slack webhook: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send a Slack alert when Codex needs user input."
    )
    parser.add_argument(
        "--title",
        default="USER_INPUT_REQUIRED",
        help="Short alert title shown in Slack.",
    )
    parser.add_argument(
        "--message",
        default="Codex 작업에 사용자 판단이 필요합니다. 스레드에 남긴 질문을 확인해주세요.",
        help="Alert body to send.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the Slack payload without sending it.",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate local Slack alert config without printing or sending the webhook URL.",
    )
    args = parser.parse_args()

    root = repo_root()
    config = load_config(root)
    webhook_url = config.get("SLACK_WEBHOOK_URL", "").strip()

    if args.check_config:
        webhook_host = urllib.parse.urlparse(webhook_url).netloc if webhook_url else ""
        if webhook_url:
            try:
                validate_webhook_url(webhook_url)
            except ValueError as exc:
                print(f"[slack-alert] {exc}", file=sys.stderr)
                return 2
        status = {
            "configured": bool(webhook_url),
            "webhookHost": webhook_host or "missing",
            "mentionConfigured": bool(config.get("CODEX_SLACK_MENTION", "").strip()),
            "threadUrlConfigured": bool(config.get("CODEX_THREAD_URL", "").strip()),
            "repo": root.name,
        }
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0 if webhook_url else 2

    if not webhook_url and not args.dry_run:
        print(
            "[slack-alert] Missing SLACK_WEBHOOK_URL. Add it to .env.local or the process environment.",
            file=sys.stderr,
        )
        return 2

    if webhook_url:
        try:
            validate_webhook_url(webhook_url)
        except ValueError as exc:
            print(f"[slack-alert] {exc}", file=sys.stderr)
            return 2

    payload = build_payload(
        title=args.title,
        message=args.message,
        root=root,
        config=config,
    )

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    try:
        post_to_slack(webhook_url, payload)
    except RuntimeError as exc:
        print(f"[slack-alert] {exc}", file=sys.stderr)
        return 1

    print("[slack-alert] sent USER_INPUT_REQUIRED to configured Slack webhook.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

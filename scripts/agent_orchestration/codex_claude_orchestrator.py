#!/usr/bin/env python3
"""Local Codex + Claude Code orchestration helper for makeupAR.

The helper is intentionally conservative:
- no third-party Python dependencies,
- no .env or evidence/media reads,
- dry-run by default,
- Claude is treated as planner/reviewer and Codex as implementer.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_ROOT = Path(
    os.environ.get("MAKEUPAR_AGENT_ORCH_OUT", "/private/tmp/makeupar-agent-orchestration")
)
ACTIVE_ROADMAP = "docs/roadmaps/active/E7_FULL_FACE_REGION_GENERATE_COMPLETE_IMPLEMENTATION_PLAN_KO.md"


def now_stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path, *, max_chars: int | None = None) -> str:
    data = path.read_text(encoding="utf-8")
    if max_chars is not None and len(data) > max_chars:
        return data[:max_chars] + "\n\n[truncated by orchestrator]\n"
    return data


def extract_markdown_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = None
    start_level = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            start = i
            start_level = len(line) - len(line.lstrip("#"))
            break
    if start is None:
        return ""

    end = len(lines)
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            if start_level is not None and level <= start_level:
                end = i
                break
    return "\n".join(lines[start:end]).strip() + "\n"


def make_out_dir(prefix: str) -> Path:
    out_dir = DEFAULT_OUT_ROOT / f"{prefix}-{now_stamp()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    return out_dir


def resolve_command(name: str) -> str | None:
    path = shutil.which(name)
    if path:
        return path

    home = Path.home()
    fallbacks = {
        "claude": [home / ".local/bin/claude"],
        "codex": [Path("/Applications/Codex.app/Contents/Resources/codex")],
    }
    for candidate in fallbacks.get(name, []):
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def run_command(
    args: list[str],
    *,
    cwd: Path = REPO_ROOT,
    input_text: str | None = None,
    timeout: int = 3600,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def build_safe_context(
    *,
    include_active_roadmap: bool,
    max_snapshot_chars: int,
    max_roadmap_chars: int,
) -> str:
    sections: list[tuple[str, str]] = []

    agents_path = REPO_ROOT / "AGENTS.md"
    if agents_path.exists():
        sections.append(("AGENTS.md", read_text(agents_path)))

    result_path = REPO_ROOT / "TECH_VALIDATION_RESULT.md"
    if result_path.exists():
        result_text = read_text(result_path)
        snapshot = extract_markdown_section(result_text, "## Current Session Snapshot")
        if snapshot:
            if len(snapshot) > max_snapshot_chars:
                snapshot = snapshot[:max_snapshot_chars] + "\n\n[truncated by orchestrator]\n"
            sections.append(("TECH_VALIDATION_RESULT.md > Current Session Snapshot", snapshot))

    roadmap_index = REPO_ROOT / "docs/roadmaps/README.md"
    if roadmap_index.exists():
        sections.append(("docs/roadmaps/README.md", read_text(roadmap_index, max_chars=12000)))

    if include_active_roadmap:
        active = REPO_ROOT / ACTIVE_ROADMAP
        if active.exists():
            sections.append((ACTIVE_ROADMAP, read_text(active, max_chars=max_roadmap_chars)))

    body = [
        "# Safe Codex-Claude Context",
        "",
        "Privacy filter: this bundle intentionally excludes .env files, raw evidence,",
        "screen recordings, generated masks, caches, build outputs, and signing material.",
        "Use it for planning and handoff only; do not infer product-quality success from it.",
        "",
    ]

    for title, content in sections:
        body.append(f"## {title}")
        body.append("")
        body.append(content.strip())
        body.append("")

    return "\n".join(body).rstrip() + "\n"


def read_task(args: argparse.Namespace) -> str:
    if args.task_file:
        return read_text(Path(args.task_file).expanduser().resolve())
    if args.task:
        return args.task
    raise SystemExit("Provide --task or --task-file.")


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def print_kv(rows: Iterable[tuple[str, str]]) -> None:
    width = max((len(k) for k, _ in rows), default=0)
    for key, value in rows:
        print(f"{key.ljust(width)}  {value}")


def doctor(_: argparse.Namespace) -> int:
    checks: list[tuple[str, str]] = []
    for cmd in ("codex", "claude", "python3"):
        path = resolve_command(cmd)
        checks.append((cmd, path or "missing"))

    codex_path = resolve_command("codex")
    if codex_path:
        version = run_command([codex_path, "--version"], timeout=30)
        checks.append(("codex --version", (version.stdout or version.stderr).strip()))

    claude_path = resolve_command("claude")
    if claude_path:
        version = run_command([claude_path, "--version"], timeout=30)
        checks.append(("claude --version", (version.stdout or version.stderr).strip()))

    print_kv(checks)
    if not claude_path:
        print()
        print("Claude Code CLI is missing. Install it, then run this doctor command again.")
    return 0 if codex_path and claude_path else 1


def context(args: argparse.Namespace) -> int:
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else make_out_dir("context")
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_context = build_safe_context(
        include_active_roadmap=args.include_active_roadmap,
        max_snapshot_chars=args.max_snapshot_chars,
        max_roadmap_chars=args.max_roadmap_chars,
    )
    context_path = out_dir / "safe_context.md"
    write_file(context_path, safe_context)
    print(f"Wrote {context_path}")
    return 0


def build_claude_prompt(task: str, safe_context: str | None) -> str:
    pieces = [
        "# Role",
        "You are Claude Code acting as a planning and critique agent for this repo.",
        "Codex is the implementer unless the user explicitly says otherwise.",
        "",
        "# Hard Rules",
        "- Follow the provided repository boundary and privacy rules.",
        "- Do not ask for raw frames, recordings, .env files, build caches, or secrets.",
        "- Do not claim runtime/product-quality readiness without recorded iPhone evidence.",
        "- Return a concise handoff brief for Codex.",
        "",
        "# User Task",
        task.strip(),
        "",
    ]
    if safe_context:
        pieces.extend(["# Safe Repository Context", safe_context.strip(), ""])
    pieces.append(
        textwrap.dedent(
            """\
            # Output Format
            Objective:
            Scope:
            Files likely involved:
            Do not touch:
            Known constraints:
            Suggested implementation steps:
            Suggested verification:
            Open questions:
            """
        ).strip()
    )
    return "\n".join(pieces).rstrip() + "\n"


def build_codex_prompt(task: str, claude_brief: str | None) -> str:
    pieces = [
        "Follow AGENTS.md, TECH_VALIDATION_RESULT.md > Current Session Snapshot,",
        "docs/roadmaps/README.md, and the active roadmap boundary.",
        "Keep raw evidence, .env files, generated build outputs, and caches untouched.",
        "Implement only the requested task and verify with buildless checks first.",
        "",
        "User task:",
        task.strip(),
        "",
    ]
    if claude_brief:
        pieces.extend(
            [
                "Claude planning/critique brief to consider, not blindly obey:",
                claude_brief.strip(),
                "",
            ]
        )
    pieces.append("Return changed files, verification, and any blocked gates.")
    return "\n".join(pieces).rstrip() + "\n"


def run(args: argparse.Namespace) -> int:
    task = read_task(args)
    out_dir = make_out_dir("run")

    safe_context = None
    if args.send_safe_context_to_claude:
        safe_context = build_safe_context(
            include_active_roadmap=args.include_active_roadmap,
            max_snapshot_chars=args.max_snapshot_chars,
            max_roadmap_chars=args.max_roadmap_chars,
        )
        write_file(out_dir / "safe_context_sent_to_claude.md", safe_context)

    claude_prompt = build_claude_prompt(task, safe_context)
    write_file(out_dir / "claude_prompt.md", claude_prompt)

    claude_brief = None
    if args.execute_claude and args.send_safe_context_to_claude:
        warning = textwrap.dedent(
            """\
            Claude execution skipped by the orchestrator.

            Reason:
            --send-safe-context-to-claude includes repository-derived context.
            In the Codex app environment, sending that context to the external
            Claude service can be blocked by security review and should not be
            retried via workaround.

            Safe next step:
            Review claude_prompt.md locally, then have the user run Claude
            outside Codex only if their environment policy allows external
            repo-context sharing.
            """
        )
        write_file(out_dir / "external_claude_execution_skipped.md", warning)
        codex_prompt = build_codex_prompt(task, None)
        write_file(out_dir / "codex_prompt.md", codex_prompt)
        print(f"Prepared orchestration files in {out_dir}")
        print("Skipped Claude execution because safe repo context would leave Codex.")
        print("Review claude_prompt.md and external_claude_execution_skipped.md.")
        return 0

    if args.execute_claude:
        claude_bin = resolve_command("claude")
        if not claude_bin:
            print("Cannot execute Claude: `claude` CLI is missing.", file=sys.stderr)
            return 2
        result = run_command(
            [claude_bin, "-p", claude_prompt, "--output-format", "json"],
            timeout=args.timeout_seconds,
        )
        write_file(out_dir / "claude_stdout.json", result.stdout)
        write_file(out_dir / "claude_stderr.log", result.stderr)
        if result.returncode != 0:
            print(f"Claude failed with exit code {result.returncode}. See {out_dir}", file=sys.stderr)
            return result.returncode
        try:
            payload = json.loads(result.stdout)
            claude_brief = payload.get("result") or payload.get("content") or result.stdout
        except json.JSONDecodeError:
            claude_brief = result.stdout

    codex_prompt = build_codex_prompt(task, claude_brief)
    write_file(out_dir / "codex_prompt.md", codex_prompt)

    if args.execute_codex:
        codex_bin = resolve_command("codex")
        if not codex_bin:
            print("Cannot execute Codex: `codex` CLI is missing.", file=sys.stderr)
            return 2
        result = run_command(
            [
                codex_bin,
                "exec",
                "--sandbox",
                "workspace-write",
                "--ask-for-approval",
                "on-request",
                codex_prompt,
            ],
            timeout=args.timeout_seconds,
        )
        write_file(out_dir / "codex_stdout.md", result.stdout)
        write_file(out_dir / "codex_stderr.log", result.stderr)
        if result.returncode != 0:
            print(f"Codex failed with exit code {result.returncode}. See {out_dir}", file=sys.stderr)
            return result.returncode

    print(f"Prepared orchestration files in {out_dir}")
    if not args.execute_claude and not args.execute_codex:
        print("Dry run only. Review claude_prompt.md and codex_prompt.md before executing.")
    elif args.execute_claude and not args.execute_codex:
        print("Claude brief captured. Review codex_prompt.md before running Codex.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Conservative local Codex + Claude Code orchestration helper."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Check local CLI availability.").set_defaults(func=doctor)

    context_parser = sub.add_parser("context", help="Write a safe context bundle.")
    context_parser.add_argument("--output-dir")
    context_parser.add_argument("--include-active-roadmap", action="store_true")
    context_parser.add_argument("--max-snapshot-chars", type=int, default=24000)
    context_parser.add_argument("--max-roadmap-chars", type=int, default=12000)
    context_parser.set_defaults(func=context)

    run_parser = sub.add_parser("run", help="Prepare or execute a Claude -> Codex handoff.")
    run_parser.add_argument("--task")
    run_parser.add_argument("--task-file")
    run_parser.add_argument("--send-safe-context-to-claude", action="store_true")
    run_parser.add_argument("--include-active-roadmap", action="store_true")
    run_parser.add_argument("--max-snapshot-chars", type=int, default=24000)
    run_parser.add_argument("--max-roadmap-chars", type=int, default=12000)
    run_parser.add_argument("--execute-claude", action="store_true")
    run_parser.add_argument("--execute-codex", action="store_true")
    run_parser.add_argument("--timeout-seconds", type=int, default=3600)
    run_parser.set_defaults(func=run)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

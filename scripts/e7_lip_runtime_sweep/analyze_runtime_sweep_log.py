#!/usr/bin/env python3
"""Analyze E7 lip runtime sweep logs.

This is a buildless verifier for the M3B run. It does not decide Lip G/Y/R by
itself; it checks whether the runtime log contains enough wiring evidence to
support a later visual/runtime review.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
from collections import defaultdict
from pathlib import Path
from typing import Any


EVENT_ALIASES = {
    "rn_texture_recipe_batch_post": ("rn_texture_recipe_batch_post",),
    "recipe_applied": ("recipe_applied",),
    "recipe_latency": ("recipe_latency",),
    "region_mask_state": ("region_mask_state",),
    "region_mask_apply": ("region_mask_apply",),
    "e7_metric_sample": ("e7_metric_sample", "metric_sample", "rn_metric_sample_received"),
}

REQUIRED_EVENTS_BY_CANDIDATE = (
    "rn_texture_recipe_batch_post",
    "recipe_applied",
    "recipe_latency",
)

REQUIRED_GLOBAL_EVENTS = (
    "region_mask_state",
    "region_mask_apply",
    "e7_metric_sample",
)

REQUIRED_RUNTIME_FIELDS = (
    "candidateId",
    "maskTextureId",
    "maskThreshold",
    "maskFeatherUvNormalized",
    "cornerReach",
    "upperLipTightness",
    "lowerLipTightness",
    "verticalOffset",
    "trackingState",
    "stateAction",
    "averageFps",
    "averageFrameTimeMs",
    "meshVertexCount",
    "meshIndexCount",
    "meshUvCount",
)

FLOAT_FIELDS = (
    "maskThreshold",
    "maskFeatherUvNormalized",
    "cornerReach",
    "upperLipTightness",
    "lowerLipTightness",
    "verticalOffset",
    "averageFps",
    "averageFrameTimeMs",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze a full console log from an E7 lip runtime sweep."
    )
    parser.add_argument("log", type=Path)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path(
            "evidence/e7-lip-runtime-sweep-prep/"
            "validation-candidates-20260626Tsetup/runtime_candidate_registry.json"
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, body: str) -> None:
    path.write_text(body.rstrip() + "\n", encoding="utf-8")


def detect_event(line: str) -> str | None:
    for event_name, aliases in EVENT_ALIASES.items():
        if any(alias in line for alias in aliases):
            return event_name

    return None


def parse_json_fragment(line: str) -> dict[str, Any]:
    start = line.find("{")
    end = line.rfind("}")
    if start < 0 or end <= start:
        return {}

    fragment = line[start : end + 1]
    try:
        parsed = json.loads(fragment)
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def parse_key_values(line: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    json_data = parse_json_fragment(line)
    data.update(json_data)

    try:
        tokens = shlex.split(line)
    except ValueError:
        tokens = line.split()

    for token in tokens:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        key = re.sub(r"^[^A-Za-z0-9_]+", "", key)
        if not key:
            continue
        data[key] = value.strip(",")

    return data


def to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None
    try:
        return float(str(value))
    except ValueError:
        return None


def load_records(log_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(log_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        event = detect_event(line)
        if event is None:
            continue

        fields = parse_key_values(line)
        records.append(
            {
                "line": line_number,
                "event": event,
                "candidateId": fields.get("candidateId"),
                "fields": fields,
                "raw": line,
            }
        )

    return records


def summarize_candidate(candidate_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    matching = [
        record
        for record in records
        if record.get("candidateId") == candidate_id
    ]
    event_counts = {
        event_name: sum(1 for record in matching if record["event"] == event_name)
        for event_name in EVENT_ALIASES
    }
    seen_fields = sorted(
        {
            key
            for record in matching
            for key, value in record["fields"].items()
            if value not in (None, "")
        }
    )
    missing_events = [
        event_name
        for event_name in REQUIRED_EVENTS_BY_CANDIDATE
        if event_counts.get(event_name, 0) == 0
    ]
    missing_fields = [
        field
        for field in (
            "candidateId",
            "maskTextureId",
            "maskThreshold",
            "maskFeatherUvNormalized",
            "cornerReach",
            "upperLipTightness",
            "lowerLipTightness",
            "verticalOffset",
        )
        if field not in seen_fields
    ]

    return {
        "candidateId": candidate_id,
        "recordCount": len(matching),
        "eventCounts": event_counts,
        "seenFields": seen_fields,
        "missingEvents": missing_events,
        "missingFields": missing_fields,
        "firstLine": matching[0]["line"] if matching else None,
        "lastLine": matching[-1]["line"] if matching else None,
        "wiringEvidenceReady": not missing_events and not missing_fields,
    }


def summarize_global(records: list[dict[str, Any]]) -> dict[str, Any]:
    event_counts = {
        event_name: sum(1 for record in records if record["event"] == event_name)
        for event_name in EVENT_ALIASES
    }
    all_fields = {
        key
        for record in records
        for key, value in record["fields"].items()
        if value not in (None, "")
    }
    numeric_ranges: dict[str, dict[str, float] | None] = {}
    for field in FLOAT_FIELDS:
        values = [
            numeric
            for record in records
            for numeric in [to_float(record["fields"].get(field))]
            if numeric is not None
        ]
        numeric_ranges[field] = (
            {"min": min(values), "max": max(values)}
            if values
            else None
        )

    return {
        "recordCount": len(records),
        "eventCounts": event_counts,
        "missingGlobalEvents": [
            event_name
            for event_name in REQUIRED_GLOBAL_EVENTS
            if event_counts.get(event_name, 0) == 0
        ],
        "missingRuntimeFields": [
            field for field in REQUIRED_RUNTIME_FIELDS if field not in all_fields
        ],
        "numericRanges": numeric_ranges,
    }


def build_summary(log_path: Path, registry_path: Path) -> dict[str, Any]:
    registry = read_json(registry_path)
    candidate_ids = [
        str(candidate["candidateId"])
        for candidate in registry.get("candidates", [])
    ]
    records = load_records(log_path)
    candidate_summaries = [
        summarize_candidate(candidate_id, records)
        for candidate_id in candidate_ids
    ]
    global_summary = summarize_global(records)
    missing_candidates = [
        summary["candidateId"]
        for summary in candidate_summaries
        if summary["recordCount"] == 0
    ]
    candidates_with_gaps = [
        summary["candidateId"]
        for summary in candidate_summaries
        if not summary["wiringEvidenceReady"]
    ]
    wiring_ready = (
        not missing_candidates
        and not candidates_with_gaps
        and not global_summary["missingGlobalEvents"]
        and not global_summary["missingRuntimeFields"]
    )

    return {
        "schemaVersion": "e7-lip-runtime-sweep-log-analysis-v0",
        "log": str(log_path),
        "registry": str(registry_path),
        "candidateIds": candidate_ids,
        "decision": "wiring_ready" if wiring_ready else "partial_or_missing_evidence",
        "wiringEvidenceReady": wiring_ready,
        "missingCandidates": missing_candidates,
        "candidatesWithGaps": candidates_with_gaps,
        "globalSummary": global_summary,
        "candidateSummaries": candidate_summaries,
        "forbiddenClaims": {
            "claimsM1Ready": False,
            "claimsRuntimeReady": False,
            "claimsE73Green": False,
            "claimsLipGyrDecision": False,
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# E7 Lip Runtime Sweep Log Analysis",
        "",
        f"Decision: `{summary['decision']}`",
        "",
        f"Log: `{summary['log']}`",
        f"Registry: `{summary['registry']}`",
        "",
        "## Candidate Coverage",
        "",
    ]
    for candidate in summary["candidateSummaries"]:
        lines.append(
            f"- `{candidate['candidateId']}`: records `{candidate['recordCount']}`, "
            f"ready `{candidate['wiringEvidenceReady']}`, "
            f"missing events `{', '.join(candidate['missingEvents']) or 'none'}`, "
            f"missing fields `{', '.join(candidate['missingFields']) or 'none'}`"
        )

    global_summary = summary["globalSummary"]
    lines.extend(
        [
            "",
            "## Global Runtime Fields",
            "",
            f"- Missing global events: `{', '.join(global_summary['missingGlobalEvents']) or 'none'}`",
            f"- Missing runtime fields: `{', '.join(global_summary['missingRuntimeFields']) or 'none'}`",
            "",
            "## Boundaries",
            "",
            "- This analysis checks wiring evidence only.",
            "- It does not mark M1 ready, runtime ready, E7.3 Green, or Lip G/Y/R.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    log_path = args.log.resolve()
    registry_path = args.registry.resolve()
    output_dir = args.output_dir or log_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = build_summary(log_path, registry_path)
    output_json = output_dir / f"{log_path.stem}-runtime-sweep-analysis.json"
    output_md = output_dir / f"{log_path.stem}-runtime-sweep-analysis.md"
    write_json(output_json, summary)
    write_text(output_md, render_markdown(summary))
    print(output_json)
    print(output_md)
    return 0 if summary["wiringEvidenceReady"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

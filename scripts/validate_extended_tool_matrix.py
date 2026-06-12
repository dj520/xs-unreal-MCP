from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from server.xs_unreal_mcp.extended_tools import (  # noqa: E402
    EXTENDED_TOOL_SPECS,
    LOCAL_BACKEND_COMMANDS,
    normalize_profile,
    selected_specs,
)


READ_ONLY_PREFIXES = (
    "get_",
    "search_",
    "find_",
    "list_",
    "validate_",
    "inspect_",
)
CREATE_PREFIXES = (
    "create_",
    "import_",
    "spawn_",
)
MUTATION_PREFIXES = (
    "add_",
    "bind_",
    "compile_",
    "configure_",
    "connect_",
    "copy_",
    "link_",
    "paste_",
    "reorder_",
    "set_",
    "wrap_",
)
DESTRUCTIVE_PREFIXES = (
    "delete_",
    "remove_",
    "clear_",
    "destroy_",
)
MANUAL_PATTERNS = (
    "capture_",
    "debug",
    "history",
    "open_level",
    "pie",
    "play_",
    "runtime",
    "screenshot",
)


def scan_registered_commands(source: Path | None) -> tuple[set[str], str]:
    if source is None:
        return set(), "source_unavailable"
    if not source.exists():
        return set(), "source_missing"

    registered: set[str] = set()
    pattern = re.compile(r'return\s+TEXT\("([^"]+)"\)')
    for path in source.rglob("*"):
        if path.suffix.lower() not in {".cpp", ".h"}:
            continue
        if "Commands" not in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in pattern.finditer(text):
            command = match.group(1)
            if re.fullmatch(r"[a-z][a-z0-9_]*", command):
                registered.add(command)
    return registered, "source_scanned"


def latest_live_report() -> Path | None:
    generated = REPO_ROOT / "generated"
    if not generated.exists():
        return None
    candidates = list(generated.glob("live_validation_*/live_validation_*.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_live_report(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_live_indexes(report: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], set[str]]:
    by_command: dict[str, list[dict[str, Any]]] = defaultdict(list)
    domains_with_pass: set[str] = set()
    for step in report.get("steps", []):
        command = step.get("command")
        if isinstance(command, str) and command:
            by_command[command].append(step)
        if step.get("outcome") == "pass":
            domain = step.get("domain")
            if isinstance(domain, str) and domain:
                domains_with_pass.add(domain)
    return by_command, domains_with_pass


def backend_status(command: str, registered: set[str], source_status: str) -> str:
    if command in LOCAL_BACKEND_COMMANDS:
        return "local_adapter"
    if source_status != "source_scanned":
        return source_status
    if command in registered:
        return "backend_registered"
    return "backend_missing"


def live_status(spec_domain: str, command: str, by_command: dict[str, list[dict[str, Any]]], domains_with_pass: set[str]) -> str:
    steps = by_command.get(command, [])
    outcomes = {step.get("outcome") for step in steps}
    if "pass" in outcomes:
        return "pass_live"
    if "fail" in outcomes:
        return "fail_live"
    if "blocked" in outcomes:
        return "blocked_live"
    if spec_domain in domains_with_pass:
        return "domain_smoke_pass"
    return "not_executed"


def execution_policy(upstream_tool: str, backend_command: str, params: tuple[str, ...], status: str) -> str:
    if status == "backend_missing":
        return "backend_required"

    name = upstream_tool.lower()
    command = backend_command.lower()
    haystack = f"{name} {command}"

    if any(command.startswith(prefix) or name.startswith(prefix) for prefix in DESTRUCTIVE_PREFIXES):
        return "unsafe_skip"
    if any(pattern in haystack for pattern in MANUAL_PATTERNS):
        return "manual_only"
    if any(command.startswith(prefix) or name.startswith(prefix) for prefix in READ_ONLY_PREFIXES):
        return "read_only_auto"
    if any(command.startswith(prefix) or name.startswith(prefix) for prefix in CREATE_PREFIXES):
        return "safe_temp_asset"
    if any(command.startswith(prefix) or name.startswith(prefix) for prefix in MUTATION_PREFIXES):
        return "requires_fixture"
    if any(param.endswith("_path") or param.endswith("_name") for param in params):
        return "requires_fixture"
    return "manual_review"


def row_note(status: str, live: str, policy: str) -> str:
    if status == "backend_missing":
        return "UE plugin source does not expose this backend command"
    if status in {"source_unavailable", "source_missing"}:
        return "Set XS_MCP_VALIDATE_UNREAL_PLUGIN or pass --source to audit backend command coverage"
    if live == "pass_live":
        return "Exact backend command passed in the latest live report"
    if live == "blocked_live":
        return "Exact backend command was reached but lacked required fixture/state"
    if live == "domain_smoke_pass":
        return "Domain has live smoke coverage, but this exact command was not executed"
    if policy == "unsafe_skip":
        return "Do not auto-run without a disposable fixture and explicit cleanup"
    if policy == "requires_fixture":
        return "Needs a prepared temporary asset/node/component/graph fixture"
    if policy == "manual_only":
        return "Needs editor/runtime/manual context"
    return ""


def make_matrix(
    profile: str,
    source: Path | None,
    live_report_path: Path | None,
) -> dict[str, Any]:
    normalized_profile = normalize_profile(profile)
    specs = selected_specs(normalized_profile)
    if not specs:
        raise ValueError(f"Unknown extended profile: {profile}")

    registered, source_status = scan_registered_commands(source)
    live_report = load_live_report(live_report_path)
    by_command, domains_with_pass = build_live_indexes(live_report)

    rows: list[dict[str, Any]] = []
    for spec in specs:
        command = spec.backend_command
        b_status = backend_status(command, registered, source_status)
        l_status = live_status(spec.domain, command, by_command, domains_with_pass)
        policy = execution_policy(spec.upstream_tool, command, spec.params, b_status)
        live_steps = by_command.get(command, [])
        rows.append(
            {
                "name": spec.name,
                "domain": spec.domain,
                "upstream_tool": spec.upstream_tool,
                "backend_command": command,
                "backend_status": b_status,
                "live_status": l_status,
                "execution_policy": policy,
                "source_server": spec.source_server,
                "source_file": spec.source_file,
                "params": list(spec.params),
                "live_step_names": [str(step.get("name", "")) for step in live_steps],
                "note": row_note(b_status, l_status, policy),
            }
        )

    summary = {
        "profile": normalized_profile,
        "tool_count": len(rows),
        "unique_backend_command_count": len({row["backend_command"] for row in rows}),
        "source_status": source_status,
        "source": str(source) if source else "",
        "registered_command_count": len(registered),
        "live_report": str(live_report_path) if live_report_path else "",
        "latest_live_summary": live_report.get("summary", {}),
        "backend_status_counts": dict(sorted(Counter(row["backend_status"] for row in rows).items())),
        "live_status_counts": dict(sorted(Counter(row["live_status"] for row in rows).items())),
        "execution_policy_counts": dict(sorted(Counter(row["execution_policy"] for row in rows).items())),
        "domain_counts": dict(sorted(Counter(row["domain"] for row in rows).items())),
        "missing_backend_commands": sorted(
            {row["backend_command"] for row in rows if row["backend_status"] == "backend_missing"}
        ),
        "exact_live_pass_commands": sorted(
            {row["backend_command"] for row in rows if row["live_status"] == "pass_live"}
        ),
    }
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "summary": summary,
        "rows": rows,
    }


def write_json(path: Path, matrix: dict[str, Any]) -> None:
    path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "name",
        "domain",
        "upstream_tool",
        "backend_command",
        "backend_status",
        "live_status",
        "execution_policy",
        "source_server",
        "source_file",
        "params",
        "live_step_names",
        "note",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            item = dict(row)
            item["params"] = "|".join(item["params"])
            item["live_step_names"] = "|".join(item["live_step_names"])
            writer.writerow(item)


def write_markdown(path: Path, matrix: dict[str, Any]) -> None:
    summary = matrix["summary"]
    rows = matrix["rows"]

    lines = [
        "# Extended Tool Validation Matrix",
        "",
        f"- Generated: `{matrix['generated_at']}`",
        f"- Profile: `{summary['profile']}`",
        f"- Tool count: `{summary['tool_count']}`",
        f"- Unique backend commands: `{summary['unique_backend_command_count']}`",
        f"- Source status: `{summary['source_status']}`",
        f"- Live report: `{summary['live_report'] or 'not provided'}`",
        "",
        "## Summary",
        "",
        "| Bucket | Counts |",
        "| --- | --- |",
        f"| Backend status | `{json.dumps(summary['backend_status_counts'], ensure_ascii=False)}` |",
        f"| Live status | `{json.dumps(summary['live_status_counts'], ensure_ascii=False)}` |",
        f"| Execution policy | `{json.dumps(summary['execution_policy_counts'], ensure_ascii=False)}` |",
        f"| Domains | `{json.dumps(summary['domain_counts'], ensure_ascii=False)}` |",
        "",
        "## Backend Gaps",
        "",
    ]

    missing = summary["missing_backend_commands"]
    if missing:
        for command in missing:
            affected = [row["name"] for row in rows if row["backend_command"] == command]
            lines.append(f"- `{command}`: {', '.join(f'`{name}`' for name in affected)}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Matrix",
            "",
            "| Tool | Domain | Backend | Backend Status | Live Status | Policy | Note |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['name']}`",
                    f"`{row['domain']}`",
                    f"`{row['backend_command']}`",
                    f"`{row['backend_status']}`",
                    f"`{row['live_status']}`",
                    f"`{row['execution_policy']}`",
                    row["note"].replace("|", "/"),
                ]
            )
            + " |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a validation matrix for xs-unreal-MCP extended tools.")
    parser.add_argument("--profile", default="all", help="Extended profile to validate. Default: all.")
    parser.add_argument(
        "--source",
        default=os.getenv("XS_MCP_VALIDATE_UNREAL_PLUGIN", ""),
        help="Path to the UnrealMCP C++ Source directory. Defaults to XS_MCP_VALIDATE_UNREAL_PLUGIN.",
    )
    parser.add_argument(
        "--live-report",
        default="",
        help="Path to a live_validation_*.json report. Defaults to the newest generated live validation report.",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory. Defaults to generated/extended_tool_matrix_<timestamp>.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when backend commands are missing or live exact commands failed.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    source = Path(args.source) if args.source else None
    live_report_path = Path(args.live_report) if args.live_report else latest_live_report()
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "generated" / f"extended_tool_matrix_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    matrix = make_matrix(args.profile, source, live_report_path)
    json_path = out_dir / "extended_tool_matrix.json"
    csv_path = out_dir / "extended_tool_matrix.csv"
    md_path = out_dir / "extended_tool_matrix.md"
    write_json(json_path, matrix)
    write_csv(csv_path, matrix["rows"])
    write_markdown(md_path, matrix)

    summary = matrix["summary"]
    print(f"matrix_tool_count={summary['tool_count']}")
    print(f"unique_backend_command_count={summary['unique_backend_command_count']}")
    print(f"backend_status_counts={json.dumps(summary['backend_status_counts'], ensure_ascii=False)}")
    print(f"live_status_counts={json.dumps(summary['live_status_counts'], ensure_ascii=False)}")
    print(f"execution_policy_counts={json.dumps(summary['execution_policy_counts'], ensure_ascii=False)}")
    print(f"missing_backend_commands={json.dumps(summary['missing_backend_commands'], ensure_ascii=False)}")
    print(f"json={json_path}")
    print(f"csv={csv_path}")
    print(f"markdown={md_path}")

    if args.strict:
        backend_missing = summary["backend_status_counts"].get("backend_missing", 0)
        fail_live = summary["live_status_counts"].get("fail_live", 0)
        if backend_missing or fail_live:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

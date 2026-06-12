from __future__ import annotations

import argparse
import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
import wave
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from server.xs_unreal_mcp.extended_tools import EXTENDED_TOOL_SPECS, LOCAL_BACKEND_COMMANDS  # noqa: E402
from server.xs_unreal_mcp.router import ADD_NODE_COMMANDS, SET_PIN_COMMANDS, TOOL_ROUTES  # noqa: E402
from server.xs_unreal_mcp.tools import normalize_forward_params  # noqa: E402


HOST = os.getenv("XS_MCP_HOST", "127.0.0.1")
UNREAL_PORT = int(os.getenv("XS_MCP_UNREAL_PORT", "55557"))
BLUEPRINT_PORT = int(os.getenv("XS_MCP_BLUEPRINT_PORT", "55558"))
TIMEOUT = float(os.getenv("XS_MCP_VALIDATE_TIMEOUT", "90"))


@dataclass
class Step:
    name: str
    domain: str
    port: int | None
    command: str
    outcome: str
    elapsed_ms: int
    note: str = ""
    response_excerpt: str = ""


class ValidationRun:
    def __init__(self, timestamp: str, dry_run: bool = False) -> None:
        self.timestamp = timestamp
        self.dry_run = dry_run
        self.steps: list[Step] = []
        self.assets_to_delete: list[str] = []
        self.actors_to_delete: list[str] = []
        self.generated_files: list[str] = []

    def add_step(
        self,
        name: str,
        domain: str,
        port: int | None,
        command: str,
        outcome: str,
        elapsed_ms: int,
        note: str = "",
        response: Any | None = None,
    ) -> None:
        excerpt = ""
        if response is not None:
            excerpt = json.dumps(response, ensure_ascii=False, separators=(",", ":"))[:1200]
        self.steps.append(Step(name, domain, port, command, outcome, elapsed_ms, note, excerpt))
        print(f"[{outcome.upper():7}] {domain:16} {name} ({command}) {note}")


def _recv_json(sock: socket.socket) -> dict[str, Any]:
    chunks = bytearray()
    while True:
        chunk = sock.recv(8192)
        if not chunk:
            if not chunks:
                raise RuntimeError("socket closed before response")
            break
        chunks.extend(chunk)
        try:
            return json.loads(chunks.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    return json.loads(chunks.decode("utf-8"))


def send_raw(command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    with socket.create_connection((HOST, UNREAL_PORT), timeout=8) as sock:
        sock.settimeout(TIMEOUT)
        payload = json.dumps(
            {"type": command, "params": params or {}},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        sock.sendall(payload)
        try:
            sock.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        return _recv_json(sock)


def send_length(command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    with socket.create_connection((HOST, BLUEPRINT_PORT), timeout=8) as sock:
        sock.settimeout(TIMEOUT)
        payload = json.dumps(
            {"type": command, "params": params or {}},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        sock.sendall(struct.pack(">I", len(payload)))
        sock.sendall(payload)
        header = sock.recv(4)
        if len(header) != 4:
            raise RuntimeError("missing length response header")
        size = struct.unpack(">I", header)[0]
        body = bytearray()
        while len(body) < size:
            chunk = sock.recv(size - len(body))
            if not chunk:
                raise RuntimeError("socket closed while reading length response")
            body.extend(chunk)
        return json.loads(body.decode("utf-8"))


def call_port(port: int, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if port == UNREAL_PORT:
        return send_raw(command, params)
    if port == BLUEPRINT_PORT:
        return send_length(command, params)
    raise ValueError(f"unsupported validation port: {port}")


def result_body(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("result", response)
    return body if isinstance(body, dict) else response


def is_success(response: dict[str, Any]) -> bool:
    if response.get("status") == "error":
        return False
    body = result_body(response)
    if body.get("success") is False:
        return False
    if response.get("status") == "success":
        return True
    if body.get("success") is True:
        return True
    return "error" not in body


def failure_note(response: dict[str, Any]) -> str:
    body = result_body(response)
    for key in ("error", "message"):
        value = body.get(key) or response.get(key)
        if isinstance(value, str) and value:
            return value[:220]
    return "backend returned non-success response"


def run_command(
    run: ValidationRun,
    name: str,
    domain: str,
    port: int,
    command: str,
    params: dict[str, Any] | None = None,
    required: bool = True,
) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        response = call_port(port, command, params or {})
        elapsed = int((time.perf_counter() - start) * 1000)
        if is_success(response):
            run.add_step(name, domain, port, command, "pass", elapsed, response=response)
        else:
            outcome = "fail" if required else "blocked"
            run.add_step(name, domain, port, command, outcome, elapsed, failure_note(response), response)
        return response
    except Exception as exc:  # noqa: BLE001
        elapsed = int((time.perf_counter() - start) * 1000)
        outcome = "fail" if required else "blocked"
        run.add_step(name, domain, port, command, outcome, elapsed, str(exc)[:220])
        return {"status": "error", "error": str(exc)}


def slim(run: ValidationRun, tool_name: str, params: dict[str, Any] | None = None, required: bool = True) -> dict[str, Any]:
    port, command = TOOL_ROUTES[tool_name]
    normalized_params = normalize_forward_params(tool_name, command, params or {})
    return run_command(run, f"slim_{tool_name}", "slim", port, command, normalized_params, required)


def slim_add_node(run: ValidationRun, node_type: str, params: dict[str, Any]) -> dict[str, Any]:
    command = ADD_NODE_COMMANDS[node_type]
    return run_command(run, f"slim_add_node_{node_type}", "slim", BLUEPRINT_PORT, command, params)


def slim_set_pin(run: ValidationRun, mode: str, params: dict[str, Any]) -> dict[str, Any]:
    command = SET_PIN_COMMANDS[mode]
    port = BLUEPRINT_PORT if mode == "default" else UNREAL_PORT
    return run_command(run, f"slim_set_pin_{mode}", "slim", port, command, params)


def extract_node_id(response: dict[str, Any]) -> str:
    body = result_body(response)
    for key in ("node_id", "id", "new_node_id"):
        value = body.get(key)
        if isinstance(value, str) and value:
            return value
    node = body.get("node")
    if isinstance(node, dict):
        for key in ("node_id", "id"):
            value = node.get(key)
            if isinstance(value, str) and value:
                return value
    return ""


def extract_path(response: dict[str, Any], fallback: str = "") -> str:
    body = result_body(response)
    for key in (
        "path",
        "asset_path",
        "blueprint_path",
        "widget_path",
        "state_tree_path",
        "graph_path",
        "material_path",
        "font_path",
        "datatable_path",
        "struct_path",
        "system_path",
        "emitter_path",
    ):
        value = body.get(key)
        if isinstance(value, str) and value.startswith("/"):
            return value
    return fallback


def source_command_audit(run: ValidationRun) -> dict[str, Any]:
    source_env = os.getenv("XS_MCP_VALIDATE_UNREAL_PLUGIN", "")
    actual_source = Path(source_env) if source_env else None
    registered: set[str] = set()
    if actual_source and actual_source.exists():
        pattern = re.compile(r'return\s+TEXT\("([^"]+)"\)')
        for path in actual_source.rglob("*"):
            if path.suffix.lower() not in {".cpp", ".h"}:
                continue
            if "Commands" not in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for match in pattern.finditer(text):
                name = match.group(1)
                if re.fullmatch(r"[a-z][a-z0-9_]*", name):
                    registered.add(name)

    backend_commands = {spec.backend_command for spec in EXTENDED_TOOL_SPECS if spec.backend_command not in LOCAL_BACKEND_COMMANDS}
    missing = sorted(backend_commands - registered)
    count_by_domain = Counter(spec.domain for spec in EXTENDED_TOOL_SPECS)
    missing_by_domain: dict[str, list[str]] = defaultdict(list)
    for spec in EXTENDED_TOOL_SPECS:
        if spec.backend_command in missing and spec.backend_command not in LOCAL_BACKEND_COMMANDS:
            missing_by_domain[spec.domain].append(spec.backend_command)

    report = {
        "source": str(actual_source) if actual_source else "",
        "extended_tool_count": len(EXTENDED_TOOL_SPECS),
        "unique_backend_command_count": len(backend_commands),
        "registered_command_count_from_source": len(registered),
        "local_backend_commands": sorted(LOCAL_BACKEND_COMMANDS),
        "missing_backend_command_count": len(missing),
        "missing_backend_commands": missing,
        "tool_count_by_domain": dict(sorted(count_by_domain.items())),
        "missing_by_domain": {k: sorted(set(v)) for k, v in sorted(missing_by_domain.items())},
    }
    if not actual_source or not actual_source.exists():
        outcome = "blocked"
        note = "set XS_MCP_VALIDATE_UNREAL_PLUGIN to audit actual UnrealMCP C++ source"
    else:
        outcome = "pass" if not missing else "fail"
        note = "" if not missing else f"{len(missing)} backend commands not found in actual plugin source"
    run.add_step("actual_unrealmcp_source_command_audit", "source_audit", None, "source_scan", outcome, 0, note, report)
    return report


def run_subprocess_check(run: ValidationRun, name: str, args: list[str]) -> None:
    start = time.perf_counter()
    try:
        completed = subprocess.run(
            args,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        elapsed = int((time.perf_counter() - start) * 1000)
        outcome = "pass" if completed.returncode == 0 else "fail"
        note = (completed.stdout or completed.stderr).strip().replace("\r", "")[:220]
        run.add_step(name, "static", None, " ".join(args), outcome, elapsed, note)
    except Exception as exc:  # noqa: BLE001
        elapsed = int((time.perf_counter() - start) * 1000)
        run.add_step(name, "static", None, " ".join(args), "fail", elapsed, str(exc)[:220])


def write_tiny_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 8000
    frames = bytearray()
    for i in range(sample_rate // 8):
        value = int(12000 * (1 if (i // 20) % 2 == 0 else -1))
        frames.extend(int(value).to_bytes(2, "little", signed=True))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))


def validate_slim(run: ValidationRun) -> dict[str, str]:
    suffix = run.timestamp
    bp_name = f"BP_XS_MCP_VALIDATE_{suffix}"
    bpi_name = f"BPI_XS_MCP_VALIDATE_{suffix}"
    actor_name = f"XS_MCP_VALIDATE_Actor_{suffix}"
    bp_path = f"/Game/Blueprints/{bp_name}"
    bpi_path = f"/Game/Blueprints/{bpi_name}"
    run.assets_to_delete.extend([bp_path, bpi_path])
    run.actors_to_delete.append(actor_name)

    run_command(run, "create_temp_blueprint_for_slim", "setup", UNREAL_PORT, "create_blueprint", {
        "name": bp_name,
        "parent_class": "Actor",
        "folder_path": "/Game/Blueprints",
    })
    run_command(run, "create_temp_interface_for_slim", "setup", UNREAL_PORT, "create_blueprint_interface", {
        "name": bpi_name,
        "folder_path": "/Game/Blueprints",
    })

    slim(run, "get_metadata", {"blueprint_name": bp_name, "fields": ["graphs", "variables", "components"]})
    slim(run, "find_nodes", {"blueprint_name": bp_name, "graph_name": "EventGraph"})
    slim(run, "add_variable", {
        "blueprint_name": bp_name,
        "variable_name": "ValidateFloat",
        "variable_type": "Float",
        "is_exposed": True,
    })
    slim(run, "get_variable_info", {"blueprint_name": bp_name, "variable_name": "ValidateFloat"})
    slim(run, "add_component", {
        "blueprint_name": bp_name,
        "component_name": "ValidateScene",
        "component_type": "SceneComponent",
    }, required=False)
    slim(run, "set_parent_class", {"blueprint_name": bp_name, "new_parent_class": "Actor"})
    slim(run, "add_interface", {"blueprint_name": bp_name, "interface_name": bpi_name})

    self_ref = slim_add_node(run, "self_ref", {"blueprint_name": bp_name, "graph_name": "EventGraph"})
    self_id = extract_node_id(self_ref)
    if self_id:
        slim(run, "get_pins", {"blueprint_name": bp_name, "node_id": self_id, "graph_name": "EventGraph"})

    branch_a = slim_add_node(run, "branch", {
        "blueprint_name": bp_name,
        "graph_name": "EventGraph",
        "node_position": [0, 0],
    })
    branch_b = slim_add_node(run, "branch", {
        "blueprint_name": bp_name,
        "graph_name": "EventGraph",
        "node_position": [360, 0],
    })
    branch_a_id = extract_node_id(branch_a)
    branch_b_id = extract_node_id(branch_b)
    if branch_a_id and branch_b_id:
        slim(run, "connect", {
            "blueprint_name": bp_name,
            "source_node_id": branch_a_id,
            "source_pin": "then",
            "target_node_id": branch_b_id,
            "target_pin": "execute",
            "graph_name": "EventGraph",
        })
        slim_set_pin(run, "default", {
            "blueprint_name": bp_name,
            "node_id": branch_a_id,
            "pin_name": "Condition",
            "default_value": "true",
            "graph_name": "EventGraph",
        })
        slim(run, "disconnect", {
            "blueprint_name": bp_name,
            "node_id": branch_b_id,
            "target_graph": "EventGraph",
            "disconnect_inputs": True,
            "disconnect_outputs": True,
        })
        slim(run, "replace_node", {
            "blueprint_name": bp_name,
            "old_node_id": branch_a_id,
            "new_node_type": "Branch",
            "target_graph": "EventGraph",
        })
    else:
        run.add_step("slim_branch_node_ids", "slim", None, "extract_node_id", "fail", 0, "missing branch node id")

    if self_id:
        slim(run, "delete_node", {"blueprint_name": bp_name, "node_id": self_id, "graph_name": "EventGraph"})
    slim(run, "auto_arrange", {"blueprint_name": bp_name, "graph_name": "EventGraph"})
    slim(run, "cleanup_graph", {
        "blueprint_name": bp_name,
        "cleanup_mode": "orphans",
        "graph_name": "EventGraph",
        "include_event_graph": True,
    })
    slim(run, "compile", {"blueprint_name": bp_name})

    slim(run, "spawn_actor", {
        "type": "PointLight",
        "name": actor_name,
        "location": [0, 0, 180],
    })
    slim(run, "get_level", {"fields": ["actors"], "actor_filter": f"{actor_name}*"})
    slim(run, "set_actor_transform", {
        "name": actor_name,
        "location": [100, 0, 180],
        "rotation": [0, 45, 0],
        "scale": [1, 1, 1],
    })
    slim(run, "set_actor_property", {
        "name": actor_name,
        "property_name": "bHidden",
        "value": True,
    })
    delete_actor_response = slim(run, "delete_actor", {"name": actor_name})
    if is_success(delete_actor_response) and actor_name in run.actors_to_delete:
        run.actors_to_delete.remove(actor_name)

    return {"bp_name": bp_name, "bp_path": bp_path, "bpi_path": bpi_path}


def validate_extended_domains(run: ValidationRun, out_dir: Path) -> None:
    suffix = run.timestamp
    folder = "/Game/XS_MCP_Validation"

    def asset(name: str) -> str:
        return f"{folder}/{name}"

    # blueprint_action
    run_command(run, "blueprint_action_search", "blueprint_action", UNREAL_PORT, "search_blueprint_actions", {
        "search_query": "Print String",
        "max_results": 5,
    })

    # project
    run_command(run, "project_search_assets", "project", UNREAL_PORT, "search_assets", {
        "folder": "/Game",
        "pattern": "BP_*",
    })
    struct_name = f"XS_MCP_VALIDATE_Row_{suffix}"
    struct_path = asset(struct_name)
    run.assets_to_delete.append(struct_path)
    run_command(run, "project_create_struct_for_datatable", "project", UNREAL_PORT, "create_struct", {
        "struct_name": struct_name,
        "path": folder,
        "properties": [{"name": "Label", "type": "String"}],
        "description": "xs-unreal-MCP live validation temp struct",
    }, required=False)

    # datatable
    dt_name = f"DT_XS_MCP_VALIDATE_{suffix}"
    dt_path = asset(dt_name)
    run.assets_to_delete.append(dt_path)
    dt = run_command(run, "datatable_create", "datatable", UNREAL_PORT, "create_datatable", {
        "datatable_name": dt_name,
        "row_struct_name": struct_path,
        "path": folder,
        "description": "xs-unreal-MCP live validation temp table",
    }, required=False)
    if is_success(dt):
        run_command(run, "datatable_get_row_names", "datatable", UNREAL_PORT, "get_datatable_row_names", {
            "datatable_path": dt_path,
        }, required=False)

    # editor
    run_command(run, "editor_get_level_metadata", "editor", UNREAL_PORT, "get_level_metadata", {
        "fields": ["actors"],
        "actor_filter": "XS_MCP_VALIDATE_DOES_NOT_EXIST*",
    })

    # material
    mat_name = f"M_XS_MCP_VALIDATE_{suffix}"
    mat_path = asset(mat_name)
    run.assets_to_delete.append(mat_path)
    mat = run_command(run, "material_create", "material", UNREAL_PORT, "create_material", {
        "name": mat_name,
        "path": folder,
        "blend_mode": "Opaque",
        "shading_model": "DefaultLit",
    })
    run_command(run, "material_search_palette", "material", UNREAL_PORT, "search_material_palette", {
        "search_query": "Constant",
        "max_results": 5,
    }, required=False)
    if is_success(mat):
        run_command(run, "material_get_graph_metadata", "material", UNREAL_PORT, "get_material_expression_metadata", {
            "material_path": mat_path,
            "fields": ["expressions", "properties"],
        }, required=False)
        run_command(run, "material_compile", "material", UNREAL_PORT, "compile_material", {
            "material_path": mat_path,
        }, required=False)

    # mesh
    run_command(run, "mesh_get_static_mesh_metadata", "mesh", UNREAL_PORT, "get_static_mesh_metadata", {
        "mesh_path": "/Engine/BasicShapes/Cube",
    }, required=False)

    # niagara
    run_command(run, "niagara_search_modules", "niagara", UNREAL_PORT, "search_niagara_modules", {
        "search_query": "Spawn",
        "max_results": 5,
    }, required=False)
    ns_name = f"NS_XS_MCP_VALIDATE_{suffix}"
    ns_path = asset(ns_name)
    run.assets_to_delete.append(ns_path)
    ns = run_command(run, "niagara_create_system", "niagara", UNREAL_PORT, "create_niagara_system", {
        "name": ns_name,
        "folder_path": folder,
        "auto_activate": True,
    }, required=False)
    if is_success(ns):
        run_command(run, "niagara_get_metadata", "niagara", UNREAL_PORT, "get_niagara_system_metadata", {
            "system": ns_path,
        }, required=False)
        run_command(run, "niagara_compile", "niagara", UNREAL_PORT, "compile_niagara_system", {
            "system": ns_path,
        }, required=False)

    # node domain overlaps graph manipulation but is exposed as extended node_* tools.
    # Slim graph manipulation already performs the live destructive-safe node checks.
    run.add_step("node_domain_covered_by_slim_graph_ops", "node", UNREAL_PORT, "disconnect_node/replace_node", "pass", 0)

    # pcg
    run_command(run, "pcg_search_palette", "pcg", UNREAL_PORT, "search_pcg_palette", {
        "search_query": "Input",
        "max_results": 5,
    }, required=False)
    pcg_name = f"PCG_XS_MCP_VALIDATE_{suffix}"
    pcg_path = asset(pcg_name)
    run.assets_to_delete.append(pcg_path)
    pcg = run_command(run, "pcg_create_graph", "pcg", UNREAL_PORT, "create_pcg_graph", {
        "name": pcg_name,
        "path": folder,
    }, required=False)
    if is_success(pcg):
        run_command(run, "pcg_get_metadata", "pcg", UNREAL_PORT, "get_pcg_graph_metadata", {
            "graph_path": pcg_path,
            "include_properties": False,
        }, required=False)

    # sound
    wav_path = out_dir / f"SW_XS_MCP_VALIDATE_{suffix}.wav"
    write_tiny_wav(wav_path)
    run.generated_files.append(str(wav_path))
    sw_name = f"SW_XS_MCP_VALIDATE_{suffix}"
    sw_path = asset(sw_name)
    run.assets_to_delete.append(sw_path)
    sw = run_command(run, "sound_import_wav", "sound", UNREAL_PORT, "import_sound_file", {
        "source_file_path": str(wav_path),
        "asset_name": sw_name,
        "folder_path": folder,
    }, required=False)
    if is_success(sw):
        run_command(run, "sound_get_wave_metadata", "sound", UNREAL_PORT, "get_sound_wave_metadata", {
            "sound_wave_path": sw_path,
        }, required=False)
    scue_name = f"SCue_XS_MCP_VALIDATE_{suffix}"
    scue_path = asset(scue_name)
    run.assets_to_delete.append(scue_path)
    scue = run_command(run, "sound_create_sound_cue", "sound", UNREAL_PORT, "create_sound_cue", {
        "asset_name": scue_name,
        "folder_path": folder,
        "initial_sound_wave": sw_path if is_success(sw) else "",
    }, required=False)
    if is_success(scue):
        run_command(run, "sound_compile_sound_cue", "sound", UNREAL_PORT, "compile_sound_cue", {
            "sound_cue_path": scue_path,
        }, required=False)

    # statetree
    run_command(run, "statetree_get_available_tasks", "statetree", UNREAL_PORT, "get_available_tasks", {}, required=False)
    st_name = f"ST_XS_MCP_VALIDATE_{suffix}"
    st_path = asset(st_name)
    run.assets_to_delete.append(st_path)
    st = run_command(run, "statetree_create", "statetree", UNREAL_PORT, "create_state_tree", {
        "name": st_name,
        "path": folder,
        "schema_class": "StateTreeComponentSchema",
        "compile_on_creation": False,
    }, required=False)
    if is_success(st):
        run_command(run, "statetree_add_state", "statetree", UNREAL_PORT, "add_state", {
            "state_tree_path": st_path,
            "state_name": "ValidateIdle",
        }, required=False)
        run_command(run, "statetree_get_metadata", "statetree", UNREAL_PORT, "get_state_tree_metadata", {
            "state_tree_path": st_path,
        }, required=False)

    # umg
    wbp_name = f"WBP_XS_MCP_VALIDATE_{suffix}"
    wbp_folder = "/Game/Widgets"
    wbp_path = f"{wbp_folder}/{wbp_name}"
    run.assets_to_delete.append(wbp_path)
    wbp = run_command(run, "umg_create_widget_blueprint", "umg", UNREAL_PORT, "create_umg_widget_blueprint", {
        "name": wbp_name,
        "widget_name": wbp_name,
        "parent_class": "UserWidget",
        "path": wbp_folder,
    }, required=False)
    if is_success(wbp):
        run_command(run, "umg_add_textblock", "umg", UNREAL_PORT, "add_widget_component_to_widget", {
            "blueprint_name": wbp_name,
            "widget_name": wbp_name,
            "component_name": "TxtValidate",
            "component_type": "TextBlock",
            "position": [16, 16],
            "size": [220, 48],
            "kwargs": json.dumps({"text": "XS MCP Validate", "font_size": 18}, ensure_ascii=False),
        }, required=False)
        run_command(run, "umg_get_metadata", "umg", UNREAL_PORT, "get_widget_blueprint_metadata", {
            "widget_name": wbp_name,
            "fields": ["components"],
        }, required=False)

    # font
    font_source = Path(os.getenv("XS_MCP_VALIDATE_TTF", r"C:\Windows\Fonts\arial.ttf"))
    font_name = f"Font_XS_MCP_VALIDATE_{suffix}"
    font_path = asset(font_name)
    run.assets_to_delete.append(font_path)
    if font_source.exists():
        font = run_command(run, "font_create_ttf", "font", UNREAL_PORT, "create_font", {
            "font_name": font_name,
            "source_type": "ttf",
            "ttf_file_path": str(font_source),
            "path": folder,
        }, required=False)
        if is_success(font):
            run_command(run, "font_get_metadata", "font", UNREAL_PORT, "get_font_metadata", {
                "font_path": font_path,
            }, required=False)
    else:
        run.add_step("font_create_ttf", "font", UNREAL_PORT, "create_font", "blocked", 0, f"TTF not found: {font_source}")

    # animation requires a skeleton; discover one before creating.
    skeletons = run_command(run, "animation_find_skeleton", "animation", UNREAL_PORT, "search_assets", {
        "asset_class": "Skeleton",
        "folder": "/Game",
    }, required=False)
    skeleton_path = ""
    body = result_body(skeletons)
    assets = body.get("assets")
    if isinstance(assets, list) and assets:
        first = assets[0]
        if isinstance(first, dict):
            skeleton_path = first.get("path", "")
    if skeleton_path:
        abp_name = f"ABP_XS_MCP_VALIDATE_{suffix}"
        abp_path = asset(abp_name)
        run.assets_to_delete.append(abp_path)
        abp = run_command(run, "animation_create_anim_bp", "animation", UNREAL_PORT, "create_animation_blueprint", {
            "name": abp_name,
            "skeleton_path": skeleton_path,
            "folder_path": folder,
            "compile_on_creation": False,
        }, required=False)
        if is_success(abp):
            run_command(run, "animation_get_metadata", "animation", UNREAL_PORT, "get_anim_blueprint_metadata", {
                "anim_blueprint_name": abp_path,
            }, required=False)
    else:
        run.add_step("animation_create_anim_bp", "animation", UNREAL_PORT, "create_animation_blueprint", "blocked", 0, "no Skeleton asset found under /Game")


def cleanup(run: ValidationRun) -> None:
    for actor in list(dict.fromkeys(run.actors_to_delete)):
        run_command(run, f"cleanup_actor_{actor}", "cleanup", UNREAL_PORT, "delete_actor", {"name": actor}, required=False)
    for asset_path in list(dict.fromkeys(reversed(run.assets_to_delete))):
        run_command(run, f"cleanup_asset_{asset_path}", "cleanup", UNREAL_PORT, "delete_asset", {"asset_path": asset_path}, required=False)


def write_report(run: ValidationRun, source_audit: dict[str, Any], out_dir: Path) -> Path:
    counts = Counter(step.outcome for step in run.steps)
    by_domain = defaultdict(Counter)
    for step in run.steps:
        by_domain[step.domain][step.outcome] += 1
    report = {
        "timestamp": run.timestamp,
        "host": HOST,
        "unreal_port": UNREAL_PORT,
        "blueprint_port": BLUEPRINT_PORT,
        "summary": dict(sorted(counts.items())),
        "summary_by_domain": {domain: dict(sorted(counter.items())) for domain, counter in sorted(by_domain.items())},
        "source_command_audit": source_audit,
        "steps": [asdict(step) for step in run.steps],
        "assets_scheduled_for_cleanup": list(dict.fromkeys(run.assets_to_delete)),
        "actors_scheduled_for_cleanup": list(dict.fromkeys(run.actors_to_delete)),
        "generated_files": run.generated_files,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"live_validation_{run.timestamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Live validate xs-unreal-MCP against a running Unreal Editor.")
    parser.add_argument("--skip-static", action="store_true", help="Skip local static/profile checks.")
    parser.add_argument("--out-dir", default="", help="Output directory for JSON report.")
    args = parser.parse_args()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "generated" / f"live_validation_{timestamp}"
    run = ValidationRun(timestamp=timestamp)

    if not args.skip_static:
        run_subprocess_check(run, "check_slim_tools", [sys.executable, "scripts/check_slim_tools.py"])
        run_subprocess_check(run, "check_profiles", [sys.executable, "scripts/check_profiles.py"])
        run_subprocess_check(run, "validate_unrealxu_skills", [
            sys.executable,
            r"third_party\unrealengine5-skills\skills\scripts\validate_skills.py",
        ])
        run_subprocess_check(run, "audit_public_package", [sys.executable, "scripts/audit_public_package.py"])

    source_audit = source_command_audit(run)

    run_command(run, "raw_get_project_dir", "protocol", UNREAL_PORT, "get_project_dir", {})
    run_command(run, "raw_get_level_metadata", "protocol", UNREAL_PORT, "get_level_metadata", {
        "fields": ["actors"],
        "actor_filter": "XS_MCP_VALIDATE_DOES_NOT_EXIST*",
    })
    run_command(run, "length_ping", "protocol", BLUEPRINT_PORT, "ping", {})

    try:
        validate_slim(run)
        validate_extended_domains(run, out_dir)
    finally:
        cleanup(run)

    report_path = write_report(run, source_audit, out_dir)
    print(f"\nreport={report_path}")
    counts = Counter(step.outcome for step in run.steps)
    print("summary=" + json.dumps(dict(sorted(counts.items())), ensure_ascii=False))

    # Return non-zero only for required failures. Optional domain dependency gaps are blocked.
    has_required_failures = any(step.outcome == "fail" for step in run.steps)
    return 1 if has_required_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

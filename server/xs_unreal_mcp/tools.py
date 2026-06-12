from __future__ import annotations

import json
from typing import Any

from .backend import BackendError, pool
from .router import ADD_NODE_COMMANDS, BLUEPRINT_MCP_PORT, GRAPH_MCP_PORT, SET_PIN_COMMANDS, route_for


def compact(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


def forward(tool_name: str, params: dict[str, Any], command: str | None = None, port: int | None = None) -> dict[str, Any]:
    target_port, target_command = route_for(tool_name)
    target_port = port if port is not None else target_port
    target_command = command or target_command
    try:
        return pool.send(target_port, target_command, compact(params))
    except BackendError as exc:
        return {
            "status": "error",
            "error": str(exc),
            "backend_port": target_port,
            "backend_command": target_command,
        }


def forward_add_node(node_type: str, params: dict[str, Any]) -> dict[str, Any]:
    command = ADD_NODE_COMMANDS.get(node_type)
    if command is None:
        return {
            "status": "error",
            "error": f"Unsupported node_type '{node_type}'",
            "supported_node_types": sorted(ADD_NODE_COMMANDS),
        }
    params = dict(params)
    params.pop("node_type", None)
    return forward("add_node", params, command=command, port=BLUEPRINT_MCP_PORT)


def forward_set_pin(mode: str, params: dict[str, Any]) -> dict[str, Any]:
    command = SET_PIN_COMMANDS.get(mode)
    if command is None:
        return {
            "status": "error",
            "error": f"Unsupported mode '{mode}'",
            "supported_modes": sorted(SET_PIN_COMMANDS),
        }

    params = dict(params)
    params.pop("mode", None)
    if mode == "value" and "default_value" in params and "value" not in params:
        params["value"] = params.pop("default_value")
    if mode == "default" and "value" in params and "default_value" not in params:
        params["default_value"] = str(params.pop("value"))

    port = BLUEPRINT_MCP_PORT if mode == "default" else GRAPH_MCP_PORT
    return forward("set_pin", params, command=command, port=port)


def as_json_text(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


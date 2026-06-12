from __future__ import annotations

import os

UNREAL_MCP_PORT = int(os.getenv("XS_MCP_UNREAL_PORT", "55557"))
BLUEPRINT_MCP_PORT = int(os.getenv("XS_MCP_BLUEPRINT_PORT", "55558"))
GRAPH_MCP_PORT = int(os.getenv("XS_MCP_GRAPH_PORT", str(UNREAL_MCP_PORT)))

SLIM_TOOL_NAMES = [
    "find_nodes",
    "get_pins",
    "add_node",
    "connect",
    "disconnect",
    "delete_node",
    "set_pin",
    "replace_node",
    "get_metadata",
    "get_variable_info",
    "add_variable",
    "add_component",
    "compile",
    "set_parent_class",
    "add_interface",
    "spawn_actor",
    "delete_actor",
    "get_level",
    "set_actor_property",
    "set_actor_transform",
    "auto_arrange",
    "cleanup_graph",
]

TOOL_ROUTES = {
    "find_nodes": (BLUEPRINT_MCP_PORT, "find_blueprint_nodes"),
    "get_pins": (BLUEPRINT_MCP_PORT, "get_node_pins"),
    "add_node": (BLUEPRINT_MCP_PORT, "add_blueprint_self_reference"),
    "connect": (BLUEPRINT_MCP_PORT, "connect_blueprint_nodes"),
    "disconnect": (GRAPH_MCP_PORT, "disconnect_node"),
    "delete_node": (BLUEPRINT_MCP_PORT, "delete_blueprint_node"),
    "set_pin": (BLUEPRINT_MCP_PORT, "set_node_pin_default"),
    "replace_node": (GRAPH_MCP_PORT, "replace_node"),
    "get_metadata": (UNREAL_MCP_PORT, "get_blueprint_metadata"),
    "get_variable_info": (UNREAL_MCP_PORT, "get_variable_info"),
    "add_variable": (BLUEPRINT_MCP_PORT, "add_blueprint_variable"),
    "add_component": (UNREAL_MCP_PORT, "add_component_to_blueprint"),
    "compile": (BLUEPRINT_MCP_PORT, "compile_blueprint"),
    "set_parent_class": (UNREAL_MCP_PORT, "set_blueprint_parent_class"),
    "add_interface": (UNREAL_MCP_PORT, "add_interface_to_blueprint"),
    "spawn_actor": (UNREAL_MCP_PORT, "spawn_actor"),
    "delete_actor": (UNREAL_MCP_PORT, "delete_actor"),
    "get_level": (UNREAL_MCP_PORT, "get_level_metadata"),
    "set_actor_property": (UNREAL_MCP_PORT, "set_actor_property"),
    "set_actor_transform": (UNREAL_MCP_PORT, "set_actor_transform"),
    "auto_arrange": (GRAPH_MCP_PORT, "auto_arrange_nodes"),
    "cleanup_graph": (GRAPH_MCP_PORT, "cleanup_blueprint_graph"),
}

ADD_NODE_COMMANDS = {
    "branch": "add_blueprint_branch_node",
    "cast": "add_blueprint_cast_node",
    "event": "add_blueprint_event_node",
    "custom_event": "add_blueprint_custom_event",
    "function": "add_blueprint_function_node",
    "variable_get": "add_blueprint_variable_get",
    "variable_set": "add_blueprint_variable_set",
    "self_ref": "add_blueprint_self_reference",
    "self_component": "add_blueprint_get_self_component_reference",
    "subsystem": "add_blueprint_get_subsystem_node",
    "macro_instance": "add_macro_instance_node",
    "spawn_actor": "add_spawn_actor_from_class_node",
    "call_function": "call_blueprint_function",
}

SET_PIN_COMMANDS = {
    "default": "set_node_pin_default",
    "value": "set_node_pin_value",
}


def route_for(tool_name: str) -> tuple[int, str]:
    return TOOL_ROUTES[tool_name]

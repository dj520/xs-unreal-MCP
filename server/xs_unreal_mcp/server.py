from __future__ import annotations

import os
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from . import __version__
from . import tools as impl

mcp = FastMCP("xs-unreal-MCP")


@mcp.tool()
def find_nodes(
    blueprint_name: str,
    graph_name: str | None = None,
    node_type: str | None = None,
    event_type: str | None = None,
) -> dict[str, Any]:
    """Find Blueprint nodes by graph, node type, or event type."""
    return impl.forward("find_nodes", locals())


@mcp.tool()
def get_pins(blueprint_name: str, node_id: str, graph_name: str | None = None) -> dict[str, Any]:
    """Get pins for one Blueprint node."""
    return impl.forward("get_pins", locals())


@mcp.tool()
def add_node(
    blueprint_name: str,
    node_type: Literal[
        "branch",
        "cast",
        "event",
        "custom_event",
        "function",
        "variable_get",
        "variable_set",
        "self_ref",
        "self_component",
        "subsystem",
        "macro_instance",
        "spawn_actor",
        "call_function",
    ],
    graph_name: str | None = None,
    node_position: list[float] | str | None = None,
    variable_name: str | None = None,
    target: str | None = None,
    function_name: str | None = None,
    params: str | dict[str, Any] | None = None,
    target_class: str | None = None,
    pure_cast: bool | None = None,
    event_name: str | None = None,
    parameters: list[dict[str, Any]] | None = None,
    macro_name: str | None = None,
    class_to_spawn: str | None = None,
    subsystem_class: str | None = None,
    component_name: str | None = None,
) -> dict[str, Any]:
    """Add one node; node_type maps to the original backend node-creation command."""
    return impl.forward_add_node(node_type, locals())


@mcp.tool()
def connect(
    blueprint_name: str,
    source_node_id: str,
    source_pin: str,
    target_node_id: str,
    target_pin: str,
    graph_name: str | None = None,
) -> dict[str, Any]:
    """Connect two Blueprint node pins."""
    return impl.forward("connect", locals())


@mcp.tool()
def disconnect(
    blueprint_name: str,
    node_id: str,
    target_graph: str = "EventGraph",
    disconnect_inputs: bool = True,
    disconnect_outputs: bool = True,
) -> dict[str, Any]:
    """Disconnect all input and/or output links from one node."""
    return impl.forward("disconnect", locals())


@mcp.tool()
def delete_node(blueprint_name: str, node_id: str, graph_name: str | None = None) -> dict[str, Any]:
    """Delete one Blueprint node."""
    return impl.forward("delete_node", locals())


@mcp.tool()
def set_pin(
    blueprint_name: str,
    node_id: str,
    pin_name: str,
    default_value: str | None = None,
    value: str | int | float | bool | None = None,
    graph_name: str | None = None,
    target_graph: str | None = None,
    mode: Literal["default", "value"] = "default",
) -> dict[str, Any]:
    """Set a node pin default literal or backend-specific pin value."""
    return impl.forward_set_pin(mode, locals())


@mcp.tool()
def replace_node(
    blueprint_name: str,
    old_node_id: str,
    new_node_type: str,
    target_graph: str = "EventGraph",
    new_node_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replace a node and return reconnection data when the backend supports it."""
    return impl.forward("replace_node", locals())


@mcp.tool()
def get_metadata(
    blueprint_name: str,
    fields: list[str],
    graph_name: str | None = None,
    node_type: str | None = None,
    event_type: str | None = None,
    component_name: str | None = None,
    detail_level: Literal["summary", "flow", "full"] | None = None,
) -> dict[str, Any]:
    """Read Blueprint metadata, including graph nodes when graph_name is provided."""
    return impl.forward("get_metadata", locals())


@mcp.tool()
def get_variable_info(blueprint_name: str, variable_name: str) -> dict[str, Any]:
    """Read metadata for one Blueprint variable."""
    return impl.forward("get_variable_info", locals())


@mcp.tool()
def add_variable(
    blueprint_name: str,
    variable_name: str,
    variable_type: str,
    is_exposed: bool | None = None,
) -> dict[str, Any]:
    """Add a Blueprint member variable."""
    return impl.forward("add_variable", locals())


@mcp.tool()
def add_component(
    blueprint_name: str,
    component_name: str,
    component_type: str,
    location: list[float] | None = None,
    rotation: list[float] | None = None,
    scale: list[float] | None = None,
    parent_component_name: str | None = None,
) -> dict[str, Any]:
    """Add a component to a Blueprint asset."""
    return impl.forward("add_component", locals())


@mcp.tool()
def compile(blueprint_name: str) -> dict[str, Any]:
    """Compile a Blueprint."""
    return impl.forward("compile", locals())


@mcp.tool()
def set_parent_class(blueprint_name: str, new_parent_class: str) -> dict[str, Any]:
    """Change a Blueprint parent class."""
    return impl.forward("set_parent_class", locals())


@mcp.tool()
def add_interface(blueprint_name: str, interface_name: str) -> dict[str, Any]:
    """Add a Blueprint interface."""
    return impl.forward("add_interface", locals())


@mcp.tool()
def spawn_actor(
    type: str,
    name: str,
    location: list[float] | None = None,
    rotation: list[float] | None = None,
    scale: list[float] | None = None,
    mesh_path: str | None = None,
) -> dict[str, Any]:
    """Spawn an actor in the active level."""
    return impl.forward("spawn_actor", locals())


@mcp.tool()
def delete_actor(name: str) -> dict[str, Any]:
    """Delete an actor by name."""
    return impl.forward("delete_actor", locals())


@mcp.tool()
def get_level(fields: list[str] | None = None, actor_filter: str | None = None) -> dict[str, Any]:
    """Read current level metadata and actor summaries."""
    return impl.forward("get_level", locals())


@mcp.tool()
def set_actor_property(
    name: str,
    property_name: str | None = None,
    value: Any | None = None,
    properties: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Set one actor property or a batch of properties."""
    return impl.forward("set_actor_property", locals())


@mcp.tool()
def set_actor_transform(
    name: str,
    location: list[float] | None = None,
    rotation: list[float] | None = None,
    scale: list[float] | None = None,
) -> dict[str, Any]:
    """Set actor location, rotation, and/or scale."""
    return impl.forward("set_actor_transform", locals())


@mcp.tool()
def auto_arrange(blueprint_name: str, graph_name: str = "EventGraph") -> dict[str, Any]:
    """Auto-arrange nodes in one Blueprint graph when supported by the graph backend."""
    return impl.forward("auto_arrange", locals())


@mcp.tool()
def cleanup_graph(
    blueprint_name: str,
    cleanup_mode: Literal["orphans", "print_strings"],
    graph_name: str = "",
    include_event_graph: bool = False,
) -> dict[str, Any]:
    """Clean a Blueprint graph using a backend-supported cleanup mode."""
    return impl.forward("cleanup_graph", locals())


if os.getenv("XS_MCP_PROFILE", "slim").lower() == "full":

    @mcp.tool()
    def raw_command(port: int, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Full-profile escape hatch for backend commands outside the 22-tool slim set."""
        from .backend import BackendError, pool

        try:
            return pool.send(port, command, params or {})
        except BackendError as exc:
            return {"status": "error", "error": str(exc), "backend_port": port, "backend_command": command}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()


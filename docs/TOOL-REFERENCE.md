# Tool Reference

Slim mode exposes exactly 22 tools.

| # | Tool | Backend command | Default port | Required inputs | Purpose |
| --- | --- | --- | --- | --- | --- |
| 1 | `find_nodes` | `find_blueprint_nodes` | `55558` | `blueprint_name` | Find nodes in a Blueprint graph. |
| 2 | `get_pins` | `get_node_pins` | `55558` | `blueprint_name`, `node_id` | Read node pins. |
| 3 | `add_node` | depends on `node_type` | `55558` | `blueprint_name`, `node_type` | Add branch, cast, event, function, variable, self, macro, or spawn nodes. |
| 4 | `connect` | `connect_blueprint_nodes` | `55558` | `blueprint_name`, source/target node and pin ids | Connect two pins. |
| 5 | `disconnect` | `disconnect_node` | `55557` | `blueprint_name`, `node_id` | Disconnect node links through the graph-manipulation backend. |
| 6 | `delete_node` | `delete_blueprint_node` | `55558` | `blueprint_name`, `node_id` | Delete a node. |
| 7 | `set_pin` | `set_node_pin_default` or `set_node_pin_value` | `55558` or `55557` | `blueprint_name`, `node_id`, `pin_name` | Set pin literal/default value. |
| 8 | `replace_node` | `replace_node` | `55557` | `blueprint_name`, `old_node_id`, `new_node_type` | Replace a node through the graph-manipulation backend. |
| 9 | `get_metadata` | `get_blueprint_metadata` | `55557` | `blueprint_name`, `fields` | Read Blueprint metadata and graph nodes. |
| 10 | `get_variable_info` | `get_variable_info` | `55557` | `blueprint_name`, `variable_name` | Read variable metadata. |
| 11 | `add_variable` | `add_blueprint_variable` | `55558` | `blueprint_name`, `variable_name`, `variable_type` | Add a Blueprint variable. |
| 12 | `add_component` | `add_component_to_blueprint` | `55557` | `blueprint_name`, `component_name`, `component_type` | Add a component to a Blueprint. |
| 13 | `compile` | `compile_blueprint` | `55558` | `blueprint_name` | Compile a Blueprint. |
| 14 | `set_parent_class` | `set_blueprint_parent_class` | `55557` | `blueprint_name`, `new_parent_class` | Change Blueprint parent class. |
| 15 | `add_interface` | `add_interface_to_blueprint` | `55557` | `blueprint_name`, `interface_name` | Add a Blueprint interface. |
| 16 | `spawn_actor` | `spawn_actor` | `55557` | `type`, `name` | Spawn an actor in the active level. |
| 17 | `delete_actor` | `delete_actor` | `55557` | `name` | Delete an actor by name. |
| 18 | `get_level` | `get_level_metadata` | `55557` | none | Read level metadata. |
| 19 | `set_actor_property` | `set_actor_property` | `55557` | `name` plus property input | Set actor property values. |
| 20 | `set_actor_transform` | `set_actor_transform` | `55557` | `name` | Set actor transform fields. |
| 21 | `auto_arrange` | `auto_arrange_nodes` | `55557` | `blueprint_name` | Auto-layout graph nodes through the graph-manipulation backend. |
| 22 | `cleanup_graph` | `cleanup_blueprint_graph` | `55557` | `blueprint_name`, `cleanup_mode` | Remove orphan or debug nodes through the graph-manipulation backend. |

## `add_node` Node Types

| `node_type` | Backend command |
| --- | --- |
| `branch` | `add_blueprint_branch_node` |
| `cast` | `add_blueprint_cast_node` |
| `event` | `add_blueprint_event_node` |
| `custom_event` | `add_blueprint_custom_event` |
| `function` | `add_blueprint_function_node` |
| `variable_get` | `add_blueprint_variable_get` |
| `variable_set` | `add_blueprint_variable_set` |
| `self_ref` | `add_blueprint_self_reference` |
| `self_component` | `add_blueprint_get_self_component_reference` |
| `subsystem` | `add_blueprint_get_subsystem_node` |
| `macro_instance` | `add_macro_instance_node` |
| `spawn_actor` | `add_spawn_actor_from_class_node` |
| `call_function` | `call_blueprint_function` |

## Notes

- `get_metadata(fields=["graph_nodes"])` requires `graph_name` on compatible
  UnrealMCP backends to keep responses bounded.
- `disconnect`, `replace_node`, `auto_arrange`, and `cleanup_graph` default to
  the UnrealMCP graph-manipulation backend on `55557` using raw JSON. If those
  commands live on another port, set `XS_MCP_GRAPH_PORT` and, when needed,
  `XS_MCP_GRAPH_PROTOCOL`.
- `set_pin(mode="default")` uses `set_node_pin_default` on `55558`;
  `mode="value"` uses `set_node_pin_value` on the graph backend (`55557` by
  default).

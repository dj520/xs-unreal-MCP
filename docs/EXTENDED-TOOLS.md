# Extended Tools

Extended profiles are generated from the latest local
`D:/project/unreal-mcp/Python` MCP server entry points that were inspected when
this package was built.

The extended tools are domain-prefixed to avoid collisions with the 22-tool
`slim` surface. For example:

- upstream `create_material` becomes `material_create_material`
- upstream `create_state_tree` becomes `statetree_create_state_tree`
- upstream `delete_asset` becomes `editor_delete_asset`

Every extended tool accepts a single optional `params` object and forwards it to
the corresponding UnrealMCP backend command on `XS_MCP_EXTENDED_PORT`, default
`55557`.

## Profiles

| Profile | Extended domains | Extended tools | Total visible tools |
| --- | --- | ---: | ---: |
| `blueprint_plus` | `blueprint`, `blueprint_action`, `node` | 28 | 51 |
| `editor_plus` | `editor`, `project`, `mesh` | 63 | 86 |
| `data_ui` | `datatable`, `font`, `project`, `umg` | 59 | 82 |
| `fx_material` | `material`, `niagara`, `sound` | 78 | 101 |
| `ai_anim` | `animation`, `pcg`, `statetree` | 73 | 96 |
| `all` / `extended` | all domains | 271 | 294 |

`full` is not an extended domain profile. It exposes the 22 slim tools plus
`raw_command`.

## Domains

| Domain | Count | Examples |
| --- | ---: | --- |
| `animation` | 9 | `animation_create_animation_blueprint`, `animation_add_anim_state`, `animation_connect_anim_graph_nodes` |
| `blueprint` | 13 | `blueprint_create_blueprint`, `blueprint_add_event_dispatcher`, `blueprint_create_custom_blueprint_function` |
| `blueprint_action` | 7 | `blueprint_action_search_blueprint_actions`, `blueprint_action_create_node_by_action_name` |
| `datatable` | 6 | `datatable_create_datatable`, `datatable_add_rows_to_datatable` |
| `editor` | 27 | `editor_delete_asset`, `editor_create_level`, `editor_execute_console_command`, `editor_start_pie` |
| `font` | 6 | `font_create_font_face`, `font_create_font` |
| `material` | 20 | `material_create_material`, `material_add_material_expression`, `material_compile_material` |
| `mesh` | 6 | `mesh_get_static_mesh_metadata`, `mesh_auto_generate_lods` |
| `niagara` | 32 | `niagara_create_niagara_system`, `niagara_add_module_to_emitter`, `niagara_spawn_niagara_actor` |
| `node` | 8 | `node_disconnect_node`, `node_replace_node`, `node_cleanup_blueprint_graph` |
| `pcg` | 10 | `pcg_create_pcg_graph`, `pcg_connect_pcg_nodes`, `pcg_execute_pcg_graph` |
| `project` | 30 | `project_create_data_asset`, `project_search_assets`, `project_capture_viewport_screenshot` |
| `sound` | 26 | `sound_import_sound_file`, `sound_create_sound_cue`, `sound_compile_metasound` |
| `statetree` | 54 | `statetree_create_state_tree`, `statetree_add_task_to_state`, `statetree_validate_all_bindings` |
| `umg` | 17 | `umg_create_umg_widget_blueprint`, `umg_add_widget_component_to_widget`, `umg_capture_widget_screenshot` |

## Command Mapping Notes

Most extended tools forward to a backend command with the same upstream name.
The validated mismatches are encoded in `extended_tools.py`:

| Extended tool | Upstream tool | Backend command |
| --- | --- | --- |
| `blueprint_set_blueprint_variable_value` | `set_blueprint_variable_value` | `set_blueprint_property` |
| `material_get_material_graph_metadata` | `get_material_graph_metadata` | `get_material_expression_metadata` |
| `niagara_add_renderer_to_emitter` | `add_renderer_to_emitter` | `add_renderer` |

## Third-Party Skill Pack

`third_party/unrealengine5-skills` contains the latest cloned
`UnrealXu/UnrealEngine5-Skills` skill pack. It is not a TCP/MCP backend; it is a
Codex skill/reference pack for UE5.6/5.7 workflows such as architecture,
Blueprint workflow, UMG/Slate, PCG building, debug validation, and module
routing.

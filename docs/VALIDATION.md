# Validation

Last local validation: 2026-06-13.

## Completed Checks

| Check | Result | Evidence |
| --- | --- | --- |
| Slim tool contract | Pass | `check_slim_tools.py` returned `tool_count=22` and the expected 22 names. |
| Python package install through `uv` | Pass | `uv --directory server run python ../scripts/check_slim_tools.py` built the package and returned 22 tools. |
| Public package audit | Pass | `audit_public_package.py` returned `public_package_audit=pass`. |
| UnrealMCP raw JSON protocol | Pass | `get_level_metadata` returned a success response from the editor backend on port `55557`. |
| UEBlueprintMCP length-prefixed protocol | Pass | `ping` returned `{"pong": true}` from the Blueprint backend on port `55558`. |
| Write loop on disposable Blueprint | Pass | `add_node(node_type="self_ref")` succeeded; `compile` returned `error_count=0`; `delete_node` removed the validation node; final `compile` returned `error_count=0`. |
| Temporary validation asset cleanup | Pass | The temporary validation Blueprint asset was removed after testing. |

## Live Editor Recheck

Rechecked after manually launching Unreal Editor on 2026-06-13:

| Check | Result | Evidence |
| --- | --- | --- |
| Editor process and ports | Pass | Unreal Editor owned listening ports `55557` and `55558`; no other client held the `55558` connection before the test. |
| Slim tool contract | Pass | `check_slim_tools.py` returned `tool_count=22`. |
| Disposable Blueprint creation | Pass | Backend created a temporary Actor Blueprint under `/Game/Blueprints`. |
| Metadata read | Pass | `get_metadata(fields=["graphs"])` returned `UserConstructionScript` and `EventGraph`. |
| Write loop | Pass | `add_node(node_type="self_ref")` returned a node id; `compile` returned `error_count=0`; `delete_node` removed the self-reference node; final `compile` returned `error_count=0`. |
| Cleanup | Pass | `delete_asset` removed the temporary Blueprint. |

## Graph Manipulation Recheck

Rechecked against the running Unreal Editor on 2026-06-13:

| Check | Result | Evidence |
| --- | --- | --- |
| Graph route defaults | Pass | `UNREAL_MCP_PORT=55557`, `BLUEPRINT_MCP_PORT=55558`, and patched `GRAPH_MCP_PORT=55557`. |
| Backend registration | Pass | Local UnrealMCP source registers `disconnect_node`, `replace_node`, `set_node_pin_value`, `auto_arrange_nodes`, and `cleanup_blueprint_graph` through `GraphManipulationCommandRegistration`. |
| `disconnect` slim route | Pass | Disposable Blueprint `BP_XSMCP_GraphOps_20260613_044209` connected Branch `then -> execute`; `disconnect` returned `total_disconnections=1` and `disconnected_pins=["execute"]`. |
| Compile after disconnect | Pass | `compile_blueprint` on port `55557` returned `success=true` and `status="compiled successfully"`. |
| `replace_node` slim route | Pass | `replace_node(old_node_id=<Branch>, new_node_type="Branch")` returned a new node id and `success=true`. |
| Compile after replace | Pass | `compile_blueprint` on port `55557` returned `success=true` and `status="compiled successfully"`. |
| Temporary graph-op asset cleanup | Pass | `delete_asset` removed `/Game/Blueprints/BP_XSMCP_GraphOps_20260613_044209`; no matching `.uasset` remained on disk. |

## Full Live Validation Recheck

Rechecked against the running Unreal Editor on 2026-06-13 with `scripts/live_validate_unreal.py`.

| Check | Result | Evidence |
| --- | --- | --- |
| Overall live suite | Partial pass | Latest local report: `generated/live_validation_20260613_060941/live_validation_20260613_060941.json`; summary was `pass=80`, `blocked=1`, `fail=1`. |
| Slim profile live operations | Pass | All 22 public slim tools were exercised through the active UE backends; graph and actor operations produced 24 pass steps including setup variations. |
| Blueprint graph operations | Pass | `connect_blueprint_nodes`, `set_node_pin_default`, `disconnect_node`, `replace_node`, `delete_blueprint_node`, `auto_arrange_nodes`, `cleanup_blueprint_graph`, and `compile_blueprint` all passed on a disposable Blueprint. |
| Actor operations | Pass | `spawn_actor`, `get_level_metadata`, `set_actor_transform`, `set_actor_property`, and `delete_actor` all passed. |
| Extended domain smoke checks | Pass | Blueprint Action, Project, DataTable, Editor, Material, Mesh, Niagara create/metadata, PCG, Sound import/cue/compile, StateTree, UMG create/component/metadata, Font, and Animation create/metadata smoke checks passed. |
| Source command audit | Fail | Current UE plugin source did not register two upstream sound commands exposed by the extended profile: `play_sound_at_location` and `set_attenuation_property`. |
| Niagara compile smoke check | Blocked | The validation script intentionally creates a minimal empty Niagara System; the backend correctly rejected compilation because required modules/renderers were missing. |

## Extended Tool Matrix

Rechecked on 2026-06-13 with `scripts/validate_extended_tool_matrix.py`.

| Check | Result | Evidence |
| --- | --- | --- |
| Extended matrix size | Pass | The matrix covered all `271` extended tools in the `all` profile. |
| Backend command coverage | Partial pass | `267` tools mapped to commands registered in the UE plugin source, `2` tools were handled by local xs adapters, and `2` tools required missing backend commands. |
| Missing backend commands | Fail | `sound_play_sound_at_location` requires `play_sound_at_location`; `sound_set_attenuation_property` requires `set_attenuation_property`. |
| Latest live-report correlation | Pass | The matrix correlated the newest live report and found `53` tools with exact live command coverage, `212` with same-domain smoke coverage, `5` not executed, and `1` blocked exact live command. |
| Execution policy classification | Pass | The matrix classified tools as `read_only_auto=64`, `safe_temp_asset=49`, `requires_fixture=126`, `unsafe_skip=21`, `manual_only=7`, `manual_review=2`, and `backend_required=2`. |

Run command:

```powershell
$env:XS_MCP_VALIDATE_UNREAL_PLUGIN='<UnrealMCP plugin Source path>'
python scripts/validate_extended_tool_matrix.py
```

## Extended Profile Checks

| Check | Result | Evidence |
| --- | --- | --- |
| `slim` profile | Pass | `check_slim_tools.py` returned `tool_count=22`. |
| `all` profile import | Pass | `XS_MCP_PROFILE=all` listed `tool_count=294`, including `material_create_material`, `statetree_create_state_tree`, and `raw_command`. |
| `fx_material` profile import | Pass | `XS_MCP_PROFILE=fx_material` listed `tool_count=101`, including Material, Niagara, and Sound tools. |
| Profile contract script | Pass | `check_profiles.py` returned `slim=22`, `full=23`, `blueprint_plus=51`, `editor_plus=86`, `data_ui=82`, `fx_material=101`, `ai_anim=96`, and `all=294`. |
| Extended source extraction | Pass | Local `D:/project/unreal-mcp` revision `ebc639c` exposed 271 upstream Python MCP tools across 15 server entry points. |
| UnrealXu skill pack import | Pass | `UnrealXu/UnrealEngine5-Skills` revision `60ac072` was copied under `third_party/unrealengine5-skills` without its `.git` directory. |
| UnrealXu skill validation | Pass | Text files in the vendored copy were normalized to LF; `validate_skills.py` returned `Validation OK`, `skills checked: 11`. |

## Notes

- A previously running standalone Blueprint MCP Python server held the single
  `55558` connection. It was stopped before validating this slim server.
- During the later graph-manipulation recheck, a standalone
  `ue_blueprint_mcp.server` process held the `55558` connection. It was left
  running because `disconnect_node` and `replace_node` are UnrealMCP commands on
  `55557`.
- The local `UnrealMCP` backend used raw JSON on `55557`; the local
  `UEBlueprintMCP` backend used length-prefixed JSON on `55558`. The server
  supports both defaults.
- `full` profile is intentionally an escape hatch through `raw_command`.
  The production token-saving path is `XS_MCP_PROFILE=slim`.

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

---
name: xs-unreal-mcp-blueprint
description: Use xs-unreal-MCP to read and edit Unreal projects through slim or extended UnrealMCP profiles. Load when the user asks to inspect Blueprint graphs, add/delete/connect nodes, set pin values, compile Blueprints, read Blueprint metadata, perform level actor edits, or use extended UE5 tools for assets, UMG, materials, Niagara, sound, PCG, Animation Blueprints, or StateTree.
---

# xs-unreal-MCP Blueprint Workflow

Use the slim tool names exposed by `xs-unreal-MCP` for common Blueprint and
level edits. The server forwards commands to Unreal Editor TCP backends and
keeps backend sockets persistent.

Extended profiles are available when the client is configured with
`XS_MCP_PROFILE=blueprint_plus`, `editor_plus`, `data_ui`, `fx_material`,
`ai_anim`, or `all`. Extended tools are domain-prefixed and accept a single
`params` object.

## Tool Selection

| Task | Use |
| --- | --- |
| Find nodes | `find_nodes` |
| Read node pins | `get_pins` |
| Add branch/cast/event/function/variable/self/macro/spawn nodes | `add_node` |
| Connect pins | `connect` |
| Disconnect or replace nodes | `disconnect`, `replace_node` when backend supports graph manipulation |
| Delete nodes | `delete_node` |
| Set pin defaults | `set_pin` |
| Read full Blueprint metadata or collapsed graph nodes | `get_metadata` |
| Add Blueprint variables/components/interfaces | `add_variable`, `add_component`, `add_interface` |
| Compile after every edit | `compile` |
| Level actor basics | `spawn_actor`, `delete_actor`, `get_level`, `set_actor_property`, `set_actor_transform` |
| Asset/project operations | `project_*` or `editor_*` tools in `editor_plus`, `data_ui`, or `all` |
| UMG widgets | `umg_*` tools in `data_ui` or `all` |
| Materials, Niagara, sound | `material_*`, `niagara_*`, `sound_*` tools in `fx_material` or `all` |
| PCG, Animation Blueprint, StateTree | `pcg_*`, `animation_*`, `statetree_*` tools in `ai_anim` or `all` |

## Extended Tool Calling

Extended tools use one wrapper parameter:

```json
{
  "params": {
    "blueprint_name": "BP_Example",
    "fields": ["components"]
  }
}
```

For example, `blueprint_get_blueprint_metadata` forwards the `params` object to
the UnrealMCP backend command `get_blueprint_metadata`.

## Discipline

1. Read the graph before editing.
2. Make one small edit first.
3. Compile immediately and require zero compile errors before continuing.
4. For deletion, inspect downstream links with `get_pins` before deleting.
5. For collapsed/composite graphs, prefer `get_metadata(fields=["graph_nodes"], graph_name="...")` when direct node tools cannot resolve the graph.

## UE 5.7 Notes

- Double math functions often use `_DoubleDouble` suffixes.
- Actor transform functions often use `K2_` prefixes.
- Pin names are case-sensitive.
- Object default values usually require `/Game/Path/Asset.Asset` object paths.
- Macro and collapsed graph lookup may require the patch in this repository.

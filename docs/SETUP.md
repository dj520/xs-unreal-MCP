# Setup

This guide installs the slim MCP facade and connects it to Unreal Editor
backends. The backend plugins are not redistributed in this repository; obtain
them separately from their original sources and review their license status.

## 1. Prerequisites

- Unreal Engine project with compatible MCP backend plugins enabled.
- Python 3.10 or newer.
- `uv` recommended, or a standard Python virtual environment.
- MCP client such as Claude Code, Codex, or another stdio MCP-capable client.

Expected backend ports:

| Backend | Default port | Role |
| --- | --- | --- |
| UnrealMCP | `55557` | Raw JSON, one request per connection | Editor, level, and Blueprint asset commands. |
| UEBlueprintMCP | `55558` | 4-byte length-prefixed JSON, persistent connection | Blueprint graph node read/write and compile commands. |

Both ports should be hosted by the running Unreal Editor process.

## 2. Apply the Graph Lookup Patch

If your `UEBlueprintMCP` source does not already support MacroGraphs and
collapsed graph lookup, apply the patch from this repository.

```powershell
cd <YourUnrealProject>/Plugins/UEBlueprintMCP
git apply D:/xs-unreal-MCP/patches/macrographs-composite-support.patch
```

The patch touches:

- `Source/UEBlueprintMCP/Private/MCPCommonUtils.cpp`
- `Source/UEBlueprintMCP/Private/Actions/EditorAction.cpp`

It adds MacroGraphs lookup and recursive collapsed graph lookup. It is a diff
only; it does not redistribute the full backend source.

## 3. Rebuild the Unreal Project or Plugin

Use your normal Unreal build command. A typical Windows command is:

```powershell
"&<UE_ROOT>/Engine/Build/BatchFiles/Build.bat" <ProjectName>Editor Win64 Development -Project="<YourUnrealProject>/<ProjectName>.uproject" -WaitMutex
```

Close Unreal Editor before rebuilding if Windows reports locked DLL or PDB
files.

## 4. Install the Slim Server

Recommended `uv` flow:

```powershell
cd D:/xs-unreal-MCP/server
uv sync
uv run xs-unreal-mcp
```

Standard virtual environment flow:

```powershell
cd D:/xs-unreal-MCP/server
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\xs-unreal-mcp
```

## 5. Configure Your MCP Client

Copy `.mcp.json.example` into your client configuration and adjust the path if
you installed the repository somewhere else.

```json
{
  "mcpServers": {
    "xs-unreal": {
      "command": "uv",
      "args": ["--directory", "D:/xs-unreal-MCP/server", "run", "xs-unreal-mcp"],
      "env": {
        "XS_MCP_PROFILE": "slim",
        "XS_MCP_HOST": "127.0.0.1",
        "XS_MCP_UNREAL_PORT": "55557",
        "XS_MCP_BLUEPRINT_PORT": "55558",
        "XS_MCP_GRAPH_PORT": "55557",
        "XS_MCP_UNREAL_PROTOCOL": "raw",
        "XS_MCP_BLUEPRINT_PROTOCOL": "length",
        "XS_MCP_GRAPH_PROTOCOL": "raw"
      }
    }
  }
}
```

On the validated UnrealMCP backend, graph-manipulation commands such as
`disconnect_node` and `replace_node` live on `55557` and use raw JSON. If your
graph-manipulation commands live on another backend, change `XS_MCP_GRAPH_PORT`.
If that backend uses a different wire format, also set `XS_MCP_GRAPH_PROTOCOL`
to `raw` or `length`.

## 6. Verify the Slim Tool Contract

```powershell
cd D:/xs-unreal-MCP
uv --directory server run python ../scripts/check_slim_tools.py
```

Expected:

```text
tool_count=22
find_nodes
...
cleanup_graph
```

## 7. Verify Against a Running Editor

After Unreal Editor is open and the backend ports are listening, run a small
write loop through your MCP client on a disposable test Blueprint:

1. `add_node` with `node_type="self_ref"`.
2. `compile` and confirm backend reports zero compile errors.
3. `delete_node` using the node id returned by step 1.
4. `compile` again and confirm zero compile errors.

Do not run the write loop on production Blueprints until the disposable test
passes.

## 8. Single-Connection Note

Some Blueprint backends accept only one active TCP client at a time. The slim
server keeps the length-prefixed Blueprint socket persistent and reuses it
across tool calls. Avoid running a second raw socket driver against the same
port while the MCP server is connected.

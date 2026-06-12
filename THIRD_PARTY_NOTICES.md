# Third Party Notices

This repository contains only an original slim MCP facade, documentation,
configuration templates, scripts, and patch files.

It does not redistribute the full source code, binaries, assets, Python backend
packages, or game project content of any Unreal Engine MCP backend plugin.

## Backend Plugins

The facade expects compatible Unreal Editor TCP backends to be installed by the
user in their own Unreal project.

Known compatible backend families:

| Backend | Typical role | Notice |
| --- | --- | --- |
| UEBlueprintMCP | Blueprint graph read/write and compile commands on TCP port 55558 | Source and copyright belong to its original authors. Obtain it from the original upstream source and review its license status before redistribution. |
| UnrealMCP | Editor, level, and Blueprint asset commands on TCP port 55557 | Source and copyright belong to its original authors. Obtain it from the original upstream source and review its license status before redistribution. |

The patch in `patches/` is distributed as an incremental diff for users who
already have the corresponding backend source.


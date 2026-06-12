from __future__ import annotations

import asyncio
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server"))
sys.path.insert(0, ROOT)
os.environ["XS_MCP_PROFILE"] = "slim"

from xs_unreal_mcp.router import SLIM_TOOL_NAMES  # noqa: E402
from xs_unreal_mcp.server import mcp  # noqa: E402


async def main() -> int:
    tools = await mcp.list_tools()
    names = [tool.name for tool in tools]
    print(f"tool_count={len(names)}")
    for name in names:
        print(name)
    if names != SLIM_TOOL_NAMES:
        print("ERROR: tool list does not match slim contract", file=sys.stderr)
        print(f"expected={SLIM_TOOL_NAMES}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

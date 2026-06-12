from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / "server"

EXPECTED_COUNTS = {
    "slim": 22,
    "full": 23,
    "blueprint_plus": 51,
    "editor_plus": 86,
    "data_ui": 82,
    "fx_material": 101,
    "ai_anim": 96,
    "all": 294,
}

CODE = r"""
import asyncio
import sys

sys.path.insert(0, {server_root!r})
from xs_unreal_mcp.server import mcp  # noqa: E402

async def main() -> None:
    tools = await mcp.list_tools()
    print(len(tools))

asyncio.run(main())
"""


def count_tools(profile: str) -> int:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["XS_MCP_PROFILE"] = profile
    code = CODE.format(server_root=str(SERVER_ROOT))
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip().splitlines()[-1])


def main() -> int:
    for profile, expected in EXPECTED_COUNTS.items():
        actual = count_tools(profile)
        print(f"{profile}={actual}")
        if actual != expected:
            print(f"ERROR: expected {expected} tools for {profile}, got {actual}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

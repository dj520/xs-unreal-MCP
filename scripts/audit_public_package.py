from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_EXTENSIONS = {".uasset"}
FORBIDDEN_PARTS = {
    "Binaries",
    "Intermediate",
    "DerivedDataCache",
}
FORBIDDEN_TEXT = [
    "".join(["D:/", "Xs", "Game", "_Sc", "_dev08"]),
    "".join(["D:\\", "Xs", "Game", "_Sc", "_dev08"]),
    "".join(["B_", "Survival", "Player", "Controller"]),
    "".join(["Survival", "Code"]),
]


def main() -> int:
    failures: list[str] = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if any(part in FORBIDDEN_PARTS for part in rel.parts):
            failures.append(f"forbidden path segment: {rel}")
        if path.suffix.lower() in FORBIDDEN_EXTENSIONS:
            failures.append(f"forbidden asset extension: {rel}")
        if path.is_file() and path.suffix.lower() in {".md", ".py", ".toml", ".txt", ".example", ".patch", ".json"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for needle in FORBIDDEN_TEXT:
                if needle in text:
                    failures.append(f"forbidden private text '{needle}' in {rel}")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    print("public_package_audit=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

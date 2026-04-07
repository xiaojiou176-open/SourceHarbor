#!/usr/bin/env python3
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from common import repo_root

FORBIDDEN_SUBSTRINGS = {
    "httpx",
    "requests",
    "aiohttp",
    "os.getenv",
    "os.environ",
    "subprocess",
    "socket",
}


def main() -> int:
    root = repo_root()
    contract_root = root / "contracts"
    errors: list[str] = []

    if not contract_root.is_dir():
        errors.append("contracts directory missing")
        print("[contract-locality] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    # Contracts are currently a thin schema surface in this repository, not a
    # fully documented sub-product. Keep the gate focused on the actual truth
    # source instead of requiring per-module companion docs that the public
    # navigation deliberately does not expose.
    required_paths = (contract_root / "source" / "openapi.yaml",)
    for required in required_paths:
        if not required.is_file():
            errors.append(
                f"contracts missing required file: {required.relative_to(root).as_posix()}"
            )

    for path in contract_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".json", ".yaml", ".yml"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for substring in FORBIDDEN_SUBSTRINGS:
            if substring in content:
                errors.append(
                    f"{path.relative_to(root).as_posix()} references forbidden runtime surface `{substring}`"
                )

    if errors:
        print("[contract-locality] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[contract-locality] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Package an ARC Phase-A handoff folder as a zip.

Usage:
  package_handoff.py <handoff_dir> <output_zip>
"""
import sys
import zipfile
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        print("usage: package_handoff.py <handoff_dir> <output_zip>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    out = Path(sys.argv[2])
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 1
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(root.parent))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

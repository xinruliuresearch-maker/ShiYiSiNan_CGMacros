from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=r"D:\ai for science")
    args = parser.parse_args()
    root = Path(args.repo_root)
    subprocess.run([sys.executable, str(root / "scripts" / "run_npj_digital_medicine_p0_workup.py")], check=True, cwd=root)
    subprocess.run([sys.executable, str(root / "scripts" / "run_npj_digital_medicine_p0_extensions.py")], check=True, cwd=root)


if __name__ == "__main__":
    main()

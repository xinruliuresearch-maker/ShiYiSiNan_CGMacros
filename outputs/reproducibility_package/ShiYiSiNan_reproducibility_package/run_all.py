# -*- coding: utf-8 -*-
"""Run all analysis scripts in numeric order."""

from pathlib import Path
import argparse
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / 'scripts'

def numeric_prefix(name):
    try:
        return int(str(name).split('_', 1)[0])
    except Exception:
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--end', type=int, default=13)
    parser.add_argument('--skip-external', action='store_true')
    args = parser.parse_args()

    selected = []
    for path in sorted(SCRIPTS.glob('*.py')):
        n = numeric_prefix(path.name)
        if n is None:
            continue
        if n < args.start or n > args.end:
            continue
        if args.skip_external and 'external' in path.name.lower():
            continue
        selected.append(path)

    if not selected:
        print('No scripts selected.')
        return

    for script in selected:
        print('=' * 90)
        print('Running:', script.name)
        print('=' * 90)
        result = subprocess.run([sys.executable, str(script)], cwd=str(ROOT))
        if result.returncode != 0:
            raise SystemExit(result.returncode)

    print('All selected scripts completed.')

if __name__ == '__main__':
    main()

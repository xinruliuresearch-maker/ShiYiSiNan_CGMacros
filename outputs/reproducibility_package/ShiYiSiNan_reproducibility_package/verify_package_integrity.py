# -*- coding: utf-8 -*-
"""Verify SHA256 checksums for this package."""

from pathlib import Path
import csv
import hashlib
import sys

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'checksums' / 'sha256_manifest.csv'

def sha256_file(path, block_size=1024 * 1024):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while True:
            block = f.read(block_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()

def main():
    if not MANIFEST.exists():
        print('Missing manifest:', MANIFEST)
        sys.exit(1)

    failures = []
    checked = 0

    with MANIFEST.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rel = row['relative_path']
            expected = row['sha256']
            path = ROOT / rel
            if not path.exists():
                failures.append((rel, 'missing'))
                continue
            observed = sha256_file(path)
            checked += 1
            if observed != expected:
                failures.append((rel, 'checksum_mismatch'))

    if failures:
        print('Integrity check failed:')
        for rel, reason in failures:
            print(' -', rel, reason)
        sys.exit(1)

    print(f'Integrity check passed for {checked} files.')

if __name__ == '__main__':
    main()

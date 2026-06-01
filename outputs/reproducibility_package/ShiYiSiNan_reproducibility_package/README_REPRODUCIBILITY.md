# ShiYiSiNan Reproducibility Package

This package supports reproducibility of the diet-to-physiology modeling analysis.

## Contents

- Analysis scripts
- Aggregate result tables
- Figures
- Software environment files
- Run-order documentation
- Data availability notes
- SHA256 checksums and file manifests

## Package mode

This package was generated in mode: public

Public mode excludes raw datasets, XML files, row-level prediction records, tokens, and local credentials.

## Not included

The following files are intentionally not included:

- Raw CGMacros files
- Raw OhioT1DM XML files
- Kaggle credentials
- API tokens
- Local .env files
- Row-level prediction records in public mode

## Minimal workflow

1. Create or activate the Python environment.
2. Obtain CGMacros and OhioT1DM from their original sources.
3. Place raw data according to DATA_AVAILABILITY.md.
4. Run scripts in the order described in RUN_ORDER.md.
5. Compare regenerated aggregate outputs with the included tables and manifests.

## Windows command

Run from the project root:

powershell -ExecutionPolicy Bypass -File .\run_all_windows.ps1

## Python command

Run from the project root:

python run_all.py

## Integrity check

Run from the package directory:

python verify_package_integrity.py

Generated at: 2026-06-01T17:28:21.581185

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

print("Project root:", ROOT)
print("Raw data dir:", RAW)

csv_files = list(RAW.rglob("*.csv"))
print(f"\nFound {len(csv_files)} CSV files")

print("\nFirst 20 CSV files:")
for f in csv_files[:20]:
    print(f.relative_to(RAW))

main_files = [
    f for f in csv_files
    if "CGMacros" in f.name and "DataDictionary" not in f.name
]

print("\nMain participant files:")
for f in main_files[:10]:
    print(f.relative_to(RAW))

print(f"\nTotal main participant files: {len(main_files)}")

if main_files:
    df = pd.read_csv(main_files[0])
    print("\nExample file:", main_files[0])
    print("\nHead:")
    print(df.head())
    print("\nColumns:")
    print(df.columns.tolist())
    print("\nShape:")
    print(df.shape)

for name in ["bio.csv", "microbes.csv", "gut_health_test.csv"]:
    matches = list(RAW.rglob(name))
    if matches:
        print(f"\n{name}: {matches[0]}")
        temp = pd.read_csv(matches[0])
        print(temp.head())
        print("Columns:", temp.columns.tolist())
        print("Shape:", temp.shape)
    else:
        print(f"\n{name} not found")
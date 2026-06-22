from pathlib import Path
import re

import pandas as pd
from huggingface_hub import snapshot_download

YEARS = [2022, 2023, 2024, 2025]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

patterns = ["officeqa_pro.csv"]
patterns.extend(
    f"treasury_bulletins_parsed/transformed/treasury_bulletin_{year}_*.txt"
    for year in YEARS
)

print("Downloading OfficeQA answer key and 2022-2025 transformed TXT files...")
print("Allow patterns:")
for pattern in patterns:
    print("  -", pattern)

snapshot_path = snapshot_download(
    repo_id="databricks/officeqa",
    repo_type="dataset",
    allow_patterns=patterns,
    local_dir=RAW_DIR,
)

print("\nDownloaded to:")
print(snapshot_path)

csv_path = RAW_DIR / "officeqa_pro.csv"
txt_dir = RAW_DIR / "treasury_bulletins_parsed" / "transformed"

df = pd.read_csv(csv_path)

year_pattern = re.compile(r"treasury_bulletin_(2022|2023|2024|2025)_\d{2}\.txt")
filtered = df[df["source_files"].astype(str).str.contains(year_pattern, regex=True)].copy()

out_csv = PROCESSED_DIR / "officeqa_pro_2022_2025.csv"
filtered.to_csv(out_csv, index=False)

txt_files = sorted(txt_dir.glob("treasury_bulletin_*.txt"))

print("\nSummary")
print("-------")
print(f"Raw answer key rows: {len(df)}")
print(f"Filtered 2022-2025 answer key rows: {len(filtered)}")
print(f"Downloaded TXT files: {len(txt_files)}")
print(f"Filtered answer key saved to: {out_csv}")

print("\nFirst 5 filtered questions:")
if len(filtered) == 0:
    print("No filtered questions found. We need to adjust the year filter.")
else:
    print(filtered[["uid", "question", "answer", "source_files", "difficulty"]].head(5).to_string(index=False))

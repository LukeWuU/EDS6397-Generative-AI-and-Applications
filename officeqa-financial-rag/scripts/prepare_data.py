from pathlib import Path
import re

import pandas as pd
from huggingface_hub import snapshot_download

YEARS = list(range(2010, 2026))
YEAR_SET = set(YEARS)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

patterns = ["officeqa_pro.csv"]
patterns.extend(
    f"treasury_bulletins_parsed/transformed/treasury_bulletin_{year}_*.txt"
    for year in YEARS
)

print("Downloading OfficeQA answer key and 2010-2025 transformed TXT files...")
print(f"Year window: {YEARS[0]}-{YEARS[-1]}")
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

file_pattern = re.compile(r"treasury_bulletin_(\d{4})_(\d{2})\.txt")

def extract_source_files(value):
    text = str(value)
    return [f"treasury_bulletin_{year}_{month}.txt" for year, month in file_pattern.findall(text)]

def extract_source_years(value):
    return sorted({int(year) for year, month in file_pattern.findall(str(value))})

def all_source_files_in_year_window(value):
    years = extract_source_years(value)
    return bool(years) and all(year in YEAR_SET for year in years)

df["source_file_list"] = df["source_files"].apply(extract_source_files)
df["source_years"] = df["source_files"].apply(extract_source_years)
df["all_sources_in_2010_2025"] = df["source_files"].apply(all_source_files_in_year_window)

filtered = df[df["all_sources_in_2010_2025"]].copy()

out_csv = PROCESSED_DIR / "officeqa_eval_2010_2025.csv"
filtered.to_csv(out_csv, index=False)

txt_files = sorted(txt_dir.glob("treasury_bulletin_*.txt"))
txt_files_in_window = [
    path for path in txt_files
    if path.name.startswith("treasury_bulletin_")
    and int(path.name.split("_")[2]) in YEAR_SET
]

print("\nSummary")
print("-------")
print(f"Raw answer key rows: {len(df)}")
print(f"Strict 2010-2025 answer key rows: {len(filtered)}")
print(f"Downloaded TXT files in 2010-2025 window: {len(txt_files_in_window)}")
print(f"Filtered answer key saved to: {out_csv}")

print("\nFirst 10 strict 2010-2025 questions:")
if len(filtered) == 0:
    print("No filtered questions found. We need to adjust the year filter.")
else:
    print(filtered[["uid", "question", "answer", "source_files", "difficulty", "source_years"]].head(10).to_string(index=False))

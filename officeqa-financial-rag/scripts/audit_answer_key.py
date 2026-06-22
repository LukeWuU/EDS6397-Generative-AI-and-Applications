from pathlib import Path
import re
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "raw" / "officeqa_pro.csv"

TARGET_YEARS = set(range(2022, 2026))

file_pattern = re.compile(r"treasury_bulletin_(\d{4})_(\d{2})\.txt")

def extract_files(value):
    text = str(value)
    return file_pattern.findall(text)

def extract_years(value):
    return sorted({int(year) for year, month in extract_files(value)})

def all_files_in_target(value):
    years = extract_years(value)
    return bool(years) and all(year in TARGET_YEARS for year in years)

def any_file_in_target(value):
    years = extract_years(value)
    return any(year in TARGET_YEARS for year in years)

df = pd.read_csv(CSV_PATH)
df["source_years"] = df["source_files"].apply(extract_years)
df["any_2022_2025"] = df["source_files"].apply(any_file_in_target)
df["all_2022_2025"] = df["source_files"].apply(all_files_in_target)

any_df = df[df["any_2022_2025"]].copy()
strict_df = df[df["all_2022_2025"]].copy()
problem_df = any_df[~any_df["all_2022_2025"]].copy()

print("Answer Key Audit")
print("================")
print(f"Total answer key rows: {len(df)}")
print(f"Rows with ANY 2022-2025 source file: {len(any_df)}")
print(f"Rows with ALL source files inside 2022-2025: {len(strict_df)}")
print(f"Rows that partially overlap 2022-2025 but also need older files: {len(problem_df)}")

print("\nStrict 2022-2025 questions:")
if len(strict_df) == 0:
    print("None")
else:
    print(strict_df[["uid", "question", "answer", "source_files", "difficulty", "source_years"]].to_string(index=False))

print("\nProblem rows to exclude from strict 2022-2025 evaluation:")
if len(problem_df) == 0:
    print("None")
else:
    print(problem_df[["uid", "answer", "source_files", "source_years"]].to_string(index=False))

print("\nCounts if we expand the year window:")
for start_year in [2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2010]:
    year_window = set(range(start_year, 2026))

    def all_in_window(value):
        years = extract_years(value)
        return bool(years) and all(year in year_window for year in years)

    count = df["source_files"].apply(all_in_window).sum()
    print(f"{start_year}-2025: {count} fully answerable rows")

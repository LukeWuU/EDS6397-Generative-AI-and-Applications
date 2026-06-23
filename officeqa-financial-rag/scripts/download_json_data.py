from pathlib import Path
import json

from huggingface_hub import snapshot_download


YEARS = list(range(2010, 2026))

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
JSON_DIR = RAW_DIR / "treasury_bulletins_parsed" / "jsons"

patterns = [
    f"treasury_bulletins_parsed/jsons/treasury_bulletin_{year}_*.json"
    for year in YEARS
]

print("Downloading OfficeQA parsed JSON files for 2010-2025...")
print("Allow patterns:")
for pattern in patterns:
    print("  -", pattern)

snapshot_path = snapshot_download(
    repo_id="databricks/officeqa",
    repo_type="dataset",
    allow_patterns=patterns,
    local_dir=RAW_DIR,
)

json_files = sorted(JSON_DIR.glob("treasury_bulletin_*.json"))

print("\nJSON Download Summary")
print("=====================")
print(f"Downloaded to: {snapshot_path}")
print(f"JSON files found: {len(json_files)}")

print("\nFirst 10 JSON files:")
for path in json_files[:10]:
    print("  -", path.name)

sample_path = JSON_DIR / "treasury_bulletin_2025_06.json"
if not sample_path.exists() and json_files:
    sample_path = json_files[-1]

print("\nSample JSON inspection")
print("======================")
print(f"Sample file: {sample_path.name}")

with sample_path.open("r", encoding="utf-8") as file:
    data = json.load(file)

print(f"Top-level type: {type(data).__name__}")

if isinstance(data, dict):
    print("Top-level keys:")
    for key in list(data.keys())[:20]:
        print(f"  - {key}")

    for key, value in data.items():
        print(f"\nFirst nested item under key: {key}")
        print(f"Nested type: {type(value).__name__}")

        if isinstance(value, list):
            print(f"List length: {len(value)}")
            if value:
                first = value[0]
                print(f"First item type: {type(first).__name__}")
                if isinstance(first, dict):
                    print("First item keys:")
                    for nested_key in list(first.keys())[:20]:
                        print(f"  - {nested_key}")
                else:
                    print(str(first)[:500])
            break

        if isinstance(value, dict):
            print("Nested dict keys:")
            for nested_key in list(value.keys())[:20]:
                print(f"  - {nested_key}")
            break

elif isinstance(data, list):
    print(f"Top-level list length: {len(data)}")
    if data:
        first = data[0]
        print(f"First item type: {type(first).__name__}")
        if isinstance(first, dict):
            print("First item keys:")
            for key in list(first.keys())[:30]:
                print(f"  - {key}")
        else:
            print(str(first)[:500])
else:
    print(str(data)[:500])

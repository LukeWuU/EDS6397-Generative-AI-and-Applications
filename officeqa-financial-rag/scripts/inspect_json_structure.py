from pathlib import Path
import json
from collections import Counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JSON_DIR = PROJECT_ROOT / "data" / "raw" / "treasury_bulletins_parsed" / "jsons"

SAMPLE_PATH = JSON_DIR / "treasury_bulletin_2025_06.json"

if not SAMPLE_PATH.exists():
    json_files = sorted(JSON_DIR.glob("treasury_bulletin_*.json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {JSON_DIR}")
    SAMPLE_PATH = json_files[-1]

print("Detailed JSON Structure Inspection")
print("==================================")
print(f"Sample file: {SAMPLE_PATH.name}")

with SAMPLE_PATH.open("r", encoding="utf-8") as file:
    data = json.load(file)

document = data.get("document", {})
elements = document.get("elements", [])
pages = document.get("pages", [])
metadata = data.get("metadata", {})

print("\nTop-level keys:")
for key in data.keys():
    print(f"  - {key}")

print("\nDocument keys:")
for key in document.keys():
    print(f"  - {key}")

print("\nMetadata keys:")
if isinstance(metadata, dict):
    for key in metadata.keys():
        print(f"  - {key}")
else:
    print(f"metadata type: {type(metadata).__name__}")

print("\nElements summary")
print("----------------")
print(f"Elements type: {type(elements).__name__}")
print(f"Elements count: {len(elements)}")

if elements:
    type_counter = Counter()
    key_counter = Counter()

    for element in elements:
        if isinstance(element, dict):
            element_type = element.get("type") or element.get("category") or element.get("element_type") or "UNKNOWN"
            type_counter[str(element_type)] += 1
            key_counter.update(element.keys())

    print("\nMost common element types:")
    for element_type, count in type_counter.most_common(20):
        print(f"  - {element_type}: {count}")

    print("\nMost common element keys:")
    for key, count in key_counter.most_common(30):
        print(f"  - {key}: {count}")

    print("\nFirst 5 elements:")
    for i, element in enumerate(elements[:5], start=1):
        print(f"\nElement {i}")
        print(f"Type: {type(element).__name__}")

        if isinstance(element, dict):
            for key, value in element.items():
                value_text = str(value)
                if len(value_text) > 500:
                    value_text = value_text[:500] + "..."
                print(f"  {key}: {value_text}")
        else:
            print(str(element)[:500])

print("\nPages summary")
print("-------------")
print(f"Pages type: {type(pages).__name__}")
print(f"Pages count: {len(pages)}")

if pages:
    print("\nFirst page item:")
    first_page = pages[0]
    print(f"Type: {type(first_page).__name__}")

    if isinstance(first_page, dict):
        for key, value in first_page.items():
            value_text = str(value)
            if len(value_text) > 500:
                value_text = value_text[:500] + "..."
            print(f"  {key}: {value_text}")
    else:
        print(str(first_page)[:500])

from pathlib import Path

from officeqa_rag.json_loader import (
    build_json_chunks,
    json_chunks_to_dataframe,
    load_json_elements,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

JSON_DIR = PROJECT_ROOT / "data" / "raw" / "treasury_bulletins_parsed" / "jsons"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_json_2010_2025.csv"


def main() -> None:
    elements = load_json_elements(JSON_DIR, start_year=2010, end_year=2025)

    chunks = build_json_chunks(
        elements,
        chunk_size_words=350,
        overlap_elements=3,
    )

    chunk_df = json_chunks_to_dataframe(chunks)
    chunk_df.to_csv(OUTPUT_PATH, index=False)

    print("JSON Chunk Build Summary")
    print("========================")
    print(f"Loaded content-bearing JSON elements: {len(elements)}")
    print(f"Created JSON-aware chunks: {len(chunk_df)}")
    print("Chunk strategy: consecutive JSON elements up to about 350 words with 3-element overlap")
    print("Metadata columns: file_name, year, month, chunk_index, page_ids, element_types")
    print(f"Saved JSON chunks to: {OUTPUT_PATH}")

    print("\nFirst 10 JSON chunks:")
    print(
        chunk_df[
            [
                "chunk_id",
                "file_name",
                "year",
                "month",
                "chunk_index",
                "page_ids",
                "element_types",
            ]
        ].head(10).to_string(index=False)
    )


if __name__ == "__main__":
    main()

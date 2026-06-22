from pathlib import Path

from officeqa_rag.data_loader import (
    build_chunks,
    chunks_to_dataframe,
    load_answer_key,
    load_txt_documents,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TXT_DIR = PROJECT_ROOT / "data" / "raw" / "treasury_bulletins_parsed" / "transformed"
ANSWER_KEY_PATH = PROJECT_ROOT / "data" / "processed" / "officeqa_eval_2010_2025.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_baseline_2010_2025.csv"


def main() -> None:
    answer_key = load_answer_key(ANSWER_KEY_PATH)
    documents = load_txt_documents(TXT_DIR, start_year=2010, end_year=2025)

    chunks = build_chunks(
        documents,
        chunk_words=350,
        overlap_words=80,
    )

    chunk_df = chunks_to_dataframe(chunks)
    chunk_df.to_csv(OUTPUT_PATH, index=False)

    print("Chunk Build Summary")
    print("===================")
    print(f"Evaluation questions: {len(answer_key)}")
    print(f"Loaded TXT documents: {len(documents)}")
    print(f"Created baseline chunks: {len(chunk_df)}")
    print(f"Chunk strategy: 350 words with 80-word overlap")
    print(f"Metadata columns: file_name, year, month, chunk_index")
    print(f"Saved chunks to: {OUTPUT_PATH}")

    print("\nFirst 5 chunks:")
    print(
        chunk_df[
            ["chunk_id", "file_name", "year", "month", "chunk_index"]
        ].head(5).to_string(index=False)
    )


if __name__ == "__main__":
    main()

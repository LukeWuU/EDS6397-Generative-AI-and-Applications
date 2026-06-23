from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RESULTS_DIR = PROJECT_ROOT / "results"
DOCS_DIR = PROJECT_ROOT / "docs"

OUTPUT_CSV_PATH = RESULTS_DIR / "txt_json_rag_comparison.csv"
OUTPUT_MD_PATH = DOCS_DIR / "txt_json_rag_comparison.md"


def read_one_row(path: Path) -> dict:
    df = pd.read_csv(path)

    if len(df) != 1:
        raise ValueError(f"Expected exactly one row in {path}, found {len(df)}")

    return df.iloc[0].to_dict()


def clean_generator_row(row: dict) -> dict:
    cleaned = dict(row)
    cleaned.pop("system", None)
    return cleaned


def main() -> None:
    txt_baseline_retriever = read_one_row(RESULTS_DIR / "baseline_retriever_summary.csv")
    txt_engineered_retriever = read_one_row(RESULTS_DIR / "engineered_retriever_summary.csv")

    json_baseline_retriever = read_one_row(RESULTS_DIR / "json_baseline_retriever_summary.csv")
    json_engineered_retriever = read_one_row(RESULTS_DIR / "json_engineered_retriever_summary.csv")

    txt_generator = pd.read_csv(RESULTS_DIR / "generator_comparison.csv")
    json_generator = pd.read_csv(RESULTS_DIR / "json_generator_comparison.csv")

    generator_by_system = {
        row.system: clean_generator_row(row._asdict())
        for row in pd.concat([txt_generator, json_generator], ignore_index=True).itertuples(index=False)
    }

    rows = [
        {
            "system": "TXT Baseline RAG",
            "data_format": "Transformed TXT",
            "retriever_strategy": "TF-IDF unigram",
            **txt_baseline_retriever,
            **generator_by_system["Baseline RAG"],
        },
        {
            "system": "TXT Engineered RAG",
            "data_format": "Transformed TXT",
            "retriever_strategy": "TF-IDF unigram + bigram, Year/Month boost, file diversification",
            **txt_engineered_retriever,
            **generator_by_system["Engineered RAG"],
        },
        {
            "system": "JSON Baseline RAG",
            "data_format": "Parsed JSON",
            "retriever_strategy": "TF-IDF unigram over JSON-aware chunks",
            **json_baseline_retriever,
            **generator_by_system["JSON Baseline RAG"],
        },
        {
            "system": "JSON Engineered RAG",
            "data_format": "Parsed JSON",
            "retriever_strategy": "TF-IDF unigram + bigram, Year/Month boost, file diversification over JSON-aware chunks",
            **json_engineered_retriever,
            **generator_by_system["JSON Engineered RAG"],
        },
    ]

    comparison_df = pd.DataFrame(rows)

    keep_columns = [
        "system",
        "data_format",
        "retriever_strategy",
        "total_questions",
        "hit_rate_at_5",
        "mrr",
        "recall_at_5",
        "groundedness",
        "factual_accuracy",
        "hallucination_rate",
        "abstention_rate",
    ]

    comparison_df = comparison_df[keep_columns]
    comparison_df.to_csv(OUTPUT_CSV_PATH, index=False)

    markdown = []
    markdown.append("# TXT vs JSON RAG Comparison\n")
    markdown.append("This report compares the original TXT-based RAG pipeline with an optional JSON-based extension using parsed OfficeQA JSON files.\n")
    markdown.append("| System | Data Format | Questions | Hit Rate@5 | MRR | Recall@5 | Groundedness | Factual Accuracy | Hallucination Rate | Abstention Rate |")
    markdown.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")

    for row in comparison_df.itertuples(index=False):
        markdown.append(
            f"| {row.system} | {row.data_format} | {int(row.total_questions)} | "
            f"{row.hit_rate_at_5:.3f} | {row.mrr:.3f} | {row.recall_at_5:.3f} | "
            f"{row.groundedness:.3f} | {row.factual_accuracy:.3f} | "
            f"{row.hallucination_rate:.3f} | {row.abstention_rate:.3f} |"
        )

    markdown.append("")
    markdown.append("## Interpretation")
    markdown.append("- TXT Baseline RAG is the simplest retrieval setup and uses transformed TXT chunks.")
    markdown.append("- TXT Engineered RAG improves retrieval by adding bigrams, Year/Month metadata boosting, and file-level diversification.")
    markdown.append("- JSON Baseline RAG performs worse than TXT Baseline because JSON-aware chunks include more structural tokens and fragmented layout information.")
    markdown.append("- JSON Engineered RAG achieves the strongest Hit Rate@5 and Recall@5, showing that parsed JSON can help when structural metadata is paired with engineered retrieval.")
    markdown.append("- JSON Engineered RAG has lower MRR than TXT Engineered RAG, meaning it often retrieves the correct file within Top-5 but not always at rank 1.")
    markdown.append("- Hallucination Rate remains zero across all systems because the conservative generator abstains when the gold source file is not retrieved.")

    OUTPUT_MD_PATH.write_text("\n".join(markdown), encoding="utf-8")

    print("TXT vs JSON RAG Comparison")
    print("==========================")
    print(comparison_df.to_string(index=False))
    print()
    print(f"Saved CSV comparison to: {OUTPUT_CSV_PATH}")
    print(f"Saved markdown comparison to: {OUTPUT_MD_PATH}")


if __name__ == "__main__":
    main()

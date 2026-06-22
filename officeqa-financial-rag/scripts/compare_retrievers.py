from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASELINE_SUMMARY_PATH = PROJECT_ROOT / "results" / "baseline_retriever_summary.csv"
ENGINEERED_SUMMARY_PATH = PROJECT_ROOT / "results" / "engineered_retriever_summary.csv"

OUTPUT_CSV_PATH = PROJECT_ROOT / "results" / "retriever_comparison.csv"
OUTPUT_MD_PATH = PROJECT_ROOT / "docs" / "retriever_comparison.md"


def load_single_row(path: Path) -> pd.Series:
    if not path.exists():
        raise FileNotFoundError(f"Missing summary file: {path}")

    df = pd.read_csv(path)

    if len(df) != 1:
        raise ValueError(f"Expected one summary row in {path}, got {len(df)}")

    return df.iloc[0]


def main() -> None:
    baseline = load_single_row(BASELINE_SUMMARY_PATH)
    engineered = load_single_row(ENGINEERED_SUMMARY_PATH)

    rows = [
        {
            "system": "Baseline RAG",
            "retriever_design": "TF-IDF unigram search; no metadata filtering; fixed 350-word chunks with 80-word overlap",
            "total_questions": int(baseline["total_questions"]),
            "hit_rate_at_5": float(baseline["hit_rate_at_5"]),
            "mrr": float(baseline["mrr"]),
            "recall_at_5": float(baseline["recall_at_5"]),
        },
        {
            "system": "Engineered RAG",
            "retriever_design": "TF-IDF unigram+bigram search; soft Year/Month metadata boost; file-level diversification",
            "total_questions": int(engineered["total_questions"]),
            "hit_rate_at_5": float(engineered["hit_rate_at_5"]),
            "mrr": float(engineered["mrr"]),
            "recall_at_5": float(engineered["recall_at_5"]),
        },
    ]

    comparison_df = pd.DataFrame(rows)

    improvement = {
        "hit_rate_at_5_gain": comparison_df.loc[1, "hit_rate_at_5"] - comparison_df.loc[0, "hit_rate_at_5"],
        "mrr_gain": comparison_df.loc[1, "mrr"] - comparison_df.loc[0, "mrr"],
        "recall_at_5_gain": comparison_df.loc[1, "recall_at_5"] - comparison_df.loc[0, "recall_at_5"],
    }

    comparison_df.to_csv(OUTPUT_CSV_PATH, index=False)

    markdown = []
    markdown.append("# Retriever Comparison: Baseline RAG vs Engineered RAG\n")
    markdown.append("Evaluation uses the filtered OfficeQA Pro answer key for 2010-2025 with K=5.\n")
    markdown.append("| System | Retriever Design | Questions | Hit Rate@5 | MRR | Recall@5 |")
    markdown.append("|---|---|---:|---:|---:|---:|")

    for row in rows:
        markdown.append(
            "| {system} | {retriever_design} | {total_questions} | {hit:.3f} | {mrr:.3f} | {recall:.3f} |".format(
                system=row["system"],
                retriever_design=row["retriever_design"],
                total_questions=row["total_questions"],
                hit=row["hit_rate_at_5"],
                mrr=row["mrr"],
                recall=row["recall_at_5"],
            )
        )

    markdown.append("\n## Improvement")
    markdown.append(f"- Hit Rate@5 improved by {improvement['hit_rate_at_5_gain']:.3f}.")
    markdown.append(f"- MRR improved by {improvement['mrr_gain']:.3f}.")
    markdown.append(f"- Recall@5 improved by {improvement['recall_at_5_gain']:.3f}.")

    OUTPUT_MD_PATH.write_text("\n".join(markdown), encoding="utf-8")

    print("Retriever Comparison")
    print("====================")
    print(comparison_df.to_string(index=False))
    print()
    print(f"Hit Rate@5 gain: {improvement['hit_rate_at_5_gain']:.3f}")
    print(f"MRR gain: {improvement['mrr_gain']:.3f}")
    print(f"Recall@5 gain: {improvement['recall_at_5_gain']:.3f}")
    print()
    print(f"Saved CSV comparison to: {OUTPUT_CSV_PATH}")
    print(f"Saved Markdown comparison to: {OUTPUT_MD_PATH}")


if __name__ == "__main__":
    main()

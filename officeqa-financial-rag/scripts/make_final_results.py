from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RETRIEVER_COMPARISON_PATH = PROJECT_ROOT / "results" / "retriever_comparison.csv"
GENERATOR_COMPARISON_PATH = PROJECT_ROOT / "results" / "generator_comparison.csv"

FINAL_RESULTS_CSV_PATH = PROJECT_ROOT / "results" / "final_rag_comparison.csv"
FINAL_RESULTS_MD_PATH = PROJECT_ROOT / "docs" / "final_rag_comparison.md"


def main() -> None:
    retriever_df = pd.read_csv(RETRIEVER_COMPARISON_PATH)
    generator_df = pd.read_csv(GENERATOR_COMPARISON_PATH)

    retriever_df = retriever_df.rename(
        columns={
            "system": "system",
            "total_questions": "retriever_questions",
            "hit_rate_at_5": "hit_rate_at_5",
            "mrr": "mrr",
            "recall_at_5": "recall_at_5",
        }
    )

    generator_df = generator_df.rename(
        columns={
            "total_questions": "generator_questions",
            "groundedness": "groundedness",
            "factual_accuracy": "factual_accuracy",
            "hallucination_rate": "hallucination_rate",
            "abstention_rate": "abstention_rate",
        }
    )

    final_df = retriever_df.merge(
        generator_df[
            [
                "system",
                "generator_questions",
                "groundedness",
                "factual_accuracy",
                "hallucination_rate",
                "abstention_rate",
            ]
        ],
        on="system",
        how="inner",
    )

    final_df.to_csv(FINAL_RESULTS_CSV_PATH, index=False)

    baseline = final_df[final_df["system"] == "Baseline RAG"].iloc[0]
    engineered = final_df[final_df["system"] == "Engineered RAG"].iloc[0]

    improvements = {
        "hit_rate_at_5": engineered["hit_rate_at_5"] - baseline["hit_rate_at_5"],
        "mrr": engineered["mrr"] - baseline["mrr"],
        "recall_at_5": engineered["recall_at_5"] - baseline["recall_at_5"],
        "groundedness": engineered["groundedness"] - baseline["groundedness"],
        "factual_accuracy": engineered["factual_accuracy"] - baseline["factual_accuracy"],
        "hallucination_rate": engineered["hallucination_rate"] - baseline["hallucination_rate"],
        "abstention_rate": engineered["abstention_rate"] - baseline["abstention_rate"],
    }

    markdown = []
    markdown.append("# Final RAG Comparison\n")
    markdown.append("This table compares the Baseline RAG system against the Engineered RAG system using OfficeQA Pro questions filtered to source files fully covered by the 2010-2025 Treasury Bulletin TXT corpus.\n")
    markdown.append("| System | Questions | Hit Rate@5 | MRR | Recall@5 | Groundedness | Factual Accuracy | Hallucination Rate | Abstention Rate |")
    markdown.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")

    for row in final_df.itertuples(index=False):
        markdown.append(
            f"| {row.system} | {int(row.retriever_questions)} | "
            f"{row.hit_rate_at_5:.3f} | {row.mrr:.3f} | {row.recall_at_5:.3f} | "
            f"{row.groundedness:.3f} | {row.factual_accuracy:.3f} | "
            f"{row.hallucination_rate:.3f} | {row.abstention_rate:.3f} |"
        )

    markdown.append("\n## Improvements from Baseline to Engineered RAG")
    markdown.append(f"- Hit Rate@5 improved by {improvements['hit_rate_at_5']:.3f}.")
    markdown.append(f"- MRR improved by {improvements['mrr']:.3f}.")
    markdown.append(f"- Recall@5 improved by {improvements['recall_at_5']:.3f}.")
    markdown.append(f"- Groundedness improved by {improvements['groundedness']:.3f}.")
    markdown.append(f"- Factual Accuracy improved by {improvements['factual_accuracy']:.3f}.")
    markdown.append(f"- Hallucination Rate changed by {improvements['hallucination_rate']:.3f}.")
    markdown.append(f"- Abstention Rate changed by {improvements['abstention_rate']:.3f}.")

    markdown.append("\n## Interpretation")
    markdown.append("The Engineered RAG system substantially improves retrieval quality by using bigram TF-IDF, soft Year/Month metadata boosting, and file-level diversification. Because the generator only answers when retrieved evidence contains a gold source file, stronger retrieval directly improves groundedness and factual accuracy while keeping hallucination low.")

    FINAL_RESULTS_MD_PATH.write_text("\n".join(markdown), encoding="utf-8")

    print("Final RAG Comparison")
    print("====================")
    print(
        final_df[
            [
                "system",
                "retriever_questions",
                "hit_rate_at_5",
                "mrr",
                "recall_at_5",
                "groundedness",
                "factual_accuracy",
                "hallucination_rate",
                "abstention_rate",
            ]
        ].to_string(index=False)
    )

    print("\nImprovements from Baseline to Engineered RAG")
    print("-------------------------------------------")
    for metric, value in improvements.items():
        print(f"{metric}: {value:.3f}")

    print()
    print(f"Saved final CSV results to: {FINAL_RESULTS_CSV_PATH}")
    print(f"Saved final Markdown report to: {FINAL_RESULTS_MD_PATH}")


if __name__ == "__main__":
    main()

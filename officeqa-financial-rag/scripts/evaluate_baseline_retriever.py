from pathlib import Path

import pandas as pd

from officeqa_rag.metrics import (
    evaluate_retriever_row,
    metric_rows_to_dataframe,
    summarize_retriever_metrics,
)
from officeqa_rag.retriever import TfidfRetriever


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ANSWER_KEY_PATH = PROJECT_ROOT / "data" / "processed" / "officeqa_eval_2010_2025.csv"
CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_baseline_2010_2025.csv"

DETAIL_OUTPUT_PATH = PROJECT_ROOT / "results" / "baseline_retriever_details.csv"
SUMMARY_OUTPUT_PATH = PROJECT_ROOT / "results" / "baseline_retriever_summary.csv"

K = 5


def main() -> None:
    answer_key = pd.read_csv(ANSWER_KEY_PATH)
    chunks = pd.read_csv(CHUNKS_PATH)

    retriever = TfidfRetriever(
        max_features=50000,
        stop_words="english",
        ngram_range=(1, 1),
    )
    retriever.fit(chunks)

    metric_rows = []

    for row in answer_key.itertuples(index=False):
        results = retriever.search(row.question, top_k=K)

        metric_row = evaluate_retriever_row(
            uid=str(row.uid),
            question=str(row.question),
            answer=str(row.answer),
            source_files=str(row.source_files),
            results=results,
        )
        metric_rows.append(metric_row)

    detail_df = metric_rows_to_dataframe(metric_rows)
    summary = summarize_retriever_metrics(metric_rows)
    summary_df = pd.DataFrame([summary])

    detail_df.to_csv(DETAIL_OUTPUT_PATH, index=False)
    summary_df.to_csv(SUMMARY_OUTPUT_PATH, index=False)

    print("Baseline Retriever Evaluation")
    print("=============================")
    print(f"Questions evaluated: {int(summary['total_questions'])}")
    print(f"K cutoff: {K}")
    print("Retriever: TF-IDF unigram search")
    print("Metadata filter used: No")
    print()
    print(f"Hit Rate@5: {summary['hit_rate_at_5']:.3f} ({summary['hit_rate_at_5'] * 100:.1f}%)")
    print(f"MRR: {summary['mrr']:.3f}")
    print(f"Recall@5: {summary['recall_at_5']:.3f} ({summary['recall_at_5'] * 100:.1f}%)")
    print()
    print(f"Saved detail results to: {DETAIL_OUTPUT_PATH}")
    print(f"Saved summary results to: {SUMMARY_OUTPUT_PATH}")

    print("\nFirst 10 retrieval results:")
    print(
        detail_df[
            ["uid", "hit_at_5", "reciprocal_rank", "recall_at_5", "relevant_files", "retrieved_files"]
        ].head(10).to_string(index=False)
    )


if __name__ == "__main__":
    main()

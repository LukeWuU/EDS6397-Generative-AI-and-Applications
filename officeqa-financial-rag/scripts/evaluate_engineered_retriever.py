from pathlib import Path

import pandas as pd

from officeqa_rag.engineered_retriever import EngineeredTfidfRetriever, MetadataFilter
from officeqa_rag.metadata import infer_month_hints, infer_year_hints
from officeqa_rag.metrics import (
    evaluate_retriever_row,
    metric_rows_to_dataframe,
    summarize_retriever_metrics,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ANSWER_KEY_PATH = PROJECT_ROOT / "data" / "processed" / "officeqa_eval_2010_2025.csv"
CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_baseline_2010_2025.csv"

DETAIL_OUTPUT_PATH = PROJECT_ROOT / "results" / "engineered_retriever_details.csv"
SUMMARY_OUTPUT_PATH = PROJECT_ROOT / "results" / "engineered_retriever_summary.csv"

K = 5


def main() -> None:
    answer_key = pd.read_csv(ANSWER_KEY_PATH)
    chunks = pd.read_csv(CHUNKS_PATH)

    retriever = EngineeredTfidfRetriever(
        max_features=120000,
        stop_words="english",
        ngram_range=(1, 2),
        year_boost=0.12,
        month_boost=0.04,
    )
    retriever.fit(chunks)

    metric_rows = []
    metadata_debug_rows = []

    for row in answer_key.itertuples(index=False):
        year_hints = infer_year_hints(str(row.question), start_year=2010, end_year=2025)
        month_hints = infer_month_hints(str(row.question))

        metadata_filter = MetadataFilter(
            years=year_hints,
            months=month_hints,
        )

        results = retriever.search(
            str(row.question),
            top_k=K,
            metadata_filter=metadata_filter,
            candidate_pool_size=100,
        )

        metric_row = evaluate_retriever_row(
            uid=str(row.uid),
            question=str(row.question),
            answer=str(row.answer),
            source_files=str(row.source_files),
            results=results,
        )
        metric_rows.append(metric_row)

        metadata_debug_rows.append(
            {
                "uid": str(row.uid),
                "inferred_years": ", ".join(str(year) for year in sorted(year_hints)),
                "inferred_months": ", ".join(str(month) for month in sorted(month_hints)),
            }
        )

    detail_df = metric_rows_to_dataframe(metric_rows)
    metadata_debug_df = pd.DataFrame(metadata_debug_rows)
    detail_df = detail_df.merge(metadata_debug_df, on="uid", how="left")

    summary = summarize_retriever_metrics(metric_rows)
    summary_df = pd.DataFrame([summary])

    detail_df.to_csv(DETAIL_OUTPUT_PATH, index=False)
    summary_df.to_csv(SUMMARY_OUTPUT_PATH, index=False)

    print("Engineered Retriever Evaluation")
    print("===============================")
    print(f"Questions evaluated: {int(summary['total_questions'])}")
    print(f"K cutoff: {K}")
    print("Retriever: TF-IDF unigram + bigram search")
    print("Metadata strategy: soft Year/Month boost + file-level diversification")
    print()
    print(f"Hit Rate@5: {summary['hit_rate_at_5']:.3f} ({summary['hit_rate_at_5'] * 100:.1f}%)")
    print(f"MRR: {summary['mrr']:.3f}")
    print(f"Recall@5: {summary['recall_at_5']:.3f} ({summary['recall_at_5'] * 100:.1f}%)")
    print()
    print(f"Saved detail results to: {DETAIL_OUTPUT_PATH}")
    print(f"Saved summary results to: {SUMMARY_OUTPUT_PATH}")

    print("\nFirst 10 engineered retrieval results:")
    print(
        detail_df[
            [
                "uid",
                "hit_at_5",
                "reciprocal_rank",
                "recall_at_5",
                "inferred_years",
                "inferred_months",
                "relevant_files",
                "retrieved_files",
            ]
        ].head(10).to_string(index=False)
    )


if __name__ == "__main__":
    main()

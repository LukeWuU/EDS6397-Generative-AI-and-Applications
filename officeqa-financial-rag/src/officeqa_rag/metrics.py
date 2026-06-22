import re
from dataclasses import dataclass

import pandas as pd

from officeqa_rag.retriever import SearchResult


SOURCE_FILE_PATTERN = re.compile(r"treasury_bulletin_\d{4}_\d{2}\.txt")


@dataclass(frozen=True)
class RetrieverMetricRow:
    uid: str
    question: str
    answer: str
    relevant_files: list[str]
    retrieved_files: list[str]
    hit_at_5: int
    reciprocal_rank: float
    recall_at_5: float


def parse_source_files(source_files: str) -> list[str]:
    """Extract source file names from the OfficeQA source_files field."""
    return SOURCE_FILE_PATTERN.findall(str(source_files))


def evaluate_retriever_row(
    uid: str,
    question: str,
    answer: str,
    source_files: str,
    results: list[SearchResult],
) -> RetrieverMetricRow:
    relevant_files = parse_source_files(source_files)
    relevant_set = set(relevant_files)

    retrieved_files = [result.file_name for result in results]

    first_correct_rank: int | None = None
    found_relevant_files: set[str] = set()

    for result in results:
        if result.file_name in relevant_set:
            found_relevant_files.add(result.file_name)

            if first_correct_rank is None:
                first_correct_rank = result.rank

    hit_at_5 = 1 if first_correct_rank is not None else 0
    reciprocal_rank = 0.0 if first_correct_rank is None else 1.0 / first_correct_rank
    recall_at_5 = 0.0 if not relevant_set else len(found_relevant_files) / len(relevant_set)

    return RetrieverMetricRow(
        uid=uid,
        question=question,
        answer=answer,
        relevant_files=relevant_files,
        retrieved_files=retrieved_files,
        hit_at_5=hit_at_5,
        reciprocal_rank=reciprocal_rank,
        recall_at_5=recall_at_5,
    )


def summarize_retriever_metrics(rows: list[RetrieverMetricRow]) -> dict[str, float]:
    if not rows:
        raise ValueError("No metric rows to summarize.")

    return {
        "total_questions": float(len(rows)),
        "hit_rate_at_5": sum(row.hit_at_5 for row in rows) / len(rows),
        "mrr": sum(row.reciprocal_rank for row in rows) / len(rows),
        "recall_at_5": sum(row.recall_at_5 for row in rows) / len(rows),
    }


def metric_rows_to_dataframe(rows: list[RetrieverMetricRow]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "uid": row.uid,
                "question": row.question,
                "answer": row.answer,
                "relevant_files": " | ".join(row.relevant_files),
                "retrieved_files": " | ".join(row.retrieved_files),
                "hit_at_5": row.hit_at_5,
                "reciprocal_rank": row.reciprocal_rank,
                "recall_at_5": row.recall_at_5,
            }
            for row in rows
        ]
    )

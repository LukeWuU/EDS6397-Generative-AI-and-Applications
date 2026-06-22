from dataclasses import dataclass

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from officeqa_rag.retriever import SearchResult


@dataclass(frozen=True)
class MetadataFilter:
    years: set[int]
    months: set[int]


class EngineeredTfidfRetriever:
    """
    Metadata-aware TF-IDF retriever.

    Engineered behavior:
    - unigram + bigram TF-IDF
    - soft year/month metadata boosting
    - file-level diversification so Top-K covers more source files
    """

    def __init__(
        self,
        max_features: int = 120000,
        stop_words: str | None = "english",
        ngram_range: tuple[int, int] = (1, 2),
        year_boost: float = 0.12,
        month_boost: float = 0.04,
    ) -> None:
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words=stop_words,
            ngram_range=ngram_range,
            sublinear_tf=True,
        )
        self.year_boost = year_boost
        self.month_boost = month_boost
        self.chunk_df: pd.DataFrame | None = None
        self.chunk_matrix = None

    def fit(self, chunk_df: pd.DataFrame) -> None:
        required_columns = {"chunk_id", "file_name", "year", "month", "text"}
        missing = required_columns - set(chunk_df.columns)

        if missing:
            raise ValueError(f"Chunk dataframe is missing columns: {sorted(missing)}")

        self.chunk_df = chunk_df.reset_index(drop=True).copy()
        texts = self.chunk_df["text"].fillna("").astype(str).tolist()
        self.chunk_matrix = self.vectorizer.fit_transform(texts)

    def search(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: MetadataFilter | None = None,
        candidate_pool_size: int = 100,
    ) -> list[SearchResult]:
        if self.chunk_df is None or self.chunk_matrix is None:
            raise RuntimeError("Retriever must be fit before calling search().")

        query_vector = self.vectorizer.transform([query])
        base_scores = linear_kernel(query_vector, self.chunk_matrix).ravel()
        final_scores = base_scores.copy()

        if metadata_filter is not None:
            if metadata_filter.years:
                year_matches = self.chunk_df["year"].isin(metadata_filter.years).to_numpy()
                final_scores[year_matches] += self.year_boost

            if metadata_filter.months:
                month_matches = self.chunk_df["month"].isin(metadata_filter.months).to_numpy()
                final_scores[month_matches] += self.month_boost

        candidate_pool_size = max(candidate_pool_size, top_k)
        ranked_indices = final_scores.argsort()[::-1][:candidate_pool_size]

        selected_indices: list[int] = []
        selected_files: set[str] = set()

        # First pass: prefer different files.
        for row_index in ranked_indices:
            file_name = str(self.chunk_df.iloc[row_index]["file_name"])
            if file_name in selected_files:
                continue

            selected_indices.append(int(row_index))
            selected_files.add(file_name)

            if len(selected_indices) >= top_k:
                break

        # Second pass: fill remaining slots if fewer than top_k unique files were available.
        if len(selected_indices) < top_k:
            for row_index in ranked_indices:
                if int(row_index) in selected_indices:
                    continue

                selected_indices.append(int(row_index))

                if len(selected_indices) >= top_k:
                    break

        results: list[SearchResult] = []

        for rank, row_index in enumerate(selected_indices, start=1):
            row = self.chunk_df.iloc[row_index]
            results.append(
                SearchResult(
                    rank=rank,
                    score=float(final_scores[row_index]),
                    chunk_id=str(row["chunk_id"]),
                    file_name=str(row["file_name"]),
                    year=int(row["year"]),
                    month=int(row["month"]),
                    text=str(row["text"]),
                )
            )

        return results

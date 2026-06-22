from dataclasses import dataclass

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


@dataclass(frozen=True)
class SearchResult:
    rank: int
    score: float
    chunk_id: str
    file_name: str
    year: int
    month: int
    text: str


class TfidfRetriever:
    """
    Simple TF-IDF retriever.

    Baseline behavior:
    - uses text similarity only
    - does not use year/month metadata filters
    - returns top-k chunks
    """

    def __init__(
        self,
        max_features: int = 50000,
        stop_words: str | None = "english",
        ngram_range: tuple[int, int] = (1, 1),
    ) -> None:
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words=stop_words,
            ngram_range=ngram_range,
        )
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

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if self.chunk_df is None or self.chunk_matrix is None:
            raise RuntimeError("Retriever must be fit before calling search().")

        query_vector = self.vectorizer.transform([query])
        scores = linear_kernel(query_vector, self.chunk_matrix).ravel()

        top_indices = scores.argsort()[::-1][:top_k]

        results: list[SearchResult] = []

        for rank, row_index in enumerate(top_indices, start=1):
            row = self.chunk_df.iloc[row_index]
            results.append(
                SearchResult(
                    rank=rank,
                    score=float(scores[row_index]),
                    chunk_id=str(row["chunk_id"]),
                    file_name=str(row["file_name"]),
                    year=int(row["year"]),
                    month=int(row["month"]),
                    text=str(row["text"]),
                )
            )

        return results

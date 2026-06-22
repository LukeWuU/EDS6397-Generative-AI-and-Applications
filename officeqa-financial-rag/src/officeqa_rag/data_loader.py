from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

import pandas as pd


FILE_PATTERN = re.compile(r"treasury_bulletin_(\d{4})_(\d{2})\.txt")


@dataclass(frozen=True)
class TreasuryDocument:
    file_name: str
    year: int
    month: int
    text: str


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    file_name: str
    year: int
    month: int
    chunk_index: int
    text: str


def parse_year_month(file_name: str) -> tuple[int, int]:
    """Extract year and month from a Treasury Bulletin TXT file name."""
    match = FILE_PATTERN.fullmatch(file_name)
    if not match:
        raise ValueError(f"Invalid Treasury Bulletin file name: {file_name}")

    year = int(match.group(1))
    month = int(match.group(2))
    return year, month


def load_answer_key(csv_path: Path) -> pd.DataFrame:
    """Load the filtered OfficeQA answer key."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Answer key not found: {csv_path}")

    df = pd.read_csv(csv_path)
    required_columns = {"uid", "question", "answer", "source_files", "difficulty"}
    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(f"Answer key is missing columns: {sorted(missing)}")

    return df


def load_txt_documents(
    txt_dir: Path,
    start_year: int = 2010,
    end_year: int = 2025,
) -> list[TreasuryDocument]:
    """Load Treasury Bulletin TXT files within the selected year window."""
    if not txt_dir.exists():
        raise FileNotFoundError(f"TXT directory not found: {txt_dir}")

    documents: list[TreasuryDocument] = []

    for path in sorted(txt_dir.glob("treasury_bulletin_*.txt")):
        try:
            year, month = parse_year_month(path.name)
        except ValueError:
            continue

        if start_year <= year <= end_year:
            text = path.read_text(encoding="utf-8", errors="ignore")
            documents.append(
                TreasuryDocument(
                    file_name=path.name,
                    year=year,
                    month=month,
                    text=text,
                )
            )

    return documents


def split_words_into_chunks(
    text: str,
    chunk_size_words: int = 350,
    overlap_words: int = 80,
) -> list[str]:
    """
    Split text into overlapping word chunks.

    Baseline strategy:
    - fixed-size word windows
    - simple overlap
    - no table-aware parsing yet
    """
    if chunk_size_words <= 0:
        raise ValueError("chunk_size_words must be positive")

    if overlap_words < 0:
        raise ValueError("overlap_words cannot be negative")

    if overlap_words >= chunk_size_words:
        raise ValueError("overlap_words must be smaller than chunk_size_words")

    words = text.split()
    if not words:
        return []

    step = chunk_size_words - overlap_words
    chunks: list[str] = []

    for start in range(0, len(words), step):
        end = start + chunk_size_words
        chunk = " ".join(words[start:end]).strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

    return chunks


def build_chunks(
    documents: Iterable[TreasuryDocument],
    chunk_words: int = 350,
    overlap_words: int = 80,
) -> list[TextChunk]:
    """Build metadata-tagged chunks from Treasury documents."""
    all_chunks: list[TextChunk] = []

    for document in documents:
        pieces = split_words_into_chunks(
            document.text,
            chunk_size_words=chunk_words,
            overlap_words=overlap_words,
        )

        for index, piece in enumerate(pieces):
            chunk_id = f"{document.file_name}::chunk_{index:04d}"
            all_chunks.append(
                TextChunk(
                    chunk_id=chunk_id,
                    file_name=document.file_name,
                    year=document.year,
                    month=document.month,
                    chunk_index=index,
                    text=piece,
                )
            )

    return all_chunks


def chunks_to_dataframe(chunks: list[TextChunk]) -> pd.DataFrame:
    """Convert chunks to a DataFrame for indexing and evaluation."""
    return pd.DataFrame(
        [
            {
                "chunk_id": chunk.chunk_id,
                "file_name": chunk.file_name,
                "year": chunk.year,
                "month": chunk.month,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
            }
            for chunk in chunks
        ]
    )

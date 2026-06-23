from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Iterable

import pandas as pd


JSON_FILE_PATTERN = re.compile(r"treasury_bulletin_(\d{4})_(\d{2})\.json")


@dataclass(frozen=True)
class JsonElement:
    file_name: str
    year: int
    month: int
    element_id: int
    element_type: str
    page_id: int | None
    content: str


@dataclass(frozen=True)
class JsonChunk:
    chunk_id: str
    file_name: str
    year: int
    month: int
    chunk_index: int
    start_element_id: int
    end_element_id: int
    page_ids: str
    element_types: str
    text: str


def parse_json_year_month(file_name: str) -> tuple[int, int]:
    """Extract year and month from a Treasury Bulletin JSON file name."""
    match = JSON_FILE_PATTERN.fullmatch(file_name)
    if not match:
        raise ValueError(f"Invalid Treasury Bulletin JSON file name: {file_name}")

    year = int(match.group(1))
    month = int(match.group(2))
    return year, month


def extract_page_id(element: dict) -> int | None:
    """Extract the first page_id from an element bbox field."""
    bbox = element.get("bbox")

    if not isinstance(bbox, list) or not bbox:
        return None

    first_box = bbox[0]

    if not isinstance(first_box, dict):
        return None

    page_id = first_box.get("page_id")

    if page_id is None:
        return None

    try:
        return int(page_id)
    except (TypeError, ValueError):
        return None


def extract_vertical_position(element: dict) -> int:
    """Extract the top y coordinate from bbox so elements can be sorted within a page."""
    bbox = element.get("bbox")

    if not isinstance(bbox, list) or not bbox:
        return 0

    first_box = bbox[0]

    if not isinstance(first_box, dict):
        return 0

    coord = first_box.get("coord")

    if not isinstance(coord, list) or len(coord) < 2:
        return 0

    try:
        return int(coord[1])
    except (TypeError, ValueError):
        return 0


def load_json_elements(
    json_dir: Path,
    start_year: int = 2010,
    end_year: int = 2025,
) -> list[JsonElement]:
    """Load content-bearing JSON elements from parsed Treasury Bulletin JSON files."""
    if not json_dir.exists():
        raise FileNotFoundError(f"JSON directory not found: {json_dir}")

    elements: list[JsonElement] = []

    for path in sorted(json_dir.glob("treasury_bulletin_*.json")):
        try:
            year, month = parse_json_year_month(path.name)
        except ValueError:
            continue

        if not (start_year <= year <= end_year):
            continue

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        document = data.get("document", {})
        raw_elements = document.get("elements", [])

        if not isinstance(raw_elements, list):
            continue

        sortable_items = []

        for raw_element in raw_elements:
            if not isinstance(raw_element, dict):
                continue

            content = raw_element.get("content")
            if content is None:
                continue

            content_text = " ".join(str(content).split())
            if not content_text:
                continue

            element_id = raw_element.get("id", -1)
            try:
                element_id = int(element_id)
            except (TypeError, ValueError):
                element_id = -1

            element_type = str(raw_element.get("type", "unknown"))
            page_id = extract_page_id(raw_element)
            vertical_position = extract_vertical_position(raw_element)

            sortable_items.append(
                (
                    page_id if page_id is not None else 999999,
                    vertical_position,
                    element_id,
                    JsonElement(
                        file_name=path.name.replace(".json", ".txt"),
                        year=year,
                        month=month,
                        element_id=element_id,
                        element_type=element_type,
                        page_id=page_id,
                        content=content_text,
                    ),
                )
            )

        for _, _, _, element in sorted(sortable_items):
            elements.append(element)

    return elements


def element_to_text(element: JsonElement) -> str:
    """Create a text representation that keeps useful JSON structural metadata."""
    prefix = f"[type={element.element_type}]"

    if element.page_id is not None:
        prefix += f" [page={element.page_id}]"

    return f"{prefix} {element.content}"


def build_json_chunks(
    elements: Iterable[JsonElement],
    chunk_size_words: int = 350,
    overlap_elements: int = 3,
    max_pages_per_chunk: int = 2,
) -> list[JsonChunk]:
    """
    Build page-aware JSON chunks.

    Strategy:
    - preserve parsed JSON structural metadata
    - sort elements by file, page_id, vertical position, and element_id
    - avoid chunks that span too many pages
    - overlap by a few elements to preserve local continuity
    """
    if chunk_size_words <= 0:
        raise ValueError("chunk_size_words must be positive")

    if overlap_elements < 0:
        raise ValueError("overlap_elements cannot be negative")

    if max_pages_per_chunk <= 0:
        raise ValueError("max_pages_per_chunk must be positive")

    elements_by_file: dict[str, list[JsonElement]] = {}

    for element in elements:
        elements_by_file.setdefault(element.file_name, []).append(element)

    all_chunks: list[JsonChunk] = []

    for file_name, file_elements in sorted(elements_by_file.items()):
        file_elements = sorted(
            file_elements,
            key=lambda item: (
                item.page_id if item.page_id is not None else 999999,
                item.element_id,
            ),
        )

        if not file_elements:
            continue

        year = file_elements[0].year
        month = file_elements[0].month

        chunk_index = 0
        start_index = 0

        while start_index < len(file_elements):
            current_elements: list[JsonElement] = []
            current_word_count = 0
            current_pages: set[int] = set()
            current_index = start_index

            while current_index < len(file_elements):
                element = file_elements[current_index]
                element_text = element_to_text(element)
                element_words = element_text.split()

                next_pages = set(current_pages)
                if element.page_id is not None:
                    next_pages.add(element.page_id)

                would_exceed_pages = len(next_pages) > max_pages_per_chunk
                would_exceed_words = (
                    current_elements
                    and current_word_count + len(element_words) > chunk_size_words
                )

                if current_elements and (would_exceed_pages or would_exceed_words):
                    break

                current_elements.append(element)
                current_word_count += len(element_words)
                current_pages = next_pages
                current_index += 1

            if not current_elements:
                break

            text = "\n".join(element_to_text(element) for element in current_elements)

            page_ids = sorted(
                {
                    element.page_id
                    for element in current_elements
                    if element.page_id is not None
                }
            )
            element_types = sorted({element.element_type for element in current_elements})

            start_element_id = current_elements[0].element_id
            end_element_id = current_elements[-1].element_id

            chunk_id = f"{file_name}::json_chunk_{chunk_index:04d}"

            all_chunks.append(
                JsonChunk(
                    chunk_id=chunk_id,
                    file_name=file_name,
                    year=year,
                    month=month,
                    chunk_index=chunk_index,
                    start_element_id=start_element_id,
                    end_element_id=end_element_id,
                    page_ids=", ".join(str(page_id) for page_id in page_ids),
                    element_types=", ".join(element_types),
                    text=text,
                )
            )

            chunk_index += 1

            if current_index >= len(file_elements):
                break

            start_index = max(current_index - overlap_elements, start_index + 1)

    return all_chunks


def json_chunks_to_dataframe(chunks: list[JsonChunk]) -> pd.DataFrame:
    """Convert JSON-aware chunks to a DataFrame for retrieval and evaluation."""
    return pd.DataFrame(
        [
            {
                "chunk_id": chunk.chunk_id,
                "file_name": chunk.file_name,
                "year": chunk.year,
                "month": chunk.month,
                "chunk_index": chunk.chunk_index,
                "start_element_id": chunk.start_element_id,
                "end_element_id": chunk.end_element_id,
                "page_ids": chunk.page_ids,
                "element_types": chunk.element_types,
                "text": chunk.text,
            }
            for chunk in chunks
        ]
    )

import re


YEAR_PATTERN = re.compile(r"(19\d{2}|20\d{2})")
YEAR_RANGE_PATTERN = re.compile(r"(19\d{2}|20\d{2})\s*(?:-|–|—|to|through)\s*(19\d{2}|20\d{2})", re.IGNORECASE)

MONTH_NAME_TO_NUMBER = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def infer_year_hints(
    question: str,
    start_year: int = 2010,
    end_year: int = 2025,
) -> set[int]:
    """
    Infer likely Treasury Bulletin source years from a question.

    This is intentionally soft metadata logic. We do not assume the answer key.
    We only use years mentioned in the question, plus the following year because
    Treasury Bulletins often report prior fiscal/calendar periods later.
    """
    text = str(question)
    years = {int(match) for match in YEAR_PATTERN.findall(text)}

    for start_text, end_text in YEAR_RANGE_PATTERN.findall(text):
        start = int(start_text)
        end = int(end_text)

        if start <= end and end - start <= 30:
            years.update(range(start, end + 1))

    expanded_years: set[int] = set()

    for year in years:
        for candidate in (year, year + 1):
            if start_year <= candidate <= end_year:
                expanded_years.add(candidate)

    return expanded_years


def next_reporting_months(month: int) -> set[int]:
    """
    Map a mentioned month to likely Treasury Bulletin reporting months.

    Treasury Bulletins are commonly quarterly. If a question mentions March 31,
    the relevant bulletin may be March or June; if it mentions June, the relevant
    bulletin may be June or September, etc.
    """
    if month <= 3:
        return {3, 6}
    if month <= 6:
        return {6, 9}
    if month <= 9:
        return {9, 12}
    return {12}


def infer_month_hints(question: str) -> set[int]:
    """Infer likely Treasury Bulletin source months from a question."""
    text = str(question).lower()
    months: set[int] = set()

    for name, month in MONTH_NAME_TO_NUMBER.items():
        if re.search(rf"\b{name}\b", text):
            months.update(next_reporting_months(month))

    if "calendar year" in text or re.search(r"\bcy\s*\d{4}", text):
        months.add(12)

    if "fiscal year" in text or re.search(r"\bfy\s*\d{4}", text):
        months.update({9, 12})

    if "quarter" in text or "qoq" in text:
        months.update({3, 6, 9, 12})

    return months

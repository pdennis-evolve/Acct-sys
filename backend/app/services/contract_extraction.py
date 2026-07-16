"""Real (not mocked) text extraction from uploaded PDF/docx contracts,
plus heuristic key-date detection. The heuristics are genuinely run
against the document's actual text -- they are not guaranteed correct
for every contract layout, which is exactly why every extracted date
is surfaced back to the user as an editable, reviewable suggestion
rather than applied silently.
"""
import re

from dateutil import parser as dateutil_parser


def extract_text(file_obj, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    file_obj.seek(0)
    if ext == "pdf":
        return _extract_pdf_text(file_obj)
    if ext == "docx":
        return _extract_docx_text(file_obj)
    try:
        return file_obj.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_pdf_text(file_obj) -> str:
    from pypdf import PdfReader

    reader = PdfReader(file_obj)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx_text(file_obj) -> str:
    import docx

    document = docx.Document(file_obj)
    return "\n".join(p.text for p in document.paragraphs)


_DATE_PATTERN = re.compile(
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b"
    r"|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)

# Search window in characters after a keyword hit -- most contracts state
# the date within a sentence or two of the label ("Effective Date: ...").
_WINDOW = 200

_KEYWORDS = {
    "start_date": ["effective date", "commencement date", "start date", "effective as of", "begins on"],
    "end_date": ["expiration date", "end date", "termination date", "expires on", "terminates on"],
    "renewal_date": ["renewal date", "renews on", "next renewal"],
}


def _parse_date(fragment: str):
    try:
        return dateutil_parser.parse(fragment, fuzzy=False).date()
    except (ValueError, OverflowError, TypeError):
        return None


def extract_key_dates(text: str) -> dict:
    """Returns {"start_date": "YYYY-MM-DD" | None, "end_date": ..., "renewal_date": ...}."""
    lowered = text.lower()
    results = {}
    for field, keywords in _KEYWORDS.items():
        found = None
        for kw in keywords:
            idx = lowered.find(kw)
            if idx == -1:
                continue
            window = text[idx: idx + _WINDOW]
            match = _DATE_PATTERN.search(window)
            if match:
                parsed = _parse_date(match.group(0))
                if parsed:
                    found = parsed
                    break
        results[field] = found.isoformat() if found else None
    return results

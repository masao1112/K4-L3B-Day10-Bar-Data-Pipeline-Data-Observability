from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path

import requests

from core.config import Settings


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(value: str | None) -> str:
    """Chuẩn hóa text từ Crossref."""

    if not value:
        return ""

    # Decode HTML entities
    value = unescape(value)

    # Loại bỏ HTML/XML tags, ví dụ <jats:p>...</jats:p>
    value = re.sub(r"<[^>]+>", " ", value)

    # Chuẩn hóa khoảng trắng
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def _extract_date(item: dict, date_field: str) -> str:
    """Lấy ngày từ Crossref date-parts."""

    date_info = item.get(date_field) or {}

    date_parts = date_info.get("date-parts", [])

    if not date_parts or not date_parts[0]:
        return ""

    parts = date_parts[0]

    if len(parts) >= 3:
        return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"

    if len(parts) == 2:
        return f"{parts[0]:04d}-{parts[1]:02d}"

    if len(parts) == 1:
        return str(parts[0])

    return ""


def _extract_authors(item: dict) -> list[str]:
    """Lấy danh sách tác giả từ Crossref."""

    authors = []

    for author in item.get("author", []):
        given = _clean_text(author.get("given"))
        family = _clean_text(author.get("family"))

        if given and family:
            name = f"{given} {family}"
        elif family:
            name = family
        elif given:
            name = given
        else:
            continue

        authors.append(name)

    return authors


def _extract_pdf_url(item: dict) -> str:
    """Tìm URL PDF trong trường link của Crossref."""

    for link in item.get("link", []):
        content_type = link.get("content-type", "")
        url = link.get("URL", "")

        if url and content_type == "application/pdf":
            return url

    # Một số record không khai báo content-type rõ ràng
    for link in item.get("link", []):
        url = link.get("URL", "")

        if url and ".pdf" in url.lower():
            return url

    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thành list PaperRecord."""

    records: list[PaperRecord] = []

    message = payload.get("message", {})

    if not isinstance(message, dict):
        return records

    items = message.get("items", [])

    if not isinstance(items, list):
        return records

    for item in items:
        if not isinstance(item, dict):
            continue

        # --------------------------------------------------
        # 1. DOI / paper_id
        # --------------------------------------------------
        paper_id = _clean_text(item.get("DOI"))

        if not paper_id:
            continue

        # --------------------------------------------------
        # 2. Title
        # --------------------------------------------------
        title_list = item.get("title", [])

        if isinstance(title_list, list):
            title = _clean_text(title_list[0]) if title_list else ""
        else:
            title = _clean_text(title_list)

        # Record không có title thì bỏ
        if not title:
            continue

        # --------------------------------------------------
        # 3. Abstract
        # --------------------------------------------------
        summary = _clean_text(item.get("abstract"))

        # --------------------------------------------------
        # 4. Authors
        # --------------------------------------------------
        authors = _extract_authors(item)

        # --------------------------------------------------
        # 5. Categories / subjects
        # --------------------------------------------------
        categories = []

        for subject in item.get("subject", []):
            subject = _clean_text(subject)

            if subject and subject not in categories:
                categories.append(subject)

        primary_category = categories[0] if categories else ""

        # --------------------------------------------------
        # 6. Published date
        # --------------------------------------------------
        published = (
            _extract_date(item, "published")
            or _extract_date(item, "published-online")
            or _extract_date(item, "published-print")
        )

        # --------------------------------------------------
        # 7. Updated date
        # --------------------------------------------------
        updated = _extract_date(item, "updated")

        # --------------------------------------------------
        # 8. Abstract URL
        # --------------------------------------------------
        abs_url = f"https://doi.org/{paper_id}"

        # --------------------------------------------------
        # 9. PDF URL
        # --------------------------------------------------
        pdf_url = _extract_pdf_url(item)

        # --------------------------------------------------
        # 10. Comment
        # --------------------------------------------------
        comment = _clean_text(item.get("comment"))

        record = PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment,
        )

        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Gọi Crossref API, lưu raw response và parse thành records."""

    # ------------------------------------------------------
    # 1. Tạo parameters
    # ------------------------------------------------------

    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    # Nếu filter rỗng thì bỏ khỏi params
    params = {
        key: value
        for key, value in params.items()
        if value not in (None, "")
    }

    url = "https://api.crossref.org/works"

    # ------------------------------------------------------
    # 2. Retry khi gặp 429 / 503
    # ------------------------------------------------------

    max_retries = 3

    response = None

    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=30,
                headers={
                    "User-Agent": "PaperIngestion/1.0"
                },
            )

            # Thành công
            if response.status_code == 200:
                break

            # Có thể retry
            if response.status_code in (429, 500, 502, 503, 504):
                if attempt < max_retries - 1:
                    wait_seconds = 2 ** attempt
                    time.sleep(wait_seconds)
                    continue

            # Status code khác
            response.raise_for_status()

        except requests.RequestException:
            if attempt >= max_retries - 1:
                raise

            wait_seconds = 2 ** attempt
            time.sleep(wait_seconds)

    if response is None:
        raise RuntimeError("Không nhận được response từ Crossref API.")

    # ------------------------------------------------------
    # 3. Parse JSON
    # ------------------------------------------------------

    payload = response.json()

    # ------------------------------------------------------
    # 4. Lưu raw API response
    # ------------------------------------------------------

    raw_api_path = Path(settings.paths.raw_api_response)

    raw_api_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_api_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ------------------------------------------------------
    # 5. Parse thành PaperRecord
    # ------------------------------------------------------

    records = parse_crossref_payload(payload)

    # ------------------------------------------------------
    # 6. Lưu records
    # ------------------------------------------------------

    raw_records_path = Path(settings.paths.raw_records_json)

    raw_records_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_records_path.write_text(
        json.dumps(
            [asdict(record) for record in records],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Đọc JSON snapshot và map thành PaperRecord."""

    if not path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy raw records file: {path}"
        )

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, list):
        raise ValueError(
            f"Expected JSON list, nhưng nhận được {type(data).__name__}"
        )

    records = []

    for item in data:
        if not isinstance(item, dict):
            continue

        record = PaperRecord(
            paper_id=item.get("paper_id", ""),
            title=item.get("title", ""),
            summary=item.get("summary", ""),
            authors=item.get("authors", []),
            categories=item.get("categories", []),
            primary_category=item.get("primary_category", ""),
            published=item.get("published", ""),
            updated=item.get("updated", ""),
            abs_url=item.get("abs_url", ""),
            pdf_url=item.get("pdf_url", ""),
            comment=item.get("comment", ""),
        )

        records.append(record)

    return records
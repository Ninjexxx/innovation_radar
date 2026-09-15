"""Import a human-reviewed XLSX workbook into the canonical Gold Set."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


ALLOWED_LABELS = ("interesting", "maybe", "irrelevant")
REQUIRED_COLUMNS = (
    "item_id",
    "source",
    "source_surface_or_feed",
    "title",
    "url",
    "published_at",
    "author",
    "short_description",
    "available_metrics",
    "human_label",
    "human_reason",
)
NON_EMPTY_COLUMNS = (
    "item_id",
    "source",
    "source_surface_or_feed",
    "title",
    "url",
)
DEFAULT_SHEET_NAME = "review_sample"
GITHUB_SHEET_NAME = "review_sample_github"
GITHUB_SOURCE = "github"
GITHUB_REVIEWED_COUNT = 43
GITHUB_INCLUDED_COUNT = 40
GITHUB_PREVIOUS_COUNT = 90
GITHUB_FINAL_COUNT = 130
GITHUB_EXPECTED_LABEL_COUNTS = {
    "interesting": 17,
    "maybe": 4,
    "irrelevant": 19,
}
MAIN_NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOCUMENT_REL_NAMESPACE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
PACKAGE_REL_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)


class ReviewValidationError(ValueError):
    """Raised when the workbook cannot be accepted as human source of truth."""


@dataclass(frozen=True, slots=True)
class GoldSetImportResult:
    output_path: Path
    item_count: int
    source_file: str
    source_sha256: str
    items: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class GoldSetMergeResult:
    """Result of one validated and deterministic Gold Set expansion."""

    output_path: Path
    item_count: int
    added_item_count: int
    github_item_count: int
    excluded_item_count: int
    source_file: str
    source_sha256: str
    items: tuple[dict[str, Any], ...]
    previous_items: tuple[dict[str, Any], ...]
    github_items: tuple[dict[str, Any], ...]


def import_review_workbook(
    workbook_path: str | Path,
    output_path: str | Path,
    expected_count: int | None = None,
) -> GoldSetImportResult:
    """Validate all rows before writing a deterministic Gold Set JSON file."""

    source_path = Path(workbook_path)
    rows = read_xlsx_rows(source_path)
    items = validate_review_rows(rows, expected_count=expected_count)
    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    document = {
        "schema_version": "0.1",
        "source_file": source_path.name,
        "source_sha256": source_sha256,
        "item_count": len(items),
        "allowed_labels": list(ALLOWED_LABELS),
        "items": list(items),
    }
    rendered = json.dumps(document, ensure_ascii=False, indent=2) + "\n"

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    return GoldSetImportResult(
        output_path=destination,
        item_count=len(items),
        source_file=source_path.name,
        source_sha256=source_sha256,
        items=items,
    )


def merge_github_review_workbook(
    workbook_path: str | Path,
    base_gold_set_path: str | Path,
    output_path: str | Path,
    *,
    expected_reviewed_count: int = GITHUB_REVIEWED_COUNT,
    expected_github_count: int = GITHUB_INCLUDED_COUNT,
    expected_previous_count: int = GITHUB_PREVIOUS_COUNT,
    expected_final_count: int = GITHUB_FINAL_COUNT,
    expected_label_counts: Mapping[str, int] = GITHUB_EXPECTED_LABEL_COUNTS,
    sheet_name: str = GITHUB_SHEET_NAME,
) -> GoldSetMergeResult:
    """Merge only reviewed GitHub rows while preserving every prior item."""

    source_path = Path(workbook_path)
    rows = read_xlsx_rows(source_path, sheet_name=sheet_name)
    reviewed_items = validate_review_rows(
        rows, expected_count=expected_reviewed_count
    )
    github_items = tuple(
        item for item in reviewed_items if item["source"] == GITHUB_SOURCE
    )
    excluded_items = tuple(
        item for item in reviewed_items if item["source"] != GITHUB_SOURCE
    )
    problems: list[str] = []
    if len(github_items) != expected_github_count:
        problems.append(
            f"expected {expected_github_count} GitHub items after source filtering, "
            f"found {len(github_items)}"
        )

    label_counts = Counter(str(item["human_label"]) for item in github_items)
    normalized_expected_counts = {
        label: int(expected_label_counts.get(label, 0)) for label in ALLOWED_LABELS
    }
    observed_counts = {label: label_counts[label] for label in ALLOWED_LABELS}
    if observed_counts != normalized_expected_counts:
        problems.append(
            "unexpected GitHub label distribution; expected "
            f"{normalized_expected_counts}, found {observed_counts}"
        )
    if problems:
        raise ReviewValidationError(_format_problems(problems))

    base_path = Path(base_gold_set_path)
    base_document = _read_gold_set_document(base_path)
    base_items = tuple(base_document["items"])
    previous_items = tuple(
        item for item in base_items if item.get("source") != GITHUB_SOURCE
    )
    if len(previous_items) != expected_previous_count:
        raise ReviewValidationError(
            "gold set merge failed:\n- expected "
            f"{expected_previous_count} previous non-GitHub items, "
            f"found {len(previous_items)}"
        )

    existing_by_id = {str(item["item_id"]): item for item in base_items}
    merged_items = list(base_items)
    added_item_count = 0
    for item in github_items:
        item_id = str(item["item_id"])
        existing = existing_by_id.get(item_id)
        if existing is None:
            merged_items.append(item)
            existing_by_id[item_id] = item
            added_item_count += 1
        elif existing != item:
            raise ReviewValidationError(
                "gold set merge failed:\n- duplicate item_id "
                f"{item_id!r} conflicts with the existing human judgment"
            )

    if len(merged_items) != expected_final_count:
        raise ReviewValidationError(
            "gold set merge failed:\n- expected "
            f"{expected_final_count} items after merge, found {len(merged_items)}"
        )

    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source_workbooks = _merged_source_workbooks(
        base_document,
        source_file=source_path.name,
        source_sha256=source_sha256,
        reviewed_count=len(reviewed_items),
        included_count=len(github_items),
        excluded_count=len(excluded_items),
    )
    document = _expanded_document(
        base_document,
        source_workbooks=source_workbooks,
        merged_items=tuple(merged_items),
    )
    rendered = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    return GoldSetMergeResult(
        output_path=destination,
        item_count=len(merged_items),
        added_item_count=added_item_count,
        github_item_count=len(github_items),
        excluded_item_count=len(excluded_items),
        source_file=source_path.name,
        source_sha256=source_sha256,
        items=tuple(merged_items),
        previous_items=previous_items,
        github_items=github_items,
    )


def read_xlsx_rows(
    workbook_path: str | Path,
    sheet_name: str = DEFAULT_SHEET_NAME,
) -> tuple[dict[str, str], ...]:
    """Read text cells from one XLSX worksheet using only the standard library."""

    path = Path(workbook_path)
    if not path.is_file():
        raise ReviewValidationError(f"review workbook does not exist: {path}")
    try:
        with ZipFile(path) as archive:
            worksheet_path = _worksheet_path(archive, sheet_name)
            shared_strings = _shared_strings(archive)
            worksheet = ElementTree.fromstring(archive.read(worksheet_path))
    except (BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise ReviewValidationError(
            f"review workbook is not a readable XLSX file: {path}: {error}"
        ) from error

    namespace = {"main": MAIN_NAMESPACE}
    matrix: list[dict[int, str]] = []
    for row in worksheet.findall(".//main:sheetData/main:row", namespace):
        values: dict[int, str] = {}
        for cell in row.findall("main:c", namespace):
            reference = cell.get("r", "")
            values[_column_index(reference)] = _cell_text(cell, shared_strings)
        matrix.append(values)

    if not matrix:
        raise ReviewValidationError("review worksheet is empty")
    header_width = max(matrix[0], default=-1) + 1
    headers = tuple(matrix[0].get(index, "") for index in range(header_width))
    if not headers or any(not header for header in headers):
        raise ReviewValidationError("review worksheet has an empty column header")
    if len(headers) != len(set(headers)):
        raise ReviewValidationError("review worksheet has duplicate column headers")

    rows: list[dict[str, str]] = []
    for values in matrix[1:]:
        row = {header: values.get(index, "") for index, header in enumerate(headers)}
        if any(value for value in row.values()):
            rows.append(row)
    return tuple(rows)


def validate_review_rows(
    rows: tuple[dict[str, str], ...],
    expected_count: int | None = None,
) -> tuple[dict[str, Any], ...]:
    """Validate human fields without correcting or inferring their values."""

    problems: list[str] = []
    if expected_count is not None and expected_count < 1:
        raise ValueError("expected_count must be positive when provided")
    if expected_count is not None and len(rows) != expected_count:
        problems.append(
            f"expected {expected_count} reviewed items, found {len(rows)}"
        )

    available_columns = set(rows[0]) if rows else set()
    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in available_columns
    ]
    if missing_columns:
        problems.append(f"missing required columns: {', '.join(missing_columns)}")
    if not rows:
        problems.append("review contains no items")
    if problems and (missing_columns or not rows):
        raise ReviewValidationError(_format_problems(problems))

    seen_ids: dict[str, int] = {}
    validated: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        item_id = row["item_id"]
        for column in NON_EMPTY_COLUMNS:
            if not row[column].strip():
                problems.append(f"row {index}: {column} is empty")

        label = row["human_label"]
        if not label.strip():
            problems.append(f"row {index}: human_label is empty")
        elif label not in ALLOWED_LABELS:
            allowed = ", ".join(ALLOWED_LABELS)
            problems.append(
                f"row {index}: invalid human_label {label!r}; allowed: {allowed}"
            )

        if not row["human_reason"].strip():
            problems.append(f"row {index}: human_reason is empty")

        if item_id in seen_ids:
            problems.append(
                f"row {index}: duplicate item_id {item_id!r}; "
                f"first seen at row {seen_ids[item_id]}"
            )
        elif item_id:
            seen_ids[item_id] = index

        metrics: Any = None
        try:
            metrics = json.loads(row["available_metrics"])
        except json.JSONDecodeError as error:
            problems.append(
                f"row {index}: available_metrics is not valid JSON: {error.msg}"
            )
        if metrics is not None and not isinstance(metrics, dict):
            problems.append(f"row {index}: available_metrics must be a JSON object")

        validated.append(
            {
                "item_id": row["item_id"],
                "source": row["source"],
                "source_surface_or_feed": row["source_surface_or_feed"],
                "title": row["title"],
                "url": row["url"],
                "published_at": row["published_at"],
                "author": row["author"],
                "short_description": row["short_description"],
                "available_metrics": metrics,
                "human_label": row["human_label"],
                "human_reason": row["human_reason"],
            }
        )

    if problems:
        raise ReviewValidationError(_format_problems(problems))
    return tuple(validated)


def _worksheet_path(archive: ZipFile, sheet_name: str) -> str:
    namespace = {"main": MAIN_NAMESPACE, "rel": DOCUMENT_REL_NAMESPACE}
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    sheet = workbook.find(f".//main:sheet[@name='{sheet_name}']", namespace)
    if sheet is None:
        available = ", ".join(
            element.get("name", "")
            for element in workbook.findall(".//main:sheet", namespace)
        )
        raise ReviewValidationError(
            f"worksheet {sheet_name!r} not found; available: {available or 'none'}"
        )

    relationship_id = sheet.get(f"{{{DOCUMENT_REL_NAMESPACE}}}id")
    relationships = ElementTree.fromstring(
        archive.read("xl/_rels/workbook.xml.rels")
    )
    for relationship in relationships.findall(
        f"{{{PACKAGE_REL_NAMESPACE}}}Relationship"
    ):
        if relationship.get("Id") == relationship_id:
            target = relationship.get("Target", "")
            if target.startswith("/"):
                return target.lstrip("/")
            return posixpath.normpath(posixpath.join("xl", target))
    raise ReviewValidationError(
        f"worksheet relationship is missing for {sheet_name!r}"
    )


def _shared_strings(archive: ZipFile) -> tuple[str, ...]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return ()
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return tuple(
        "".join(element.itertext())
        for element in root.findall(f"{{{MAIN_NAMESPACE}}}si")
    )


def _column_index(reference: str) -> int:
    match = re.match(r"([A-Za-z]+)", reference)
    if match is None:
        raise ReviewValidationError(f"invalid XLSX cell reference: {reference!r}")
    result = 0
    for character in match.group(1).upper():
        result = result * 26 + ord(character) - ord("A") + 1
    return result - 1


def _cell_text(cell: ElementTree.Element, shared_strings: tuple[str, ...]) -> str:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        return "".join(
            element.text or ""
            for element in cell.iter(f"{{{MAIN_NAMESPACE}}}t")
        )
    value = cell.find(f"{{{MAIN_NAMESPACE}}}v")
    if value is None or value.text is None:
        return ""
    if cell_type == "s":
        try:
            return shared_strings[int(value.text)]
        except (IndexError, ValueError) as error:
            raise ReviewValidationError("invalid shared string reference") from error
    return value.text


def _format_problems(problems: list[str]) -> str:
    return "review validation failed:\n- " + "\n- ".join(problems)


def _read_gold_set_document(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ReviewValidationError(f"base Gold Set does not exist: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReviewValidationError(f"base Gold Set is not readable: {path}: {error}") from error
    if not isinstance(document, dict) or not isinstance(document.get("items"), list):
        raise ReviewValidationError("base Gold Set must contain an items array")
    items = document["items"]
    if document.get("item_count") != len(items):
        raise ReviewValidationError(
            "base Gold Set item_count does not match the number of items"
        )
    item_ids = [
        str(item.get("item_id"))
        for item in items
        if isinstance(item, dict) and item.get("item_id") is not None
    ]
    if len(item_ids) != len(items):
        raise ReviewValidationError("base Gold Set contains an item without item_id")
    if len(item_ids) != len(set(item_ids)):
        raise ReviewValidationError("base Gold Set contains duplicate item_id values")
    return document


def _merged_source_workbooks(
    base_document: Mapping[str, Any],
    *,
    source_file: str,
    source_sha256: str,
    reviewed_count: int,
    included_count: int,
    excluded_count: int,
) -> list[dict[str, Any]]:
    raw_sources = base_document.get("source_workbooks")
    if raw_sources is None:
        sources = [
            {
                "source_file": base_document.get("source_file"),
                "source_sha256": base_document.get("source_sha256"),
                "reviewed_item_count": base_document.get("item_count"),
                "included_item_count": base_document.get("item_count"),
                "excluded_item_count": 0,
                "source_filter": None,
            }
        ]
    elif isinstance(raw_sources, list) and all(
        isinstance(entry, dict) for entry in raw_sources
    ):
        sources = [dict(entry) for entry in raw_sources]
    else:
        raise ReviewValidationError("base Gold Set source_workbooks must be an array")

    github_source = {
        "source_file": source_file,
        "source_sha256": source_sha256,
        "reviewed_item_count": reviewed_count,
        "included_item_count": included_count,
        "excluded_item_count": excluded_count,
        "source_filter": GITHUB_SOURCE,
    }
    matching = [
        source
        for source in sources
        if source.get("source_file") == source_file
        and source.get("source_filter") == GITHUB_SOURCE
    ]
    if matching:
        if matching != [github_source]:
            raise ReviewValidationError(
                "base Gold Set has conflicting provenance for the GitHub workbook"
            )
        return sources
    sources.append(github_source)
    return sources


def _expanded_document(
    base_document: Mapping[str, Any],
    *,
    source_workbooks: list[dict[str, Any]],
    merged_items: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in base_document.items():
        if key == "schema_version":
            document[key] = "0.2"
        elif key == "item_count":
            document["source_workbooks"] = source_workbooks
            document[key] = len(merged_items)
        elif key == "items":
            document[key] = list(merged_items)
        elif key != "source_workbooks":
            document[key] = value
    if "schema_version" not in document:
        document["schema_version"] = "0.2"
    if "source_workbooks" not in document:
        document["source_workbooks"] = source_workbooks
    return document

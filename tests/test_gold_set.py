import hashlib
import json
import os
import subprocess
import sys
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from innovation_radar.reports.human_judgment import (
    calculate_overall_statistics,
    calculate_source_statistics,
    write_human_judgment_report,
)
from innovation_radar.reports.github_discovery import (
    calculate_lens_statistics,
    identify_noise_patterns,
    render_github_discovery_report,
)
from innovation_radar.reviews.gold_set import (
    ReviewValidationError,
    import_review_workbook,
    merge_github_review_workbook,
)


HEADERS = (
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


def _row(
    item_id: str,
    label: str = "interesting",
    reason: str = "Possible to test.",
    surface: str = "newstories",
    source: str = "hacker_news",
    author: str = "human fixture",
    metrics: str = '{"score":1}',
) -> dict[str, str]:
    return {
        "item_id": item_id,
        "source": source,
        "source_surface_or_feed": surface,
        "title": f"Reviewed {item_id}",
        "url": f"https://example.com/{item_id}",
        "published_at": "2026-08-27T12:00:00Z",
        "author": author,
        "short_description": "Controlled review item.",
        "available_metrics": metrics,
        "human_label": label,
        "human_reason": reason,
    }


def _write_xlsx(
    path: Path,
    rows: list[dict[str, str]],
    sheet_name: str = "review_sample",
) -> None:
    values = [list(HEADERS)] + [[row.get(header, "") for header in HEADERS] for row in rows]
    shared: list[str] = []
    indexes: dict[str, int] = {}
    sheet_rows: list[str] = []
    for row_number, row in enumerate(values, start=1):
        cells: list[str] = []
        for column_number, value in enumerate(row, start=1):
            if value == "":
                continue
            if value not in indexes:
                indexes[value] = len(shared)
                shared.append(value)
            reference = f"{_column_name(column_number)}{row_number}"
            cells.append(
                f'<c r="{reference}" t="s"><v>{indexes[value]}</v></c>'
            )
        sheet_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')

    shared_xml = "".join(f"<si><t>{escape(value)}</t></si>" for value in shared)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        archive.writestr(
            "xl/sharedStrings.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"{shared_xml}</sst>",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>',
        )


def _column_name(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def _write_base_gold_set(path: Path, items: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "source_file": "review_sample.xlsx",
                "source_sha256": "base-hash",
                "item_count": len(items),
                "allowed_labels": ["interesting", "maybe", "irrelevant"],
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _validated_item(row: dict[str, str]) -> dict:
    item = dict(row)
    item["available_metrics"] = json.loads(item["available_metrics"])
    return item


def test_imports_human_review_without_changing_judgment(tmp_path: Path) -> None:
    workbook = tmp_path / "review.xlsx"
    output = tmp_path / "gold.json"
    rows = [
        _row("item-1", "interesting", "Human reason one."),
        _row("item-2", "maybe", "Human reason two.", "showstories"),
    ]
    _write_xlsx(workbook, rows)

    result = import_review_workbook(workbook, output, expected_count=2)
    document = json.loads(output.read_text(encoding="utf-8"))

    assert result.item_count == 2
    assert document["schema_version"] == "0.1"
    assert document["item_count"] == 2
    assert document["items"][0]["human_label"] == "interesting"
    assert document["items"][0]["human_reason"] == "Human reason one."
    assert document["items"][0]["available_metrics"] == {"score": 1}


def test_rejects_invalid_label(tmp_path: Path) -> None:
    workbook = tmp_path / "review.xlsx"
    _write_xlsx(workbook, [_row("item-1", "important")])

    with pytest.raises(ReviewValidationError, match="invalid human_label"):
        import_review_workbook(workbook, tmp_path / "gold.json", expected_count=1)


def test_rejects_missing_label(tmp_path: Path) -> None:
    workbook = tmp_path / "review.xlsx"
    _write_xlsx(workbook, [_row("item-1", "")])

    with pytest.raises(ReviewValidationError, match="human_label is empty"):
        import_review_workbook(workbook, tmp_path / "gold.json", expected_count=1)


def test_rejects_missing_reason(tmp_path: Path) -> None:
    workbook = tmp_path / "review.xlsx"
    _write_xlsx(workbook, [_row("item-1", reason="   ")])

    with pytest.raises(ReviewValidationError, match="human_reason is empty"):
        import_review_workbook(workbook, tmp_path / "gold.json", expected_count=1)


def test_rejects_duplicate_item_id(tmp_path: Path) -> None:
    workbook = tmp_path / "review.xlsx"
    _write_xlsx(workbook, [_row("item-1"), _row("item-1", "maybe")])

    with pytest.raises(ReviewValidationError, match="duplicate item_id"):
        import_review_workbook(workbook, tmp_path / "gold.json", expected_count=2)


def test_rejects_unexpected_item_count(tmp_path: Path) -> None:
    workbook = tmp_path / "review.xlsx"
    _write_xlsx(workbook, [_row("item-1")])

    with pytest.raises(ReviewValidationError, match="expected 2 reviewed items"):
        import_review_workbook(workbook, tmp_path / "gold.json", expected_count=2)


def test_gold_set_creation_is_deterministic(tmp_path: Path) -> None:
    workbook = tmp_path / "review.xlsx"
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    _write_xlsx(workbook, [_row("item-1"), _row("item-2", "irrelevant")])

    import_review_workbook(workbook, first, expected_count=2)
    import_review_workbook(workbook, second, expected_count=2)

    assert first.read_bytes() == second.read_bytes()


def test_merges_only_github_rows_deterministically_and_preserves_base(
    tmp_path: Path,
) -> None:
    previous_rows = [
        _row("old-1", "interesting", "Old reason one."),
        _row("old-2", "irrelevant", "Old reason two.", surface="rss-feed", source="rss"),
    ]
    previous_items = [_validated_item(row) for row in previous_rows]
    base = tmp_path / "base.json"
    workbook = tmp_path / "review_sample_github.xlsx"
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    _write_base_gold_set(base, previous_items)
    reviewed_rows = [
        _row(
            "github:1",
            "interesting",
            "Testable capability.",
            surface="health_wellness",
            source="github",
        ),
        _row(
            "hn-excluded",
            "irrelevant",
            "Not part of GitHub.",
            source="hacker_news",
        ),
        _row(
            "github:2",
            "maybe",
            "Needs investigation.",
            surface="local_new_interfaces",
            source="github",
        ),
        _row(
            "github:3",
            "irrelevant",
            "No implementation.",
            surface="personal_data_experiments",
            source="github",
        ),
    ]
    _write_xlsx(workbook, reviewed_rows, sheet_name="review_sample_github")
    arguments = {
        "expected_reviewed_count": 4,
        "expected_github_count": 3,
        "expected_previous_count": 2,
        "expected_final_count": 5,
        "expected_label_counts": {
            "interesting": 1,
            "maybe": 1,
            "irrelevant": 1,
        },
    }

    result = merge_github_review_workbook(workbook, base, first, **arguments)
    merge_github_review_workbook(workbook, base, second, **arguments)
    document = json.loads(first.read_text(encoding="utf-8"))

    assert first.read_bytes() == second.read_bytes()
    assert result.item_count == 5
    assert result.added_item_count == 3
    assert result.excluded_item_count == 1
    assert document["schema_version"] == "0.2"
    assert document["items"][:2] == previous_items
    assert [item["item_id"] for item in document["items"][2:]] == [
        "github:1",
        "github:2",
        "github:3",
    ]
    assert "hn-excluded" not in {item["item_id"] for item in document["items"]}
    assert document["source_workbooks"][1]["source_filter"] == "github"

    first_render = first.read_bytes()
    repeated = merge_github_review_workbook(workbook, first, first, **arguments)
    assert repeated.added_item_count == 0
    assert first.read_bytes() == first_render


def test_merge_rejects_unexpected_github_label_distribution(tmp_path: Path) -> None:
    base = tmp_path / "base.json"
    workbook = tmp_path / "review_sample_github.xlsx"
    _write_base_gold_set(base, [_validated_item(_row("old-1"))])
    _write_xlsx(
        workbook,
        [
            _row(
                "github:1",
                "interesting",
                "Human judgment must not be changed.",
                source="github",
                surface="health_wellness",
            )
        ],
        sheet_name="review_sample_github",
    )

    with pytest.raises(ReviewValidationError, match="unexpected GitHub label distribution"):
        merge_github_review_workbook(
            workbook,
            base,
            tmp_path / "output.json",
            expected_reviewed_count=1,
            expected_github_count=1,
            expected_previous_count=1,
            expected_final_count=2,
            expected_label_counts={
                "interesting": 0,
                "maybe": 1,
                "irrelevant": 0,
            },
        )


def test_merge_rejects_conflicting_duplicate_item_id(tmp_path: Path) -> None:
    existing = _validated_item(
        _row(
            "github:1",
            "interesting",
            "Original human judgment.",
            surface="health_wellness",
            source="github",
        )
    )
    base = tmp_path / "base.json"
    workbook = tmp_path / "review_sample_github.xlsx"
    _write_base_gold_set(
        base,
        [_validated_item(_row("old-1")), existing],
    )
    _write_xlsx(
        workbook,
        [
            _row(
                "github:1",
                "irrelevant",
                "Different human judgment.",
                surface="health_wellness",
                source="github",
            )
        ],
        sheet_name="review_sample_github",
    )

    with pytest.raises(ReviewValidationError, match="conflicts with the existing"):
        merge_github_review_workbook(
            workbook,
            base,
            tmp_path / "output.json",
            expected_reviewed_count=1,
            expected_github_count=1,
            expected_previous_count=1,
            expected_final_count=2,
            expected_label_counts={
                "interesting": 0,
                "maybe": 0,
                "irrelevant": 1,
            },
        )


def test_calculates_discovery_lens_statistics_and_noise_patterns() -> None:
    rows = [
        _row("1", "interesting", surface="health_wellness", source="github"),
        _row("2", "maybe", surface="health_wellness", source="github"),
        _row(
            "3",
            "irrelevant",
            "É apenas um perfil/stub sem software.",
            surface="wearables_sensors",
            source="github",
            author="api-evangelist",
        ),
        _row(
            "4",
            "irrelevant",
            "Runtime/framework para desenvolvedores.",
            surface="voice_vision_multimodal",
            source="github",
        ),
        _row(
            "5",
            "irrelevant",
            "Exercício básico sem valor.",
            surface="local_new_interfaces | personal_data_experiments",
            source="github",
        ),
    ]
    items = tuple(_validated_item(row) for row in rows)

    lens = calculate_lens_statistics(items)
    patterns = identify_noise_patterns(items)

    assert lens["health_wellness"].total == 2
    assert lens["health_wellness"].useful_percentage == 100.0
    assert lens["local_new_interfaces"].irrelevant == 1
    assert lens["personal_data_experiments"].irrelevant == 1
    assert [pattern.count for pattern in patterns] == [1, 1, 1]


def test_renders_github_analysis_without_scores_or_automatic_changes() -> None:
    github_items = tuple(
        _validated_item(
            _row(
                str(index),
                "interesting" if index % 2 else "irrelevant",
                "Human reason.",
                surface=lens,
                source="github",
            )
        )
        for index, lens in enumerate(
            (
                "health_wellness",
                "wearables_sensors",
                "voice_vision_multimodal",
                "local_new_interfaces",
                "personal_data_experiments",
            ),
            start=1,
        )
    )
    previous_items = (_validated_item(_row("old", "maybe")),)

    report = render_github_discovery_report(
        github_items,
        previous_items,
        excluded_non_github_count=3,
    )

    assert "Qualidade por discovery lens" in report
    assert "Possible Discovery Calibration Points" in report
    assert "GitHub versus HN/RSS" in report
    assert "Não contém classificação automática, Opportunity Score" in report
    assert "Nenhuma lens, query, classificação humana" in report


def test_canonical_gold_set_v02_preserves_v01_and_contains_40_github_items() -> None:
    gold_set_path = Path(__file__).parent / "fixtures" / "signal_gold_set.json"
    document = json.loads(gold_set_path.read_text(encoding="utf-8"))
    items = document["items"]
    previous_items = [item for item in items if item["source"] != "github"]
    github_items = [item for item in items if item["source"] == "github"]
    previous_digest = hashlib.sha256(
        json.dumps(
            previous_items,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    assert document["schema_version"] == "0.2"
    assert document["item_count"] == 130
    assert len(items) == len({item["item_id"] for item in items}) == 130
    assert len(previous_items) == 90
    assert previous_digest == (
        "5b8e8929e67d54433aaea6ab441072f107c89c5f556fbdf6cacf1980b82492fe"
    )
    assert len(github_items) == 40
    assert {
        label: sum(item["human_label"] == label for item in github_items)
        for label in ("interesting", "maybe", "irrelevant")
    } == {"interesting": 17, "maybe": 4, "irrelevant": 19}


def test_calculates_general_and_source_statistics() -> None:
    items = (
        _row("1", "interesting", surface="newstories"),
        _row("2", "maybe", surface="newstories"),
        _row("3", "irrelevant", surface="showstories"),
        _row("4", "interesting", surface="showstories"),
    )

    overall = calculate_overall_statistics(items)
    by_source = calculate_source_statistics(items)

    assert overall.total == 4
    assert (overall.interesting, overall.maybe, overall.irrelevant) == (2, 1, 1)
    assert overall.interesting_percentage == 50.0
    assert by_source["newstories"].total == 2
    assert by_source["newstories"].useful_percentage == 100.0
    assert by_source["showstories"].irrelevant == 1


def test_writes_human_judgment_report_without_automatic_decision(
    tmp_path: Path,
) -> None:
    items = (
        _row("1", "interesting", "Possible to test this SDK."),
        _row("2", "irrelevant", "Sem valor algum."),
    )

    path = write_human_judgment_report(items, tmp_path / "analysis.md")
    report = path.read_text(encoding="utf-8")

    assert "Possible Policy Calibration Points" in report
    assert "Developer tooling marcado como interesting" in report
    assert "nenhuma categoria altera o label humano" in report
    assert "Opportunity Score" in report


def test_import_gold_set_cli(tmp_path: Path) -> None:
    workbook = tmp_path / "review.xlsx"
    gold_set = tmp_path / "gold.json"
    report = tmp_path / "analysis.md"
    _write_xlsx(workbook, [_row("item-1"), _row("item-2", "maybe")])
    project_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(project_root / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "innovation_radar",
            "import-gold-set",
            str(workbook),
            "--expected-count",
            "2",
            "--gold-set-path",
            str(gold_set),
            "--analysis-report-path",
            str(report),
        ],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert gold_set.is_file()
    assert report.is_file()
    assert "Gold Set imported with 2 human-reviewed items" in result.stderr

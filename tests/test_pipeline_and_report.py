from datetime import datetime, timezone
from pathlib import Path

from innovation_radar.collectors.base import CollectionBatch
from innovation_radar.models import RawItem
from innovation_radar.pipeline import run_discovery
from innovation_radar.reports.markdown import write_raw_report
from innovation_radar.storage.sqlite import SQLiteStorage


class SequenceClock:
    def __init__(self, *values: datetime) -> None:
        self._values = iter(values)

    def __call__(self) -> datetime:
        return next(self._values)


class StaticCollector:
    name = "hacker_news"

    def __init__(
        self, score: int = 1, description: str = "Original controlled description."
    ) -> None:
        self.score = score
        self.description = description

    def collect(self, collected_at: datetime) -> CollectionBatch:
        return CollectionBatch(
            items=(
                RawItem(
                    id="hacker_news:123",
                    source="hacker_news",
                    source_item_id="123",
                    title="Controlled discovery item",
                    description=self.description,
                    url="https://example.com/item",
                    author="tester",
                    published_at=collected_at,
                    first_seen_at=collected_at,
                    collected_at=collected_at,
                    raw_metrics={"score": self.score},
                    raw_payload={"score": self.score},
                ),
            )
        )


class FailingCollector:
    name = "rss"

    def collect(self, collected_at: datetime) -> CollectionBatch:
        raise OSError("controlled source failure")


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 27, hour, minute, tzinfo=timezone.utc)


def test_second_run_marks_known_item_and_preserves_first_seen(tmp_path: Path) -> None:
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")
    first = run_discovery(
        storage,
        (StaticCollector(score=1),),
        clock=SequenceClock(_utc(10), _utc(10, 1), _utc(10, 2)),
        run_id="run-first",
    )
    second = run_discovery(
        storage,
        (StaticCollector(score=7),),
        clock=SequenceClock(_utc(11), _utc(11, 1), _utc(11, 2)),
        run_id="run-second",
    )

    assert first.new_count == 1
    assert first.updated_count == 0
    assert second.new_count == 0
    assert second.updated_count == 1

    stored = storage.get_raw_item_by_source("hacker_news", "123")
    assert stored is not None
    assert stored.first_seen_at == _utc(10, 1)
    assert stored.collected_at == _utc(11, 1)
    assert stored.raw_metrics == {"score": 7}


def test_source_failure_is_recorded_and_report_remains_available(
    tmp_path: Path,
) -> None:
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")
    long_description = "Original controlled description. " + ("detail " * 200)
    result = run_discovery(
        storage,
        (StaticCollector(description=long_description), FailingCollector()),
        clock=SequenceClock(_utc(12), _utc(12, 1), _utc(12, 2), _utc(12, 3)),
        run_id="run-partial",
    )

    stored_run = storage.get_run_record("run-partial")
    assert stored_run is not None
    assert stored_run.status == "partial"
    assert stored_run.finished_at == _utc(12, 3)
    assert "controlled source failure" in (stored_run.error_message or "")
    assert storage.count_raw_items() == 1

    report_path = write_raw_report(result, tmp_path / "reports")
    report = report_path.read_text(encoding="utf-8")

    assert "Total coletado: **1**" in report
    assert "Novos itens: **1**" in report
    assert "Itens conhecidos/atualizados: **0**" in report
    assert "controlled source failure" in report
    assert "Controlled discovery item" in report
    assert "Original controlled description." in report
    assert long_description not in report
    assert "payload completo permanece no SQLite" in report
    assert "Não contém ranking ou análise de oportunidade" in report
    assert "Filtros determinísticos — shadow mode" in report
    assert "Nenhum item foi removido ou alterado" in report
    assert "Resultado do filtro shadow: `keep`" in report

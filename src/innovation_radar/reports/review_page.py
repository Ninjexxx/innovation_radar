"""Static HTML review page generated from the neutral review CSV.

This is a read-and-mark interface for human curation. It is a single, static HTML
file: no server, no framework, no runtime dependency, no network. Open it in a
browser, read the compact list, mark each item as interesting/maybe/irrelevant,
optionally write a short reason, then download a CSV with your labels filled in —
in the same schema the ``import-gold-set`` command expects.

The page never judges content and never ranks items; it only presents the same
provenance-diverse sample the CSV already contains.

Security note: every value that comes from the CSV (titles, descriptions, URLs,
authors) is untrusted external data. It is passed to the browser as JSON data and
rendered via ``textContent``/attribute assignment in the embedded script, never
via ``innerHTML``, so page content cannot inject markup or scripts.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from string import Template


# Columns copied verbatim from the review CSV into the page dataset.
_DISPLAY_FIELDS = (
    "item_id",
    "source",
    "source_surface_or_feed",
    "title",
    "url",
    "published_at",
    "author",
    "short_description",
    "available_metrics",
)
_EXPORT_FIELDS = (
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


@dataclass(frozen=True, slots=True)
class ReviewPageExport:
    html_path: Path
    item_count: int


def write_review_page(csv_path: str | Path, html_path: str | Path) -> ReviewPageExport:
    """Read the review CSV and write a self-contained HTML review page."""

    source_path = Path(csv_path)
    rows = _read_rows(source_path)
    if not rows:
        raise ValueError(f"no review rows found in {source_path}")

    output_path = Path(html_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_review_page(rows), encoding="utf-8")
    return ReviewPageExport(html_path=output_path, item_count=len(rows))


def _read_rows(csv_path: Path) -> list[dict[str, str]]:
    try:
        # utf-8-sig matches the BOM the exporter writes.
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return [
                {field: (row.get(field) or "") for field in _DISPLAY_FIELDS}
                for row in reader
            ]
    except OSError as error:
        raise ValueError(f"review CSV is not readable: {csv_path}: {error}") from error


def render_review_page(rows: list[dict[str, str]]) -> str:
    """Render the full HTML document for the given review rows."""

    # The dataset is embedded as JSON and consumed by the script via textContent.
    # </script> is escaped so the payload cannot close the surrounding tag.
    dataset = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    export_fields = json.dumps(list(_EXPORT_FIELDS))
    return _TEMPLATE.substitute(
        dataset=dataset,
        export_fields=export_fields,
        item_count=str(len(rows)),
    )


_TEMPLATE = Template(
    """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revisão de descoberta — Innovation Radar</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    margin: 0; line-height: 1.45; color: #1a1a1a; background: #f5f5f5;
  }
  header {
    position: sticky; top: 0; z-index: 10; background: #ffffff;
    border-bottom: 1px solid #ddd; padding: 12px 20px;
    display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
  }
  header h1 { font-size: 1.1rem; margin: 0 12px 0 0; }
  .counts { font-size: 0.85rem; color: #555; }
  .counts b { color: #1a1a1a; }
  .controls { margin-left: auto; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  select, button {
    font: inherit; padding: 6px 10px; border: 1px solid #bbb;
    border-radius: 6px; background: #fff; cursor: pointer;
  }
  button.primary { background: #1a6; border-color: #1a6; color: #fff; }
  main { padding: 16px 20px 60px; max-width: 980px; margin: 0 auto; }
  .card {
    background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
    padding: 14px 16px; margin-bottom: 12px;
  }
  .card.interesting { border-left: 5px solid #1a6; }
  .card.maybe { border-left: 5px solid #d90; }
  .card.irrelevant { border-left: 5px solid #999; opacity: 0.72; }
  .meta { font-size: 0.78rem; color: #666; margin-bottom: 4px; }
  .meta .src { display: inline-block; padding: 1px 6px; border-radius: 4px;
    background: #eef; color: #225; margin-right: 6px; font-weight: 600; }
  .title { font-size: 1rem; font-weight: 600; margin: 2px 0 6px; }
  .title a { color: #14c; text-decoration: none; }
  .title a:hover { text-decoration: underline; }
  .desc { font-size: 0.88rem; color: #333; margin-bottom: 8px; white-space: pre-wrap; }
  .labels { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .labels button { padding: 4px 10px; font-size: 0.82rem; }
  .labels button.active[data-label="interesting"] { background: #1a6; border-color: #1a6; color: #fff; }
  .labels button.active[data-label="maybe"] { background: #d90; border-color: #d90; color: #fff; }
  .labels button.active[data-label="irrelevant"] { background: #777; border-color: #777; color: #fff; }
  .reason { width: 100%; margin-top: 8px; padding: 6px 8px; font: inherit;
    border: 1px solid #ccc; border-radius: 6px; resize: vertical; min-height: 34px; }
  .hidden { display: none; }
  footer { text-align: center; font-size: 0.78rem; color: #888; padding: 20px; }
</style>
</head>
<body>
<header>
  <h1>Revisão de descoberta</h1>
  <div class="counts">
    <span>Total: <b id="c-total">0</b></span> ·
    <span>Interesting: <b id="c-interesting">0</b></span> ·
    <span>Maybe: <b id="c-maybe">0</b></span> ·
    <span>Irrelevant: <b id="c-irrelevant">0</b></span> ·
    <span>Sem rótulo: <b id="c-none">0</b></span>
  </div>
  <div class="controls">
    <label>Fonte
      <select id="filter-source"><option value="">todas</option></select>
    </label>
    <label>Rótulo
      <select id="filter-label">
        <option value="">todos</option>
        <option value="interesting">interesting</option>
        <option value="maybe">maybe</option>
        <option value="irrelevant">irrelevant</option>
        <option value="none">sem rótulo</option>
      </select>
    </label>
    <button class="primary" id="download">Baixar CSV rotulado</button>
  </div>
</header>
<main id="list"></main>
<footer>
  Página estática de revisão humana. Nenhum ranking ou julgamento automático.
  A decisão final é sua. Baixe o CSV ao terminar para preservar seus rótulos.
</footer>

<script type="application/json" id="dataset">$dataset</script>
<script>
(function () {
  "use strict";
  var EXPORT_FIELDS = $export_fields;
  var data = JSON.parse(document.getElementById("dataset").textContent);
  var state = data.map(function (row) {
    return { row: row, label: "", reason: "" };
  });

  var list = document.getElementById("list");
  var sourceFilter = document.getElementById("filter-source");
  var labelFilter = document.getElementById("filter-label");

  var sources = {};
  state.forEach(function (entry) {
    var src = entry.row.source || "?";
    sources[src] = true;
  });
  Object.keys(sources).sort().forEach(function (src) {
    var opt = document.createElement("option");
    opt.value = src;
    opt.textContent = src;
    sourceFilter.appendChild(opt);
  });

  function setText(el, value) { el.textContent = value == null ? "" : String(value); }

  function makeCard(entry, index) {
    var row = entry.row;
    var card = document.createElement("section");
    card.className = "card";
    card.dataset.index = String(index);

    var meta = document.createElement("div");
    meta.className = "meta";
    var src = document.createElement("span");
    src.className = "src";
    setText(src, row.source || "?");
    meta.appendChild(src);
    var prov = document.createElement("span");
    var bits = [];
    if (row.source_surface_or_feed) bits.push(row.source_surface_or_feed);
    if (row.published_at) bits.push(row.published_at);
    if (row.author) bits.push("por " + row.author);
    setText(prov, bits.join(" · "));
    meta.appendChild(prov);
    card.appendChild(meta);

    var title = document.createElement("div");
    title.className = "title";
    if (row.url) {
      var link = document.createElement("a");
      link.href = row.url;              // assigned as attribute, not parsed as HTML
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      setText(link, row.title || row.item_id || "(sem título)");
      title.appendChild(link);
    } else {
      setText(title, row.title || row.item_id || "(sem título)");
    }
    card.appendChild(title);

    if (row.short_description) {
      var desc = document.createElement("div");
      desc.className = "desc";
      setText(desc, row.short_description);
      card.appendChild(desc);
    }

    var labels = document.createElement("div");
    labels.className = "labels";
    ["interesting", "maybe", "irrelevant"].forEach(function (label) {
      var btn = document.createElement("button");
      btn.dataset.label = label;
      setText(btn, label);
      btn.addEventListener("click", function () {
        entry.label = entry.label === label ? "" : label;
        refresh();
      });
      labels.appendChild(btn);
    });
    card.appendChild(labels);

    var reason = document.createElement("textarea");
    reason.className = "reason";
    reason.placeholder = "Motivo (opcional)";
    reason.value = entry.reason;
    reason.addEventListener("input", function () { entry.reason = reason.value; });
    card.appendChild(reason);

    return card;
  }

  function applyCardState(card, entry) {
    card.className = "card" + (entry.label ? " " + entry.label : "");
    var buttons = card.querySelectorAll(".labels button");
    buttons.forEach(function (btn) {
      if (btn.dataset.label === entry.label) btn.classList.add("active");
      else btn.classList.remove("active");
    });
  }

  function visible(entry) {
    var s = sourceFilter.value;
    var l = labelFilter.value;
    if (s && entry.row.source !== s) return false;
    if (l === "none" && entry.label) return false;
    if (l && l !== "none" && entry.label !== l) return false;
    return true;
  }

  var cards = [];
  function build() {
    list.textContent = "";
    cards = state.map(function (entry, index) {
      var card = makeCard(entry, index);
      list.appendChild(card);
      return card;
    });
    refresh();
  }

  function refresh() {
    var counts = { interesting: 0, maybe: 0, irrelevant: 0, none: 0 };
    state.forEach(function (entry, index) {
      if (entry.label) counts[entry.label]++; else counts.none++;
      applyCardState(cards[index], entry);
      cards[index].classList.toggle("hidden", !visible(entry));
    });
    setText(document.getElementById("c-total"), state.length);
    setText(document.getElementById("c-interesting"), counts.interesting);
    setText(document.getElementById("c-maybe"), counts.maybe);
    setText(document.getElementById("c-irrelevant"), counts.irrelevant);
    setText(document.getElementById("c-none"), counts.none);
  }

  sourceFilter.addEventListener("change", refresh);
  labelFilter.addEventListener("change", refresh);

  function csvCell(value) {
    var s = value == null ? "" : String(value);
    if (/[",\\r\\n]/.test(s)) s = '"' + s.replace(/"/g, '""') + '"';
    return s;
  }

  function download() {
    var lines = [EXPORT_FIELDS.join(",")];
    state.forEach(function (entry) {
      var row = entry.row;
      var values = EXPORT_FIELDS.map(function (field) {
        if (field === "human_label") return csvCell(entry.label);
        if (field === "human_reason") return csvCell(entry.reason);
        return csvCell(row[field]);
      });
      lines.push(values.join(","));
    });
    var blob = new Blob(["\\ufeff" + lines.join("\\r\\n")], {
      type: "text/csv;charset=utf-8"
    });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "review_sample_labeled.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  document.getElementById("download").addEventListener("click", download);
  build();
})();
</script>
</body>
</html>
"""
)

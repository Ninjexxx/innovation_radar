# Innovation Radar

Automated innovation radar oriented toward **new possibilities**, not just technology trends or popularity.

## Purpose

The project looks for emerging signals that may represent new capabilities, new behaviors, unconventional combinations of technologies, experiments, or product, service, and experience opportunities relevant to Namu.

The radar's logic is:

**Automation discovers → AI filters → the team investigates**

The system must not become a news aggregator, an internal GitHub Trending, or a catalog of developer tools.

## Principles

1. **Popularity is evidence, not discovery.**
2. The radar looks for **new possibilities**, not necessarily new technologies.
3. Developer tools are only relevant when they clearly enable a new product, service, or experience capability.
4. The original source does not need to be about health for the signal to be relevant.
5. The final decision remains human.
6. The architecture should start simple and evolve only when a limitation is observed.

## Structure

```text
innovation-radar/
├── README.md
├── AGENTS.md
├── pyproject.toml
├── .gitignore
├── docs/
│   ├── 01_CONCEPT.md
│   ├── 02_ARCHITECTURE.md
│   ├── 03_MVP_SCOPE.md
│   ├── 04_DECISIONS.md
│   ├── 05_SIGNAL_POLICY.md
│   ├── 06_EVALUATION.md
│   ├── 07_HUMAN_JUDGMENT_ANALYSIS.md
│   ├── 08_GITHUB_DISCOVERY_ANALYSIS.md
│   ├── 09_REDDIT_DISCOVERY.md
│   └── 10_DETERMINISTIC_FILTER_EVALUATION.md
├── src/
│   └── innovation_radar/
│       ├── __main__.py
│       ├── config.py
│       ├── models.py
│       ├── logging_config.py
│       ├── pipeline.py
│       ├── collectors/
│       │   ├── github.py
│       │   ├── hackernews.py
│       │   ├── reddit.py
│       │   └── rss.py
│       ├── normalization/
│       ├── filtering/
│       │   ├── deterministic.py
│       │   └── evaluation.py
│       ├── analysis/
│       ├── reviews/
│       │   └── gold_set.py
│       ├── storage/
│       └── reports/
│           ├── deterministic_filtering.py
│           ├── human_judgment.py
│           ├── markdown.py
│           └── review_sample.py
├── tests/
│   └── fixtures/
└── data/
    ├── raw/
    ├── processed/
    └── reports/
```

## M0 — Foundation

M0 provides a runnable foundation with no collectors, network, or AI. It uses only the Python standard library at runtime and creates a local SQLite database with the minimal `RawItem` and `RunRecord` models.

### Requirements

- Python 3.11 or higher.

### Create and activate the environment

On PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

On Linux or macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### Install

```bash
python -m pip install -e ".[dev]"
```

### Run the tests

```bash
python -m pytest
```

### Initialize the database

```bash
python -m innovation_radar init-db
```

By default, the file is created at `data/innovation_radar.sqlite3`. Local databases are ignored by Git.

Settings can be changed directly through environment variables:

| Variable | Default | Values |
|---|---|---|
| `INNOVATION_RADAR_DB_PATH` | `data/innovation_radar.sqlite3` | Non-empty path to the local database |
| `INNOVATION_RADAR_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` |
| `INNOVATION_RADAR_REPORT_DIR` | `data/reports` | Directory for the raw reports |
| `INNOVATION_RADAR_HN_LIMIT` | `2` | Items per HN surface, between 1 and 100 |
| `INNOVATION_RADAR_RSS_LIMIT` | `2` | Items per feed, between 1 and 100 |
| `INNOVATION_RADAR_RSS_FEEDS` | Three validation feeds | JSON array of feeds with `id`, `name`, `url`, and optional `category` |
| `INNOVATION_RADAR_REVIEW_SAMPLE_LIMIT` | `12` | Maximum items in the review sample, between 1 and 100 |
| `INNOVATION_RADAR_GITHUB_LENSES` | Five conceptual lenses | JSON array with `id`, `description`, and `query` |
| `INNOVATION_RADAR_GITHUB_LIMIT` | `2` | Repositories per lens, between 1 and 20 |
| `INNOVATION_RADAR_GITHUB_RECENCY_DAYS` | `60` | Activity window in days, between 1 and 3650 |
| `INNOVATION_RADAR_GITHUB_MIN_STARS` | `0` | Optional anti-spam floor, between 0 and 100; not a ranking |
| `INNOVATION_RADAR_GITHUB_README_LIMIT` | `10` | Maximum READMEs fetched per run, between 0 and 50 |
| `GITHUB_TOKEN` | Absent | Optional token to raise the public API limits |
| `INNOVATION_RADAR_REDDIT_LENSES` | Five behavioral lenses | JSON array with `id`, `description`, `queries`, and `subreddits` |
| `INNOVATION_RADAR_REDDIT_LIMIT` | `8` | Maximum selected per lens, between 1 and 20 |
| `INNOVATION_RADAR_REDDIT_NEW_LIMIT` | `2` | Items requested from the `/new` surface per subreddit, between 0 and 10 |
| `INNOVATION_RADAR_REDDIT_RECENCY_DAYS` | `30` | Recent window, between 1 and 365 days |
| `REDDIT_CLIENT_ID` | Absent | ID of an OAuth client explicitly approved by Reddit |
| `REDDIT_CLIENT_SECRET` | Absent | Approved client secret; never persisted or logged |
| `INNOVATION_RADAR_REDDIT_USER_AGENT` | Absent | Identification in the format `platform:app:version (by /u/username)` |
| `INNOVATION_RADAR_ANALYSIS_PROVIDER` | `heuristic-offline` | M3 analysis provider; currently only `heuristic-offline` |

Example on PowerShell:

```powershell
$env:INNOVATION_RADAR_DB_PATH = "data/local.sqlite3"
$env:INNOVATION_RADAR_LOG_LEVEL = "DEBUG"
python -m innovation_radar init-db
```

M0 uses no credentials and does not load `.env` files.

## M1A — Discovery with Hacker News and RSS

M1A collects and normalizes a small sample, persists the items in SQLite, and generates a raw Markdown report. It does not classify relevance, compute an opportunity score, or sort items by popularity.

### Run a collection

```bash
python -m innovation_radar run
```

Each run creates or updates a `RunRecord` and writes the report to `data/reports` by default. The possible statuses are `completed`, `partial`, and `failed`.

An external item is identified by `(source, source_item_id)`. Re-encounters preserve `first_seen_at`, update `collected_at`, metrics, and payload, and do not create a new row.

### Hacker News

The collector uses the official public API:

- `https://hacker-news.firebaseio.com/v0/newstories.json`;
- `https://hacker-news.firebaseio.com/v0/showstories.json`;
- `https://hacker-news.firebaseio.com/v0/beststories.json`;
- `https://hacker-news.firebaseio.com/v0/item/<id>.json`.

The surfaces are queried in that order. Score and comments are stored only as raw metrics.

### RSS validation feeds

The defaults use a stable technical identifier separate from the display name:

| ID | Name | Category | URL |
|---|---|---|---|
| `mit_ai` | MIT News — Artificial Intelligence | `research` | `https://news.mit.edu/rss/topic/artificial-intelligence2` |
| `google_health` | Google — Health | `health` | `https://blog.google/technology/health/rss/` |
| `medium_healthtech` | Medium — Healthtech | `health` | `https://medium.com/feed/tag/healthtech` |

To replace the list on PowerShell:

```powershell
$env:INNOVATION_RADAR_RSS_FEEDS = '[{"id":"custom","name":"Custom feed","url":"https://example.com/feed.xml","category":"validation"}]'
python -m innovation_radar run
```

The `id` must remain stable; changing `name` does not change item identity. The collector accepts RSS and Atom, including the feed format documented by Medium. It does not follow links to scrape full content.

## M1B — Sample for human review

By default, the radar collects a small, daily sample suited to lightweight human review. Just run it, without configuring limits:

```powershell
python -m innovation_radar run
python -m innovation_radar export-review-sample
```

With the defaults (HN=2, RSS=2, GitHub=2, sample=12), the final list is around a dozen diverse items, rotated across sources. The sample remains neutral: no ranking, score, or automatic judgment decides what goes in.

For a larger validation cycle (for example, between 60 and 100 items), raise the limits explicitly:

```powershell
$env:INNOVATION_RADAR_HN_LIMIT = "20"
$env:INNOVATION_RADAR_RSS_LIMIT = "10"
$env:INNOVATION_RADAR_REVIEW_SAMPLE_LIMIT = "100"
python -m innovation_radar run
python -m innovation_radar export-review-sample
```

The second command reads the unique items from SQLite and writes, in the directory configured by `INNOVATION_RADAR_REPORT_DIR`:

- `review_sample.csv`: a UTF-8 sample ready for review, with `human_label` and `human_reason` empty;
- `review_sample_summary.md`: counts by source and surface/feed, covered period, duplicates avoided, and failures from the most recent run.

Selection performs a deterministic round-robin among provenance groups to preserve diversity. It does not use score, comments, or any other popularity metric to order, classify, or interpret the items. The later transformation into `tests/fixtures/signal_gold_set.json` depends on explicit human review.

### Review page (static HTML)

To review more comfortably than in the CSV, generate a static HTML page from the sample:

```powershell
python -m innovation_radar export-review-page
```

By default, the command reads `review_sample.csv` and writes `review.html` in the directory configured by `INNOVATION_RADAR_REPORT_DIR`. Use `--csv-path` and `--html-path` for specific paths.

The page opens directly in the browser, with no server, framework, or network. It shows the compact list (source, title with link, description), lets you filter by source and label, mark each item as `interesting`, `maybe`, or `irrelevant` with an optional reason, and download a labeled CSV (`review_sample_labeled.csv`). There is no ranking, score, or automatic judgment: the order is the same round-robin sample, and the decision remains human. Collected content is treated as untrusted external data and is never interpreted as HTML.

### Review memory (daily cycle)

To avoid reviewing the same item twice, record the downloaded labels back into the radar:

```powershell
python -m innovation_radar mark-reviewed "C:\path\review_sample_labeled.csv"
```

The command reads the labeled CSV, validates the labels (`interesting`, `maybe`, `irrelevant`), skips rows still without a label, and stores the decisions in a local memory in SQLite. From then on, `export-review-sample` automatically excludes any already-reviewed item. A reviewed item does not reappear; if all candidates have already been reviewed, the export fails and asks for a new collection.

The daily cycle is:

```powershell
python -m innovation_radar run
python -m innovation_radar export-review-sample
python -m innovation_radar export-review-page
# open review.html, mark items, download review_sample_labeled.csv
python -m innovation_radar mark-reviewed review_sample_labeled.csv
```

## M1C — Gold Set v0.1 and human judgment analysis

Once `review_sample.xlsx` has been fully reviewed, import it with:

```powershell
python -m innovation_radar import-gold-set "C:\path\review_sample.xlsx" --expected-count 90
```

The command validates the entire spreadsheet before writing any result. It fails clearly when it finds:

- a label other than `interesting`, `maybe`, or `irrelevant`;
- an empty label or reason;
- a duplicate `item_id`;
- a missing required column;
- a metric that is not a valid JSON object;
- a count different from `--expected-count`.

Default outputs:

- `tests/fixtures/signal_gold_set.json`: a deterministic reference with the human judgments and the workbook's SHA-256;
- `docs/07_HUMAN_JUDGMENT_ANALYSIS.md`: overall distribution, quality by surface/feed, textual indicators from the reasons, and possible policy calibration points.

The analysis uses only counts and transparent lexical matching. It does not correct labels, decide divergences, change `docs/05_SIGNAL_POLICY.md`, or use an LLM.

## M1D — GitHub Discovery

GitHub participates in the same command and sequential pipeline already used by the previous sources:

```powershell
python -m innovation_radar run
python -m innovation_radar export-review-sample
```

The collector uses only the official REST API:

- `GET https://api.github.com/search/repositories` to find repositories;
- `GET https://api.github.com/repos/<owner>/<repo>/readme` to enrich a limited number of candidates when the README is available.

Searches are split into five configurable lenses: health and wellness; wearables and sensors; voice, computer vision, and multimodality; local capabilities and new interfaces; personal data and transferable experiments. Each search gets a `pushed:>=...` window, its own limit, and ordering by `updated`. The final results go through a round-robin across lenses and deduplication by the repository's numeric ID. There is no final ordering by stars.

Stars, forks, issues, language, topics, and dates remain descriptive metadata. The default `INNOVATION_RADAR_GITHUB_MIN_STARS=0` does not exclude small projects; if configured, that floor serves only as a simple spam control.

To replace the lenses on PowerShell:

```powershell
$env:INNOVATION_RADAR_GITHUB_LENSES = '[{"id":"wearable_trials","description":"Wearable experiments","query":"wearable OR biosensor"}]'
$env:INNOVATION_RADAR_GITHUB_RECENCY_DAYS = "30"
python -m innovation_radar run
```

`GITHUB_TOKEN` is optional. Without it, the collector accesses only public data and is subject to the unauthenticated search limit reported by GitHub. With it, it sends `Authorization: Bearer ...`; the value is never written to SQLite, reports, or logs. There is no `.env` loading.

README enrichment is deliberately limited: only the first diverse candidates, up to `INNOVATION_RADAR_GITHUB_README_LIMIT`, are queried. SQLite preserves an excerpt of up to 1,200 characters, the source URL, and file metadata, not a full copy of the README. Use `0` to disable these extra calls.

In the CSV sample, the provenance column contains the lenses that found the repository, `available_metrics` contains GitHub dates and metadata, and `short_description` includes the README excerpt when available. The human judgment fields remain empty.

## M1D.1 — Gold Set v0.2 and discovery lens analysis

After the human review of `review_sample_github.xlsx`, merge it onto Gold Set v0.1 with:

```powershell
python -m innovation_radar merge-github-gold-set "C:\path\review_sample_github.xlsx"
```

Before writing, the command validates the 43 records, requires exactly 40 items with `source=github`, checks the distribution `interesting=17`, `maybe=4`, `irrelevant=19`, and preserves the 90 existing non-GitHub items. The three Hacker News records present in the workbook are validated but do not enter the merge.

Default outputs:

- `tests/fixtures/signal_gold_set.json`: a deterministic Gold Set v0.2 with 130 judgments and provenance from both workbooks;
- `docs/08_GITHUB_DISCOVERY_ANALYSIS.md`: distribution by lens, textual noise patterns, comparison with HN/RSS, and possible calibration points.

The command can be repeated on the Gold Set v0.2 itself: identical records are not duplicated, and any conflict in an `item_id`'s content stops the process. The analysis does not change labels, lenses, queries, filters, or the Signal Policy, and does not use an LLM.

## M1E — Reddit Discovery

**Status:** Implemented — real validation pending external Reddit approval.

The collector uses exclusively the [Reddit Data API](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki), with application-only OAuth and read scope. The current rules require explicit approval; use by or on behalf of companies also requires written authorization. There is no fallback to scraping or anonymous JSON endpoints.

After obtaining approval and registering a compliant client, configure it on PowerShell:

```powershell
$env:REDDIT_CLIENT_ID = "approved-client-id"
$env:REDDIT_CLIENT_SECRET = "approved-client-secret"
$env:INNOVATION_RADAR_REDDIT_USER_AGENT = "windows:namu-opportunity-radar:v0.1 (by /u/app-username)"
$env:INNOVATION_RADAR_REDDIT_RECENCY_DAYS = "30"
python -m innovation_radar run
python -m innovation_radar export-review-sample
```

Without the three access variables, the Reddit source records an explicit authentication failure and the other sources remain isolated. Credentials are not loaded from `.env`, persisted in SQLite, or shown in logs.

The five default lenses are:

| Lens | Default candidate communities |
|---|---|
| `personal_health_behavior` | `r/QuantifiedSelf`, `r/ouraring`, `r/Garmin` |
| `unmet_needs` | `r/QuantifiedSelf`, `r/caregiving`, `r/disability` |
| `ai_in_real_life` | `r/LocalLLaMA`, `r/selfhosted`, `r/ChatGPT` |
| `accessibility_care_interfaces` | `r/accessibility`, `r/caregiving`, `r/AgingParents` |
| `personal_data_and_automation` | `r/selfhosted`, `r/homeassistant`, `r/ObsidianMD` |

Each community is queried with `sort=new`; a small sample from `/new` is also combined when `INNOVATION_RADAR_REDDIT_NEW_LIMIT` is greater than zero. The post timestamp applies the exact window, and the round-robin by lens and community avoids ordering by upvotes. The same ID found across several searches yields a single `RawItem` with all provenances preserved.

To replace lenses and communities:

```powershell
$env:INNOVATION_RADAR_REDDIT_LENSES = '[{"id":"care_needs","description":"Care needs and workarounds","queries":["I wish","how do you manage"],"subreddits":["caregiving","AgingParents"]}]'
```

The CSV sample shows `r/<subreddit>` and all discovery lenses in the provenance column. Score, number of comments, and flair appear only in `available_metrics`; `human_label` and `human_reason` remain empty.

For data minimization, the collector preserves at most 2,000 characters of the public body and does not query profiles, private messages, or comment trees. Deleted authors are not stored. Operational use must also comply with Reddit's obligations to remove content or identifiers that have been deleted at the source.

## M2 — Deterministic filters in shadow mode

M2 computes objective noise after the `RawItem` is persisted, without removing or changing items. Each decision is explainable and uses only:

- `keep`;
- `noise_flag`;
- `discard_candidate`;
- `rule_id`, reason, and observable evidence.

To reproduce the evaluation over the 130 judgments of Gold Set v0.2:

```powershell
python -m innovation_radar evaluate-filters
```

The command validates `tests/fixtures/signal_gold_set.json` and recreates `docs/10_DETERMINISTIC_FILTER_EVALUATION.md`. In the current set, the observed scenario is 8 `discard_candidate`, 48 items with `noise_flag` only, and 74 `keep`; the 8 candidates are `irrelevant`, with zero `interesting` and zero `maybe`.

The `run` command also computes these decisions in shadow mode and records them in the raw report. All items remain in `DiscoveryResult.items` and in SQLite. There is no opportunity classification, developer-tooling filter, semantic deduplication, LLM, or M3 component.

## M3 — Opportunity AI

M3 introduces the first interpretation layer. It produces a structured analysis per item following the questions in `docs/01_CONCEPT.md` and the contract in `docs/02_ARCHITECTURE.md` section 11. The output is not a ranking, and the recommendation (`investigate`, `watchlist`, `archive`) is a suggestion; the final decision remains human.

The AI provider is replaceable behind the `OpportunityProvider` protocol. The default is `heuristic-offline`: deterministic, without network and without credentials, so the pipeline stays runnable without any API key. A real LLM provider would implement the same protocol without changing the engine, the CLI, or the report.

Only items that survive the M2 deterministic filter are sent to the provider. Items marked as `discard_candidate` are skipped and listed in the report with the reason.

To analyze Gold Set v0.2 and write the report:

```powershell
python -m innovation_radar analyze-opportunities
```

To analyze the items already persisted in the local SQLite:

```powershell
python -m innovation_radar analyze-opportunities --source sqlite
```

By default, the report is written to `docs/11_OPPORTUNITY_ANALYSIS.md`. Each item receives a signal type, summary, what is new, new capability, product possibility, Namu relevance, a developer-tooling flag, five explanatory scores from 1 to 5, traction, and the suggested recommendation. No human Gold Set label is changed, and no API key is required, persisted, or logged.

## M4 — Calibration

M4 compares the M3 recommendations with the human labels of Gold Set v0.2, following `docs/06_EVALUATION.md`. It measures divergences; it does not validate the system as correct and does not adjust rules or prompts automatically.

The mapping is explicit:

- `interesting` ↔ `investigate`
- `maybe` ↔ `watchlist`
- `irrelevant` ↔ `archive`

Items skipped by the M2 deterministic filter (`discard_candidate`) never reached the provider; their effective decision is treated as `archive`, so a skipped `interesting` item counts as a false negative.

```powershell
python -m innovation_radar calibrate
```

By default, the report is written to `docs/12_CALIBRATION.md`. It includes exact agreement, a confusion matrix, false positives (the system asks for attention when the human marked `irrelevant`), false negatives (the system archives when the human marked `interesting`), `maybe` divergences with the human reason, and breakdowns by source, signal type, and developer tooling. False negatives take priority over false positives. Divergences are evidence for human decision, not automatic correction, and no Gold Set label is changed.

## First phase

The first goal is not to use AI.

The initial MVP must prove that the chosen sources can bring material worth analyzing:

**Reddit + Hacker News + GitHub + Medium/RSS → normalization → SQLite → Markdown report**

Only after validating the raw material does the AI layer come in.

Read `docs/03_MVP_SCOPE.md` before implementing.

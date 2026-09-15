# Mission

This repository implements an automated Opportunity Radar for Namu.

The radar is NOT a technology popularity tracker, a news aggregator, or a GitHub Trending clone.

Its purpose is to discover emerging capabilities, behaviors, experiments and technology combinations that may enable new health, wellness, product or service opportunities.

# Source of truth

Before changing discovery, ranking, filtering or analysis behavior, read:

- docs/01_CONCEPT.md
- docs/02_ARCHITECTURE.md
- docs/05_SIGNAL_POLICY.md

For the current implementation scope, read:

- docs/03_MVP_SCOPE.md

Record meaningful architectural or product decisions in:

- docs/04_DECISIONS.md

Evaluation rules and calibration guidance live in:

- docs/06_EVALUATION.md

# Core invariants

1. Popularity is evidence, not discovery.
2. Product possibility matters more than developer popularity.
3. Developer tooling should normally be filtered or deprioritized.
4. A signal does not need to originate in healthcare to be relevant to Namu.
5. Human review remains the final decision layer.
6. Do not add complexity before the current MVP is validated.
7. Do not introduce a new source, model, database, dashboard or infrastructure layer without an observed need.
8. Raw collected data must be preserved before transformation.
9. LLM providers must be replaceable and must not define the system architecture.
10. The MVP must be able to run without any LLM API key.

# Engineering principles

- Python 3.11+
- Prefer simple modules and explicit interfaces.
- Isolate each external source behind a collector.
- Normalize all collected items into a shared internal model.
- Preserve raw payloads or source snapshots when legally and technically appropriate.
- Keep deterministic filtering separate from LLM-based analysis.
- Every transformation should be testable.
- No secret, token or API key may be committed.
- Prefer standard library and small dependencies over complex frameworks.
- Do not add orchestration frameworks unless a concrete limitation requires them.

# Validation

Before considering a task complete:

1. Run the relevant tests.
2. Run the full test suite when practical.
3. Inspect representative real output, not only unit tests.
4. Do not silently change product criteria to make tests pass.
5. If a source is unavailable or restricted, fail clearly and document the limitation.

# Working style for Codex

For non-trivial changes:

1. Read the relevant docs first.
2. Explain the intended change briefly.
3. Implement one bounded task.
4. Add or update tests.
5. Report what changed, what was tested, and any unresolved limitation.

Do not attempt to build the entire radar in one change.

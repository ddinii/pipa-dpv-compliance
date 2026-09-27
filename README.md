# PIPA-DPV Compliance Prototype

A machine-readable PIPA (Personal Information Protection Act) compliance
prototype. Input facts are structured into a frozen Fact contract, mapped
onto a frozen ontology, and evaluated by a deterministic rule engine to
produce a `GREEN` / `AMBER` / `RED` / `N/A` `RuleResult` per rule.

> **`GREEN` is not a legal compliance certification. `RED` is not
> confirmation of a legal violation.** Results indicate whether the
> machine-readable Facts required by a rule were confirmed, missing, or
> uncertain in the given input — not a final legal judgment. LLMs (where
> used) only extract Facts; they never assign rule status or make legal
> determinations.

## The three PoCs

The project implements three **equal** proof-of-concept scenarios. None of
them is "Main" or "Sub."

| PoC | Scenario | Input |
|---|---|---|
| **PoC1** | 개인정보 처리방침 준수점검 | Privacy policy text |
| **PoC2** | 개인정보 침해사고 통지 요건 검토 지원 | Incident + notification/response information |
| **PoC3** | Privacy-by-Design 개발지원 | Structured Privacy-by-Design form |

## Architecture

```
Input
  → Fact (fact-1.0 envelope)
  → Fact Schema Validation      (app/mapping/fact_schema.py)
  → RDF / Ontology Mapping      (app/mapping/ontology_mapper.py — OntologyMapper)
  → P0 Rule Engine              (app/rules/engine.py — P0RuleEngine, deterministic)
  → RuleResult                  (app/rules/models.py)
  → REST API                    (FastAPI, app/api/compliance.py)
  → UI                          (shared RuleResult UI, frontend/src/components)
```

- The REST API is implemented with **FastAPI** (`app/main.py`), extending a
  single existing application — there is no second backend.
- The **Fact contract** (`fact-1.0` envelope), the ontology mapping
  (`FACT_SPECS` in `app/mapping/mapping_registry.py`), and the P0 rule set
  are frozen and reused as-is; API and UI work depends on this stable
  contract rather than on any specific LLM implementation.
- `value_state` on every Fact is one of **`confirmed` / `unknown` /
  `absent`**, and these are never collapsed into one another. Missing or
  unextracted information is **not** automatically `N/A`.
- All three PoCs render results through the same frontend `RuleResult`
  components (see `frontend/src/pages`), and all three go through the same
  `OntologyMapper` → `P0RuleEngine` pipeline.
- LLMs, where used, only extract Facts. They never assign
  `GREEN`/`AMBER`/`RED`/`N/A` and never make a legal-compliance
  determination; that is the sole responsibility of the deterministic
  `P0RuleEngine`.

## Extractor / builder state

| PoC | Fact producer | Status |
|---|---|---|
| PoC1 | `MockPoC1Extractor` (`app/extractors/poc1_mock_extractor.py`) | Implements the `Poc1Extractor` protocol; returns a fixed scenario. Prepared for replacement with a real LLM-backed `Poc1Extractor`. |
| PoC2 | `MockPoc2Extractor` (`app/extractors/poc2_mock_extractor.py`) | Implements the `Poc2Extractor` protocol; returns a fixed scenario. Prepared for replacement with a real LLM-backed `Poc2Extractor`. |
| PoC3 | `build_poc3_facts()` (`app/builders/poc3_fact_builder.py`) | Structured form → Facts, no LLM extraction step in this design. |

PoC3's pipeline is:

```
structured form → build_poc3_facts() → Frozen Facts → OntologyMapper → P0RuleEngine
```

This is the current design, not an incomplete state — PoC3 does not require
an LLM extractor.

The mock extractors ignore their input content and always return a fixed
Fact scenario; they exist to validate the extractor → mapper → engine →
API → UI pipeline end-to-end before a real extractor is wired in. See
[`docs/context/backend/LLM_EXTRACTOR_HANDOFF.md`](docs/context/backend/LLM_EXTRACTOR_HANDOFF.md)
for the exact replacement contract.

## Frozen scope

| PoC | Facts | P0 Rules |
|---|---|---|
| PoC1 | 12 (F1-01–F1-12) | 6 (P1-R01, P1-R02, P1-R03, P1-R04, P1-R06, P1-R07) |
| PoC2 | 10 (F2-01–F2-10) | 4 (P2-R01, P2-R02, P2-R03, P2-R08) |
| PoC3 | 13 (F3-01–F3-13) | 8 (P3-R01, P3-R02, P3-R03, P3-R04, P3-R05, P3-R06, P3-R08, P3-R11) |
| **Total** | **35 Facts** | **18 P0 Rules** |

Every Fact carries a `value_state` of `confirmed`, `unknown`, or `absent`.
These three states are semantically distinct and must never be converted
into one another (e.g. `unknown` → `absent` is not allowed). See
[`docs/context/core/CONTRACTS.md`](docs/context/core/CONTRACTS.md) for the
full Fact envelope and RuleResult contract, and
[`docs/P0_RULE_MATRIX.md`](docs/P0_RULE_MATRIX.md) for a rule-by-rule
summary. This README does not duplicate the full Fact Dictionary or Rule
Specification.

## Setup

Requires **Python 3.10**.

```bash
python3.10 -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Frontend dependencies:

```bash
cd frontend
npm install
```

### Environment variables

Backend — copy [`.env.example`](.env.example) to `.env` if you need to
override these (none are secret; the FastAPI app itself does not currently
read them at startup — `APP_HOST`/`APP_PORT` are placeholders for future
process configuration, not consumed by `app/main.py` today):

```
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000
FRONTEND_ORIGIN=http://localhost:5173
LLM_PROVIDER=
LLM_MODEL=
LLM_API_KEY=
```

Frontend — copy `frontend/.env.example` to `frontend/.env` to point the UI
at a non-default backend URL:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Never commit `.env` files or put real secrets in `.env.example`; provide
real credentials only via environment variables at runtime.

## Running the backend

From the repository root, with the virtualenv activated:

```bash
uvicorn app.main:app --reload
```

- API base URL: `http://127.0.0.1:8000`
- Interactive docs (Swagger UI): `http://127.0.0.1:8000/docs`

## Running the frontend

```bash
cd frontend
npm run dev
```

- Dev server: `http://localhost:5173` (Vite default; the backend's CORS
  configuration in `app/main.py` explicitly allows this origin)
- The frontend calls the backend at `VITE_API_BASE_URL`, defaulting to
  `http://127.0.0.1:8000` if unset (`frontend/src/api/client.ts`).

## API endpoints

Current three-PoC compliance pipeline (`app/api/compliance.py`, prefix
`/api/v1/compliance`):

| Method | Path | PoC |
|---|---|---|
| `POST` | `/api/v1/compliance/policy-check` | PoC1 |
| `POST` | `/api/v1/compliance/breach-check` | PoC2 |
| `POST` | `/api/v1/compliance/design-check` | PoC3 |

Each returns `{ "poc": "PoC1"|"PoC2"|"PoC3", "rule_results": [...] }`, where
each `rule_results` entry mirrors `RuleResult.to_dict()`
(`app/rules/models.py`).

Health check:

| Method | Path |
|---|---|
| `GET` | `/health` |

**Legacy endpoint** (`app/api/validate.py`, prefix `/api/v1`):

| Method | Path |
|---|---|
| `POST` | `/api/v1/validate` |

This is an older `ProcessingFact` → SHACL validation prototype
(`app/services/validator.py`, `rules/article17_consent.ttl`). It is kept
available but is **not** part of the current three-PoC
Fact/OntologyMapper/P0RuleEngine pipeline described above — do not treat it
as equivalent to the compliance endpoints.

## Testing

Backend (repository-standard command):

```bash
python -m pytest -q
```

As of this writing this reports `134 passed` — a **current snapshot**, not
a permanent expected count. The number will change as the real PoC1/PoC2
LLM extractors and further scope are integrated; re-run the command to get
the current result rather than relying on this figure.

Frontend, from `frontend/`:

```bash
npm run build   # tsc -b && vite build
npm run lint    # oxlint
```

## Safety / interpretation

- `GREEN` is not a legal compliance certification.
- `RED` is not confirmation of a legal violation.
- PoC2 v1 does not automatically determine `ReportingObligation`.
- Enforcement Decree notification/reporting thresholds are out of scope for
  the current P0 rules.
- Final legal judgment requires separate human review.

## LLM extractor integration

PoC1 and PoC2 currently run on mock extractors. To integrate a real
LLM-backed `Poc1Extractor` / `Poc2Extractor`, follow the exact protocol,
Fact output contract, and replacement points documented in
[`docs/context/backend/LLM_EXTRACTOR_HANDOFF.md`](docs/context/backend/LLM_EXTRACTOR_HANDOFF.md).

## Further reading

- [`docs/context/INDEX.md`](docs/context/INDEX.md) — task-scoped context
  index; read only the files relevant to the task at hand.
- [`docs/context/core/PROJECT.md`](docs/context/core/PROJECT.md),
  [`PIPELINE.md`](docs/context/core/PIPELINE.md),
  [`CONTRACTS.md`](docs/context/core/CONTRACTS.md) — project scope, the
  canonical pipeline, and the frozen Fact/RuleResult contracts.
- [`docs/context/backend/EXISTING_CODE.md`](docs/context/backend/EXISTING_CODE.md) —
  existing reusable backend modules and the integration principle for new
  routes.
- [`docs/P0_RULE_MATRIX.md`](docs/P0_RULE_MATRIX.md) — rule-by-rule summary
  of all 18 P0 rules.

## Fact Extractor and evaluation set

The LLM Fact Extractor for PoC1, the gold Fact sets, the controlled variants and
the scorer live under `evals/`. See [`evals/README.md`](evals/README.md) for how
to rebuild the gold sets, run the variant checks, and score an extraction run.

```powershell
python evals\poc1\build_gold_facts.py
python evals\poc1\build_variants.py
python -m pytest -q tests\test_gold_facts_poc1.py tests\test_variants_poc1.py
```

Running `evals\run_extraction.py` calls the Claude API and costs money; it is not
part of the test suite.

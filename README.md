# Clarity Pay — Data & Visualization Engineering Take-Home

Welcome, and thanks for taking the time. This is a focused, **one-working-day**
exercise that mirrors real work on our Risk & Analytics team: deriving reliable
answers from a transactional ledger and a fraud graph, then presenting them
clearly.

## What's in this folder

| Path | What it is |
|---|---|
| `ASSIGNMENT.md` | **The brief.** Read this first — Parts A, B, and C with each task. |
| `DATA_DICTIONARY.md` | Table and column reference for the dataset. |
| `data/` | The dataset: 5 CSVs + `schema.sql` (DDL + loader + indexes). |
| `sql/` | Put your `partA.sql` and `partB.sql` here. |
| `python/` | Put your Plotly / NetworkX code here (script or notebook). |
| `figures/` | Export your charts here (PNG or HTML). |
| `NOTES.md` | A short write-up template — fill it in (assumptions, a trade-off, etc.). |
| `AI_USAGE.md` | Disclose how you used AI tools (template — see below). |

## Setup

You need PostgreSQL (local or containerized) and Python 3 with `pandas`,
`plotly`, `networkx`, and a Postgres driver (`psycopg[binary]` or `SQLAlchemy`).

```bash
# from the data/ directory, with Postgres running:
createdb claritypay
psql claritypay -f schema.sql      # creates tables and loads the CSVs
```

Sanity check after loading:

```sql
SELECT 'plans' AS table, count(*) FROM plans
UNION ALL SELECT 'installments', count(*) FROM installments
UNION ALL SELECT 'account_links', count(*) FROM account_links;
-- expected: 6462 / 33574 / 928
```

Treat **2026-06-22** as "today" for any overdue / aging calculation.

## Deliverables

```
sql/partA.sql        A1–A4, executable, commented by question
sql/partB.sql        B1–B4, using recursive CTEs
python/              C1–C3 (and optionally C4) code that produces the figures
figures/             exported PNG or HTML of your charts
NOTES.md             one page max: assumptions, a trade-off, more-time, reflections
AI_USAGE.md          how you used AI tools on this assignment
```

## Ground rules

- **The exercise is tiered.** Do the **(Core)** items first; **(Stretch)** items
  distinguish stronger submissions. A few correct, well-documented answers beat
  many incomplete ones.
- **Make and state assumptions.** Where the brief is silent, choose a reasonable,
  defensible interpretation and record it in `NOTES.md` rather than waiting.
- **Using AI is allowed and expected** — we build with AI ourselves. Just be
  transparent about it in `AI_USAGE.md`. We care how you scope, review, and
  exercise judgment, not whether you typed every character.

## Submitting

Send a compressed archive of this folder (with your `sql/`, `python/`,
`figures/`, `NOTES.md`, and `AI_USAGE.md` filled in), or a link to a Git
repository.

Good luck — we're looking forward to seeing how you think.

# Clarity Pay - Data and Visualization Engineering Assignment

## Overview

This assignment reflects the work of our Risk and Analytics team: deriving
reliable answers from a transactional ledger and a fraud graph, and presenting
those answers clearly. You will be assessed on correctness, command of advanced
SQL (common table expressions, recursive CTEs, window functions, and ranking
functions), graph reasoning, code quality, and the clarity of your written
reasoning.

- Database: PostgreSQL.
- Visualization: Python, using Plotly and NetworkX.
- Expected effort: approximately one working day.

The assignment is tiered. Items marked **(Core)** establish the baseline and
should be completed first. Items marked **(Stretch)** are more demanding and are
used to distinguish stronger submissions. A smaller number of correct,
well-documented answers is preferred over a larger number of incomplete ones.

## Scope and Assumptions

Real datasets are imperfect and requirements are rarely exhaustive. Where this
brief is silent or ambiguous, you are expected to make reasonable, defensible
assumptions and proceed rather than wait for clarification. Each assumption must
be:

1. stated explicitly in `NOTES.md` (and, where relevant, in a comment beside the
   query it affects);
2. internally consistent across your submission; and
3. justifiable on business or data-quality grounds.

We evaluate the quality of your reasoning, not your ability to guess an
unstated intent. A sound assumption, clearly documented, is always acceptable.

## Background

Clarity Pay is a Buy-Now-Pay-Later (BNPL) provider. A customer completes a
purchase at a merchant; Clarity Pay settles with the merchant immediately and
the customer repays Clarity Pay in scheduled installments (for example
`pay_in_4` or `pay_monthly_12`). Every scheduled payment is recorded as a row in
the installment ledger.

Separately, the fraud team maintains an account-linkage graph. Two accounts are
connected when they share an identifying signal (device, card, bank account,
address, and so on). Stronger signals are represented as shorter distances.

This assignment covers both domains: repayment analytics (Part A), the linkage
graph (Part B), and a visualization layer over both (Part C).

## Setup

1. Ensure a PostgreSQL instance is available (local or containerized).
2. From the `data/` directory:

   ```bash
   createdb claritypay
   psql claritypay -f schema.sql      # creates the tables and loads the CSV files
   ```

3. Review `DATA_DICTIONARY.md` for the full table and column reference. Note in
   particular:
   - Treat **2026-06-22** as the current date for any overdue or aging calculation.
   - In `account_links`, a **lower `link_distance` indicates a stronger link**, and
     every edge is stored in **both directions**.

Sanity check after loading:

```sql
SELECT 'plans' AS table, count(*) FROM plans
UNION ALL SELECT 'installments', count(*) FROM installments
UNION ALL SELECT 'account_links', count(*) FROM account_links;
-- expected: 6462 / 33574 / 928
```

---

## Part A - Repayment and Merchant Analytics

Concepts assessed: common table expressions, window aggregates, `LAG`,
`RANK` / `DENSE_RANK` / `ROW_NUMBER`, and `NTILE`.

Place your answers in `sql/partA.sql`, with each question identified by a
comment. Every query must execute without modification against the loaded
database.

**A1 - Plan amortization and running balance. (Core)**
For each plan, list its installments in order together with a running
outstanding balance, defined as `total_repayable_usd` less the cumulative
`amount_due_usd` settled to date.
Required columns: `plan_id, installment_no, due_date, amount_due_usd,
running_paid, outstanding_balance`.
The final row of a fully repaid plan must show `outstanding_balance = 0`. Use a
window function rather than a self-join.

**A2 - Merchant delinquency ranking by category. (Core)**
Define a merchant's delinquency rate as
`(missed + written_off + late) / (all installments that are due, i.e. excluding 'scheduled')`.
Rank merchants by delinquency rate within each category and return the three
worst-performing merchants per category.
Required columns: `category, merchant_id, name, due_installments,
delinquency_rate, rank_in_category`.
Use `DENSE_RANK`. In a comment, state in one sentence how the result would differ
had you used `RANK` or `ROW_NUMBER`.

**A3 - Collections momentum, month over month. (Core)**
For each merchant and calendar month, compute the total amount actually collected
and the percentage change relative to the merchant's previous month.
Required columns: `merchant_id, month, collected_usd, prev_month_collected,
mom_pct_change`.
Use `LAG`. Handle the first month and any division by zero explicitly.

**A4 - Customer segmentation. (Core)**
Assign every customer to a quartile based on lifetime on-time rate, defined as
the proportion of due installments paid on or before the due date. Label the
quartiles `Q1 (best)` through `Q4 (worst)`.
Required columns: `customer_id, due_installments, on_time_rate, quartile`.
Use `NTILE(4)` or `PERCENT_RANK`. State and justify your treatment of customers
with no due installments.

---

## Part B - Account-Linkage Graph

Concepts assessed: recursive CTEs, path reconstruction, cycle prevention, and
the distinction between shortest-path and least-cost-path traversal.

Place your answers in `sql/partB.sql`. Use a recursive CTE for B1 through B4. Do
not hard-code hop counts and do not emulate traversal with per-hop self-joins.

Use the following confirmed-fraud account as the worked example throughout:
**`customer_id = 700`** (`is_confirmed_fraud = true`).

**B1 - Reachability. (Core)**
Starting from account 700, identify every account reachable within four hops.
Return each account once, with the minimum hop count required to reach it.
Required columns: `customer_id, hops`.
Maintain the visited path in an array, prevent revisiting nodes (cycle guard),
and cap the recursion depth.

**B2 - Strongest evidence chain (least-cost path). (Stretch)**
Determine the least-cost path - the path with the minimum total `link_distance` -
from account 700 to applicant `customer_id = 2800`. Return the full chain of
accounts, the total distance, and the number of hops.
Required columns: `path` (ordered array of customer ids), `total_distance, hops`.

**B3 - Fewest-hops path. (Core)**
Determine the fewest-hops path from account 700 to account 2800.
In a comment, explain in one or two sentences why the least-cost path (B2) may
contain more hops than the fewest-hops path while still representing stronger
evidence, and which result the fraud team should rely on.

**B4 - Single-source least-cost distances (ring sizing). (Stretch)**
In a single query, return the least-cost distance from account 700 to every
account it can reach, ordered by distance. State, in a comment, how many accounts
fall within a total distance of 5 or less of account 700. Consider `DISTINCT ON`
to retain only the cheapest route per destination.

---

## Part C - Visualization Layer (Python, Plotly and NetworkX)

Place your code in `python/`. A script or a notebook is acceptable. Keep database
credentials out of source control (use environment variables or a small
configuration file). Parameters such as the source and target accounts must be
variables, not values embedded in query strings.

**C1 - Data access. (Core)**
Load the results of your Part A and Part B queries into pandas DataFrames, using
psycopg or SQLAlchemy.

**C2 - Linkage graph visualization. (Stretch)**
Render the neighborhood of account 700 with NetworkX. Color nodes by
`is_confirmed_fraud` and, optionally, by `risk_band`; encode link strength
through edge width or labels. Overlay and highlight the least-cost path from B2
so that the 700-to-2800 chain is immediately apparent. Source and target must be
parameters.

**C3 - Analytics dashboard. (Core)**
Produce two Plotly figures: a collections time-series incorporating the running
total from A1 or A3, and a ranked bar chart of the worst-delinquency merchants
from A2. Titles, axis labels, and hover text must make each figure
self-explanatory.

**C4 - Extension. (Stretch)**
Complete one of the following: add interactivity (for example, a control to
re-select the path endpoints and re-render the graph); produce a cohort repayment
curve (on-time rate by months since signup); or present a concise written insight
supported by one of your figures.

---

## Deliverables

```
sql/partA.sql        A1 through A4, executable, commented by question
sql/partB.sql        B1 through B4, using recursive CTEs
python/              C1 through C3 (and C4) code that produces the figures
figures/             exported PNG or HTML of your charts
NOTES.md             one page maximum: assumptions, one trade-off encountered,
                     and what you would do with additional time
```

Submit a compressed archive or a link to a Git repository.

## Assessment Criteria

- SQL that executes without modification and handles edge cases correctly,
  including the first month in a series, ties, division by zero, future
  (`scheduled`) installments, and customers with no due installments.
- Part B queries that return the true optimum with a reconstructed path, are
  cycle-safe, and terminate.
- Figures that answer a clearly defined question, with the B2 path distinctly
  highlighted on the graph.
- A `NOTES.md` that demonstrates understanding of the underlying business
  trade-offs, in particular the difference between fewest-hops and
  strongest-evidence paths, and that records your assumptions.

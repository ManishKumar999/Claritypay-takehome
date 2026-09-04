# AI Usage

## How I used AI

I used OpenAI Codex throughout the assignment as an implementation and review
partner. It helped me inspect the dataset, explain unfamiliar SQL concepts,
draft the SQL and Python, run queries against local PostgreSQL, and create the
Plotly/NetworkX outputs. I worked iteratively: I asked for plain-English
explanations, challenged logic I did not understand, selected assumptions, and
reviewed actual query results before accepting changes. AI produced most of the
initial code; I directed the analysis and required revisions where the behavior
did not match my interpretation of the business question.

## Prompts that mattered

### 1. Repayment definitions and edge cases

> Help me identify the assumptions and edge cases for plan amortization and
> customer on-time segmentation before writing SQL.

This exposed the installment-rounding discrepancy, distinguished contractual
amounts from cash collected, and led to explicit treatment of partial payments
and customers without due history.

### 2. Graph traversal from first principles

> Explain the account-link table, recursive traversal, cycle prevention,
> fewest-hops paths, and least-cost paths in plain English before writing Part B.

This helped me understand why the direct one-hop link from 700 to 2800 is weaker
under the supplied weights than the three-hop device/card/device route.

### 3. Reproducible visual outputs

> Load the completed SQL results into pandas and build the required Plotly and
> NetworkX figures with database credentials kept outside source control.

This produced the reusable data-access module and the first chart drafts, which I
then reviewed and revised—for example, adding the delinquency formula and
numerator/denominator labels directly to the merchant chart.

## Owned vs. delegated

- **Owned:** interpretation of the questions; decisions about settlement,
  no-history customers, and tie-breaking; requests for simpler explanations;
  review of SQL outputs and chart clarity; selection of the cohort curve for C4.
- **Delegated:** first-draft SQL and Python, repetitive database plumbing,
  visualization boilerplate, formatting, and automated verification commands.

## Where AI got it wrong

- An early graph explanation drew two-hop intermediate edges without first
  verifying them. I questioned the result; the final paths and figures use
  database-verified edges.
- The first A4 draft placed customers with no due installments into `NTILE`,
  which mixed unknown repayment performance into the worst quartile. I changed
  the requirement so only customers with due history receive Q1–Q4; other
  customers remain visible with descriptive labels and a `NULL` rate.

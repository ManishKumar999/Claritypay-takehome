# Clarity Pay — Data Dictionary

Five tables. `customers` are both BNPL accounts **and** the nodes of the
account-linkage graph; `account_links` are its edges. Everything else hangs off
`customers` and `merchants`.

```
merchants ──< plans >── customers ──< account_links >── customers
                 │
                 └──< installments
```

Row counts in the shipped dump: merchants **56**, customers **3,000**
(28 confirmed fraud), plans **6,462**, installments **33,574**,
account_links **928 rows = 464 undirected edges** (each edge stored both ways).
Calendar: signups/orders span **2025-01-01 → 2026-06-15**; treat **2026-06-22**
as "today" for anything overdue.

---

## `merchants`
| column | type | notes |
|---|---|---|
| `merchant_id` | int PK | |
| `name` | text | display name |
| `category` | text | Fashion, Electronics, Travel, Home, Beauty, Fitness, Grocery |
| `region` | text | NA / EU / APAC / LATAM |
| `mdr_bps` | int | merchant discount rate (Clarity's revenue per order), basis points |
| `onboarded_at` | date | |

## `customers`  (graph nodes)
| column | type | notes |
|---|---|---|
| `customer_id` | int PK | |
| `signup_at` | date | account creation |
| `region` | text | NA / EU / APAC / LATAM |
| `risk_band` | char | A (best) … E (worst) |
| `credit_limit_usd` | numeric | |
| `status` | text | `active` / `defaulted` |
| `is_confirmed_fraud` | bool | seeds for the fraud-graph questions |

## `plans`  (one BNPL order)
| column | type | notes |
|---|---|---|
| `plan_id` | int PK | |
| `customer_id` | int FK | |
| `merchant_id` | int FK | |
| `product_type` | text | `pay_in_4`, `pay_in_3`, `pay_monthly_6`, `pay_monthly_12` |
| `num_installments` | int | 4 / 3 / 6 / 12 |
| `order_amount_usd` | numeric | principal |
| `total_repayable_usd` | numeric | principal + interest (= principal when `apr_bps` = 0) |
| `apr_bps` | int | 0 for the pay-in-N products |
| `created_at` | date | order date |
| `status` | text | `active` / `paid_off` / `delinquent` / `defaulted` |

## `installments`  (repayment ledger)
| column | type | notes |
|---|---|---|
| `installment_id` | int PK | |
| `plan_id` | int FK | |
| `installment_no` | int | 1 … `num_installments` |
| `due_date` | date | |
| `amount_due_usd` | numeric | |
| `paid_date` | date NULL | NULL = not yet paid |
| `paid_amount_usd` | numeric NULL | NULL = not yet paid |
| `late_fee_usd` | numeric | charged on late/missed/written_off |
| `status` | text | `scheduled` (future), `paid`, `late`, `missed`, `written_off` |

## `account_links`  (graph edges, **both directions stored**)
| column | type | notes |
|---|---|---|
| `link_id` | int PK | |
| `src_customer_id` | int FK | |
| `dst_customer_id` | int FK | |
| `link_type` | text | `shared_device`, `shared_card`, `shared_bank`, `shared_phone`, `shared_address`, `shared_email_domain` |
| `link_distance` | numeric | **lower = stronger link.** device 1, card 2, bank 3, phone 5, address 8, email_domain 20 |
| `detected_at` | date | |

> **Reading the graph.** A *least-cost path* between two accounts is the chain of
> shared signals with the smallest summed `link_distance` — i.e. the **strongest
> chain of evidence** connecting them. Because both directions are stored, you can
> traverse edges without worrying about which way they point.

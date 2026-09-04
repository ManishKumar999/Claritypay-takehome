-- A1: Plan amortization and running balance.
-- Schedule order, using settlement information as of 2026-06-22; this is
-- not a reconstruction of the historical balance on each due date.
-- An installment is settled only when paid by the reporting date in full.
-- Sum contractual amount_due_usd, not cash receipts; exclude late fees.
-- Partial/unpaid installments contribute zero. Retain future installments.
-- For a complete, fully settled schedule only, normalize the final residual
-- to zero when within $0.06 (the observed per-plan rounding discrepancy).
-- Keep running_paid unadjusted and leave larger discrepancies visible.
WITH settlement AS (
    SELECT
        i.*,
        p.total_repayable_usd,
        p.num_installments,
        COALESCE(
            i.paid_date <= DATE '2026-06-22'
            AND i.paid_amount_usd >= i.amount_due_usd,
            FALSE
        ) AS is_settled
    FROM installments i
    JOIN plans p ON p.plan_id = i.plan_id
),
running AS (
    SELECT
        settlement.*,
        SUM(CASE WHEN is_settled THEN amount_due_usd ELSE 0 END)
            OVER (
                PARTITION BY plan_id
                ORDER BY installment_no, installment_id
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS running_paid,
        ROW_NUMBER() OVER (
            PARTITION BY plan_id
            ORDER BY installment_no DESC, installment_id DESC
        ) AS reverse_row_no,
        COUNT(*) OVER (PARTITION BY plan_id) AS actual_installments,
        SUM(CASE WHEN is_settled THEN 0 ELSE 1 END)
            OVER (PARTITION BY plan_id) AS unsettled_installments
    FROM settlement
)
SELECT
    plan_id,
    installment_no,
    due_date,
    amount_due_usd,
    running_paid,
    CASE
        WHEN reverse_row_no = 1
            AND actual_installments = num_installments
            AND unsettled_installments = 0
            AND ABS(total_repayable_usd - running_paid) <= 0.06
        THEN 0::numeric
        ELSE total_repayable_usd - running_paid
    END AS outstanding_balance
FROM running
ORDER BY plan_id, installment_no, installment_id;

-- A2: Merchant delinquency ranking by category.
-- Use ledger statuses exactly as specified: late counts even if later paid.
-- Exclude merchants with no due installments because their rate is undefined.
-- Keep all merchants in the worst three distinct rates, including ties.
-- RANK would leave gaps after ties, while ROW_NUMBER would assign unique
-- positions and require a tie-breaker to choose exactly three merchants.
WITH merchant_counts AS (
    SELECT
        m.category,
        m.merchant_id,
        m.name,
        COUNT(*) FILTER (
            WHERE i.status <> 'scheduled'
        ) AS due_installments,
        COUNT(*) FILTER (
            WHERE i.status IN ('missed', 'written_off', 'late')
        ) AS delinquent_installments
    FROM merchants m
    JOIN plans p ON p.merchant_id = m.merchant_id
    JOIN installments i ON i.plan_id = p.plan_id
    GROUP BY m.category, m.merchant_id, m.name
),
merchant_rates AS (
    SELECT
        category,
        merchant_id,
        name,
        due_installments,
        delinquent_installments::numeric
            / NULLIF(due_installments, 0) AS delinquency_rate
    FROM merchant_counts
    WHERE due_installments > 0
),
ranked_merchants AS (
    SELECT
        merchant_rates.*,
        DENSE_RANK() OVER (
            PARTITION BY category
            ORDER BY delinquency_rate DESC
        ) AS rank_in_category
    FROM merchant_rates
)
SELECT
    category,
    merchant_id,
    name,
    due_installments,
    delinquency_rate,
    rank_in_category
FROM ranked_merchants
WHERE rank_in_category <= 3
ORDER BY category, rank_in_category, merchant_id;

-- A3: Collections momentum by calendar month.
-- Sum actual paid_amount_usd by paid_date, including late/partial payments;
-- do not add charged late fees separately or restrict by installment status.
-- Calendar spans each merchant's first plan month through 2026-06-22.
-- Merchants without plans have no collections history and are omitted.
-- Fill empty months with zero so LAG means the previous calendar month.
-- First-month growth and growth from zero are undefined (NULL).
-- June 2026 is a partial month through June 22, compared with full May.
WITH RECURSIVE merchant_months AS (
    -- Start at each merchant's first plan month.
    SELECT
        p.merchant_id,
        DATE_TRUNC('month', MIN(p.created_at))::date AS month
    FROM plans p
    WHERE p.created_at <= DATE '2026-06-22'
    GROUP BY p.merchant_id

    UNION ALL

    -- Advance one month at a time, stopping at June 2026.
    SELECT
        merchant_id,
        (month + INTERVAL '1 month')::date
    FROM merchant_months
    WHERE month < DATE '2026-06-01'
),
monthly_collections AS (
    SELECT
        p.merchant_id,
        DATE_TRUNC('month', i.paid_date)::date AS month,
        SUM(i.paid_amount_usd) AS collected_usd
    FROM plans p
    JOIN installments i ON i.plan_id = p.plan_id
    WHERE i.paid_date <= DATE '2026-06-22'
        AND i.paid_amount_usd IS NOT NULL
    GROUP BY p.merchant_id, DATE_TRUNC('month', i.paid_date)::date
),
monthly_history AS (
    SELECT
        m.merchant_id,
        m.month,
        COALESCE(c.collected_usd, 0::numeric) AS collected_usd
    FROM merchant_months m
    LEFT JOIN monthly_collections c
        ON c.merchant_id = m.merchant_id AND c.month = m.month
),
previous_month AS (
    SELECT
        monthly_history.*,
        LAG(collected_usd) OVER (
            PARTITION BY merchant_id ORDER BY month
        ) AS prev_month_collected
    FROM monthly_history
)
SELECT
    merchant_id,
    month,
    collected_usd,
    prev_month_collected,
    CASE
        WHEN prev_month_collected IS NULL OR prev_month_collected = 0
            THEN NULL
        ELSE ROUND(
            100.0 * (collected_usd - prev_month_collected)
                / prev_month_collected,
            2
        )
    END AS mom_pct_change
FROM previous_month
ORDER BY merchant_id, month;

-- A4: Customer segmentation using installment-count on-time rate.
-- Due means non-scheduled and due by 2026-06-22. On time requires full
-- payment on or before due_date; use payment fields rather than status alone.
-- Include every customer in the output, but only customers with due installments
-- enter NTILE. Others retain NULL rates and receive descriptive labels:
-- No loan originated (no plans) or No due installments (plans exist).
-- Break rate ties by total dollars due DESC, then customer_id for stability.
-- NTILE balances group sizes but may split equal rates between quartiles.
WITH customer_counts AS (
    SELECT
        c.customer_id,
        COUNT(DISTINCT p.plan_id) AS plans_count,
        COUNT(i.installment_id) AS due_installments,
        COALESCE(SUM(i.amount_due_usd), 0::numeric) AS total_due_usd,
        COUNT(i.installment_id) FILTER (
            WHERE i.paid_date <= i.due_date
                AND i.paid_amount_usd >= i.amount_due_usd
        ) AS on_time_installments
    FROM customers c
    LEFT JOIN plans p ON p.customer_id = c.customer_id
    LEFT JOIN installments i
        ON i.plan_id = p.plan_id
        AND i.due_date <= DATE '2026-06-22'
        AND i.status <> 'scheduled'
    GROUP BY c.customer_id
),
customer_rates AS (
    SELECT
        customer_id,
        plans_count,
        due_installments,
        total_due_usd,
        on_time_installments::numeric
            / NULLIF(due_installments, 0) AS on_time_rate
    FROM customer_counts
),
segmented AS (
    SELECT
        customer_rates.*,
        NTILE(4) OVER (
            ORDER BY on_time_rate DESC NULLS LAST,
                     total_due_usd DESC,
                     customer_id
        ) AS quartile_number
    FROM customer_rates
    WHERE due_installments > 0
)
SELECT
    r.customer_id,
    r.due_installments,
    r.on_time_rate,
    CASE
        WHEN r.plans_count = 0 THEN 'No loan originated'
        WHEN r.due_installments = 0 THEN 'No due installments'
        WHEN s.quartile_number = 1 THEN 'Q1 (best)'
        WHEN s.quartile_number = 2 THEN 'Q2'
        WHEN s.quartile_number = 3 THEN 'Q3'
        WHEN s.quartile_number = 4 THEN 'Q4 (worst)'
    END AS quartile
FROM customer_rates r
LEFT JOIN segmented s ON s.customer_id = r.customer_id
ORDER BY s.quartile_number NULLS LAST, r.on_time_rate DESC NULLS LAST,
         r.total_due_usd DESC, r.customer_id;

-- Introductory exploration; these queries only read the supplied data.
-- Assignment reporting date: 2026-06-22.

-- 1. How much data do we have?
SELECT 'merchants' AS table_name, COUNT(*) AS row_count FROM merchants
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'plans', COUNT(*) FROM plans
UNION ALL SELECT 'installments', COUNT(*) FROM installments
UNION ALL SELECT 'account_links', COUNT(*) FROM account_links;

-- 2. What kinds of merchants are represented?
SELECT category, COUNT(*) AS merchant_count
FROM merchants
GROUP BY category
ORDER BY merchant_count DESC, category;

-- 3. How are installments distributed across statuses?
-- Amount due is the contractual amount, not necessarily cash collected.
SELECT status, COUNT(*) AS installment_count,
       SUM(amount_due_usd) AS scheduled_amount_usd,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_installments
FROM installments
GROUP BY status
ORDER BY installment_count DESC;

-- 4. Inspect one plan and its customer/merchant relationship.
SELECT p.plan_id, p.customer_id, m.name AS merchant,
       p.product_type, p.total_repayable_usd,
       i.installment_no, i.due_date, i.amount_due_usd,
       i.paid_date, i.paid_amount_usd, i.status
FROM plans p
JOIN merchants m USING (merchant_id)
JOIN installments i USING (plan_id)
WHERE p.plan_id = (SELECT MIN(plan_id) FROM plans)
ORDER BY i.installment_no;

-- 5. Check date ranges before interpreting the ledger.
SELECT MIN(due_date) AS first_due_date, MAX(due_date) AS last_due_date,
       MIN(paid_date) AS first_payment_date, MAX(paid_date) AS last_payment_date,
       COUNT(*) FILTER (WHERE paid_date > DATE '2026-06-22') AS payments_after_as_of,
       COUNT(*) FILTER (WHERE status = 'scheduled' AND due_date <= DATE '2026-06-22')
           AS scheduled_but_due,
       COUNT(*) FILTER (WHERE status <> 'scheduled' AND due_date > DATE '2026-06-22')
           AS non_scheduled_future_due
FROM installments;

-- 6. Inspect direct links from the confirmed-fraud example account.
SELECT l.dst_customer_id AS linked_customer, l.link_type, l.link_distance,
       c.is_confirmed_fraud
FROM account_links l
JOIN customers c ON c.customer_id = l.dst_customer_id
WHERE l.src_customer_id = 700
ORDER BY l.link_distance, l.dst_customer_id;

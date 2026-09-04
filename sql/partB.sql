-- B1: Accounts reachable within four hops from account 700.
-- Each stored edge is one hop; link_distance is irrelevant for this question.
-- Links are already stored in both directions. Guard against cycles per path.
-- Exclude the starting account itself (the anchor has zero hops).
WITH RECURSIVE reachable AS (
    SELECT
        700 AS customer_id,
        0 AS hops,
        ARRAY[700] AS visited_path

    UNION ALL

    SELECT
        l.dst_customer_id AS customer_id,
        r.hops + 1 AS hops,
        r.visited_path || l.dst_customer_id AS visited_path
    FROM reachable r
    JOIN account_links l
        ON l.src_customer_id = r.customer_id
    WHERE r.hops < 4
        AND NOT (l.dst_customer_id = ANY(r.visited_path))
)
SELECT
    customer_id,
    MIN(hops) AS hops
FROM reachable
WHERE hops > 0
GROUP BY customer_id
ORDER BY hops, customer_id;

-- B2: Least-cost path from 700 to 2800.
-- All supplied distances are positive: an optimal route needs no repeated
-- accounts. Enumerate simple paths without an arbitrary hop cap, stopping
-- each branch when it reaches the target. Finite but potentially exponential
-- on large, dense graphs; appropriate for this small source component.
-- Resolve equal costs by fewer hops, then lexicographic account path.
WITH RECURSIVE paths AS (
    SELECT
        700 AS customer_id,
        ARRAY[700] AS path,
        0::numeric AS total_distance,
        0 AS hops

    UNION ALL

    SELECT
        l.dst_customer_id,
        p.path || l.dst_customer_id,
        p.total_distance + l.link_distance,
        p.hops + 1
    FROM paths p
    JOIN account_links l
        ON l.src_customer_id = p.customer_id
    WHERE NOT (l.dst_customer_id = ANY(p.path))
        AND p.customer_id <> 2800
)
SELECT
    path,
    total_distance,
    hops
FROM paths
WHERE customer_id = 2800
ORDER BY total_distance, hops, path
LIMIT 1;

-- B3: Fewest-hops path from 700 to 2800.
-- B2 may take more hops yet have a lower summed distance because several
-- strong signals can outweigh one weak direct link.
-- The fraud team should use B2 for strongest evidence under these weights,
-- with B3 describing connection proximity; neither alone proves fraud.
-- Resolve hop ties by total distance, then lexicographic account path.
WITH RECURSIVE paths AS (
    SELECT
        700 AS customer_id,
        ARRAY[700] AS path,
        0::numeric AS total_distance,
        0 AS hops

    UNION ALL

    SELECT
        l.dst_customer_id,
        p.path || l.dst_customer_id,
        p.total_distance + l.link_distance,
        p.hops + 1
    FROM paths p
    JOIN account_links l
        ON l.src_customer_id = p.customer_id
    WHERE NOT (l.dst_customer_id = ANY(p.path))
        AND p.customer_id <> 2800
)
SELECT
    path,
    total_distance,
    hops
FROM paths
WHERE customer_id = 2800
ORDER BY hops, total_distance, path
LIMIT 1;

-- B4: Single-source least-cost distances from account 700.
-- 8 other accounts have least-cost distance <= 5 (9 including source 700).
-- Exclude source 700 from output, consistent with B1.
-- Positive weights make simple-path enumeration sufficient for the optimum;
-- cycle prevention guarantees termination without an arbitrary hop limit.
-- This enumerates all simple routes and is suitable for this small component;
-- use a dedicated shortest-path algorithm for large, dense graphs.
WITH RECURSIVE paths AS (
    SELECT
        700 AS customer_id,
        ARRAY[700] AS path,
        0::numeric AS total_distance,
        0 AS hops

    UNION ALL

    SELECT
        l.dst_customer_id,
        p.path || l.dst_customer_id,
        p.total_distance + l.link_distance,
        p.hops + 1
    FROM paths p
    JOIN account_links l
        ON l.src_customer_id = p.customer_id
    WHERE NOT (l.dst_customer_id = ANY(p.path))
),
cheapest_paths AS (
    SELECT DISTINCT ON (customer_id)
        customer_id,
        total_distance,
        path,
        hops
    FROM paths
    WHERE customer_id <> 700
    ORDER BY customer_id, total_distance, hops, path
)
SELECT
    customer_id,
    total_distance,
    path,
    hops
FROM cheapest_paths
ORDER BY total_distance, customer_id;

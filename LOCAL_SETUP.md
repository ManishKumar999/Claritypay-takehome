# Local database setup

Run these commands from the `assignment` folder with Docker Desktop running.
PostgreSQL runs in Docker; no system PostgreSQL or Python installation is needed
for this exploration step.

## First setup on another machine

Copy `.env.example` to `.env` and replace the placeholder with a local password.
The `.env` file is excluded from Git. Then start the database:

```sh
docker compose up -d --wait
```

Load the supplied dataset into this dedicated database:

```sh
docker compose exec -T -w /assignment-data db psql -X -v ON_ERROR_STOP=1 -U claritypay -d claritypay -f schema.sql
```

The original `schema.sql` drops and recreates the assignment tables. Run it for
initial loading or an intentional reset, not each time you start exploring.

## Explore

Run the saved introductory queries:

```sh
docker compose exec -T db psql -X -v ON_ERROR_STOP=1 -U claritypay -d claritypay < sql/explore.sql
```

Or open an interactive SQL terminal:

```sh
docker compose exec db psql -X -U claritypay -d claritypay
```

Enter SQL followed by a semicolon. Use `\dt` to list tables, `\d installments`
to inspect the installment columns, and `\q` to exit.

Example:

```sql
SELECT status, COUNT(*) AS installment_count
FROM installments
GROUP BY status
ORDER BY installment_count DESC;
```

## Connection details

- Host: `127.0.0.1`
- Port: `55432`
- Database: `claritypay`
- Username: `claritypay`
- Password: the value in your local `.env` file

The host port is bound only to the local machine. Database files persist in the
dedicated Docker volume `claritypay-takehome_claritypay_data`.

Stop and resume without reloading:

```sh
docker compose stop
docker compose start
```

## Verified initial exploration

All six exploration queries executed successfully on PostgreSQL 16.
Loaded counts: 56 merchants, 3,000 customers, 6,462 plans, 33,574 installments,
and 928 directed account-link rows.

Always use the assignment's reporting date, **2026-06-22**.
The first plan illustrates a rounding discrepancy: its four installments of
$81.72 total $326.88 versus the plan's $326.86 total repayable. The eventual
amortization analysis needs an explicit rounding policy.

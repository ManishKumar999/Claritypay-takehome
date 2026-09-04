"""Load Part A and Part B SQL results into pandas DataFrames.

Run from the repository root:
    .venv/bin/python python/data_access.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import psycopg


REPO_ROOT = Path(__file__).resolve().parents[1]
SQL_RESULT_NAMES = {
    "partA.sql": ["a1", "a2", "a3", "a4"],
    "partB.sql": ["b1", "b2", "b3", "b4"],
}


def load_local_env(path: Path = REPO_ROOT / ".env") -> None:
    """Load simple KEY=VALUE settings without overwriting shell variables."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def connection_settings() -> dict[str, object]:
    """Return local defaults, allowing every setting to be overridden."""
    load_local_env()
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("POSTGRES_PASSWORD is missing; set it in .env or the shell")

    return {
        "host": os.getenv("PGHOST", "127.0.0.1"),
        "port": int(os.getenv("PGPORT", "55432")),
        "dbname": os.getenv("PGDATABASE", "claritypay"),
        "user": os.getenv("PGUSER", "claritypay"),
        "password": password,
    }


def cursor_to_dataframe(cursor: psycopg.Cursor) -> pd.DataFrame:
    """Convert the cursor's current result set to a DataFrame."""
    columns = [column.name for column in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=columns)


def load_sql_results(
    connection: psycopg.Connection,
    sql_path: Path,
    result_names: list[str],
) -> dict[str, pd.DataFrame]:
    """Execute one SQL file and load each SELECT result in statement order."""
    sql = sql_path.read_text(encoding="utf-8")
    frames: dict[str, pd.DataFrame] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql)
        for name in result_names:
            if cursor.description is None:
                raise RuntimeError(f"{sql_path.name}: result {name} has no columns")
            frames[name] = cursor_to_dataframe(cursor)
            if name != result_names[-1] and not cursor.nextset():
                raise RuntimeError(f"{sql_path.name}: expected more result sets after {name}")

    return frames


def load_all_results() -> dict[str, pd.DataFrame]:
    """Load A1-A4 and B1-B4 into eight named DataFrames."""
    frames: dict[str, pd.DataFrame] = {}
    with psycopg.connect(**connection_settings()) as connection:
        for filename, names in SQL_RESULT_NAMES.items():
            frames.update(
                load_sql_results(connection, REPO_ROOT / "sql" / filename, names)
            )
    return frames


def main() -> None:
    frames = load_all_results()
    for name, frame in frames.items():
        print(f"\n{name.upper()}: {len(frame):,} rows x {len(frame.columns)} columns")
        print(frame.head(3).to_string(index=False))


if __name__ == "__main__":
    main()

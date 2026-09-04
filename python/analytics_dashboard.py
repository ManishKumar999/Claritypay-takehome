"""Create the two required C3 Plotly figures and a combined HTML dashboard.

Run from the repository root:
    .venv/bin/python python/analytics_dashboard.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from data_access import REPO_ROOT, load_all_results


FIGURES_DIR = REPO_ROOT / "figures"


def collections_figure(a3: pd.DataFrame) -> go.Figure:
    """Show portfolio monthly collections and cumulative collections."""
    history = a3.copy()
    history["month"] = pd.to_datetime(history["month"])
    history["collected_usd"] = pd.to_numeric(history["collected_usd"])
    portfolio = (
        history.groupby("month", as_index=False)["collected_usd"]
        .sum()
        .sort_values("month")
    )
    portfolio["running_collected_usd"] = portfolio["collected_usd"].cumsum()

    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(
        go.Bar(
            x=portfolio["month"],
            y=portfolio["collected_usd"],
            name="Monthly collections",
            marker_color="#3b82f6",
            hovertemplate=(
                "Month: %{x|%B %Y}<br>"
                "Collected: $%{y:,.2f}<extra></extra>"
            ),
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=portfolio["month"],
            y=portfolio["running_collected_usd"],
            name="Cumulative collections",
            mode="lines+markers",
            line={"color": "#f59e0b", "width": 3},
            hovertemplate=(
                "Through: %{x|%B %Y}<br>"
                "Cumulative collected: $%{y:,.2f}<extra></extra>"
            ),
        ),
        secondary_y=True,
    )
    figure.update_layout(
        title=(
            "Portfolio collections by payment month"
            "<br><sup>Bars show actual payments received; line shows the running total. "
            "June 2026 is partial through June 22.</sup>"
        ),
        xaxis_title="Payment month",
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.12, "x": 0},
        margin={"l": 70, "r": 70, "t": 110, "b": 60},
        template="plotly_white",
    )
    figure.update_yaxes(title_text="Monthly collections (USD)", tickprefix="$", secondary_y=False)
    figure.update_yaxes(title_text="Cumulative collections (USD)", tickprefix="$", secondary_y=True)
    return figure


def delinquency_figure(a2: pd.DataFrame) -> go.Figure:
    """Show the three worst distinct delinquency ranks per category."""
    ranking = a2.copy()
    ranking["delinquency_rate"] = pd.to_numeric(ranking["delinquency_rate"])
    ranking["delinquent_installments"] = (
        ranking["delinquency_rate"] * ranking["due_installments"]
    ).round().astype(int)
    ranking["bar_label"] = (
        ranking["delinquency_rate"].map(lambda value: f"{value:.1%}")
        + " · "
        + ranking["delinquent_installments"].astype(str)
        + "/"
        + ranking["due_installments"].astype(str)
    )
    ranking["label"] = ranking["category"] + " · " + ranking["name"]
    ranking = ranking.sort_values(
        ["delinquency_rate", "category", "merchant_id"], ascending=[True, True, True]
    )

    figure = px.bar(
        ranking,
        x="delinquency_rate",
        y="label",
        color="category",
        text="bar_label",
        orientation="h",
        custom_data=[
            "merchant_id",
            "category",
            "due_installments",
            "rank_in_category",
            "delinquent_installments",
        ],
        labels={
            "delinquency_rate": "Delinquency rate: delinquent installments ÷ due installments",
            "label": "Category and merchant",
            "category": "Category",
        },
        title=(
            "Worst merchant delinquency rates within each category"
            "<br><sup>Delinquency rate = (late + missed + written-off) ÷ all due "
            "installments. Labels show rate · delinquent/due counts.</sup>"
        ),
        template="plotly_white",
    )
    figure.update_traces(
        hovertemplate=(
            "Merchant: %{y}<br>Merchant ID: %{customdata[0]}<br>"
            "Category: %{customdata[1]}<br>Due installments: %{customdata[2]:,}<br>"
            "Delinquent installments: %{customdata[4]:,}<br>"
            "Delinquency rate: %{x:.2%}<br>Category rank: %{customdata[3]}"
            "<extra></extra>"
        )
    )
    figure.update_traces(textposition="outside", cliponaxis=False)
    figure.update_layout(
        xaxis={"tickformat": ".0%", "range": [0, ranking["delinquency_rate"].max() * 1.15]},
        yaxis={"categoryorder": "array", "categoryarray": ranking["label"].tolist()},
        legend={"title_text": "Merchant category"},
        height=760,
        margin={"l": 170, "r": 40, "t": 100, "b": 60},
    )
    return figure


def write_dashboard(collections: go.Figure, delinquency: go.Figure, output: Path) -> None:
    """Write both figures into one portable HTML page."""
    first = pio.to_html(collections, full_html=False, include_plotlyjs="cdn")
    second = pio.to_html(delinquency, full_html=False, include_plotlyjs=False)
    output.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Clarity Pay analytics dashboard</title>"
        "<style>body{font-family:Arial,sans-serif;margin:24px;max-width:1400px}"
        "section{margin-bottom:48px}</style></head><body>"
        f"<section>{first}</section><section>{second}</section></body></html>",
        encoding="utf-8",
    )


def main() -> None:
    results = load_all_results()
    collections = collections_figure(results["a3"])
    delinquency = delinquency_figure(results["a2"])

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    collections.write_html(FIGURES_DIR / "collections.html", include_plotlyjs="cdn")
    delinquency.write_html(FIGURES_DIR / "delinquency.html", include_plotlyjs="cdn")
    write_dashboard(collections, delinquency, FIGURES_DIR / "dashboard.html")
    print(f"Saved collections chart: {(FIGURES_DIR / 'collections.html').resolve()}")
    print(f"Saved delinquency chart: {(FIGURES_DIR / 'delinquency.html').resolve()}")
    print(f"Saved combined dashboard: {(FIGURES_DIR / 'dashboard.html').resolve()}")


if __name__ == "__main__":
    main()

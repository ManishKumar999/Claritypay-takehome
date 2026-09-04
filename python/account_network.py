"""Render a parameterized account-link neighborhood and least-cost path.

Run from the repository root:
    .venv/bin/python python/account_network.py --source 700 --target 2800
"""

from __future__ import annotations

import argparse
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import psycopg

from data_access import REPO_ROOT, connection_settings


FIGURES_DIR = REPO_ROOT / "figures"


def load_graph_data(connection: psycopg.Connection) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load graph nodes and one row per undirected account link."""
    nodes_sql = """
        SELECT customer_id, risk_band, status, is_confirmed_fraud
        FROM customers
    """
    edges_sql = """
        SELECT DISTINCT ON (
            LEAST(src_customer_id, dst_customer_id),
            GREATEST(src_customer_id, dst_customer_id)
        )
            LEAST(src_customer_id, dst_customer_id) AS source,
            GREATEST(src_customer_id, dst_customer_id) AS target,
            link_type,
            link_distance
        FROM account_links
        ORDER BY
            LEAST(src_customer_id, dst_customer_id),
            GREATEST(src_customer_id, dst_customer_id),
            link_distance,
            link_type
    """

    with connection.cursor() as cursor:
        cursor.execute(nodes_sql)
        nodes = pd.DataFrame(
            cursor.fetchall(), columns=[column.name for column in cursor.description]
        )
        cursor.execute(edges_sql)
        edges = pd.DataFrame(
            cursor.fetchall(), columns=[column.name for column in cursor.description]
        )
    return nodes, edges


def build_graph(nodes: pd.DataFrame, edges: pd.DataFrame) -> nx.Graph:
    """Build an undirected NetworkX graph with node and edge attributes."""
    graph = nx.Graph()
    for row in nodes.itertuples(index=False):
        graph.add_node(
            row.customer_id,
            risk_band=row.risk_band,
            status=row.status,
            is_confirmed_fraud=row.is_confirmed_fraud,
        )
    for row in edges.itertuples(index=False):
        graph.add_edge(
            row.source,
            row.target,
            link_type=row.link_type,
            link_distance=float(row.link_distance),
        )
    return graph


def edge_trace(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    width: float,
    color: str,
    label: str,
) -> go.Scatter:
    """Create one hoverable line trace."""
    return go.Scatter(
        x=[x0, x1],
        y=[y0, y1],
        mode="lines",
        line={"width": width, "color": color},
        hovertemplate=label + "<extra></extra>",
        showlegend=False,
    )


def create_figure(graph: nx.Graph, source: int, target: int) -> tuple[go.Figure, list[int]]:
    """Render source's connected component with the least-cost path highlighted."""
    if source not in graph or target not in graph:
        raise ValueError("Source and target must both be customer IDs in the graph")

    neighborhood = graph.subgraph(nx.node_connected_component(graph, source)).copy()
    if target not in neighborhood:
        raise nx.NetworkXNoPath(f"No path exists from {source} to {target}")

    cheapest_path = nx.shortest_path(
        neighborhood, source=source, target=target, weight="link_distance"
    )
    path_edges = {
        frozenset((left, right))
        for left, right in zip(cheapest_path, cheapest_path[1:])
    }
    positions = nx.spring_layout(neighborhood, seed=42, weight="link_distance")

    figure = go.Figure()
    for left, right, attrs in neighborhood.edges(data=True):
        x0, y0 = positions[left]
        x1, y1 = positions[right]
        on_path = frozenset((left, right)) in path_edges
        distance = attrs["link_distance"]
        figure.add_trace(
            edge_trace(
                x0,
                y0,
                x1,
                y1,
                width=6 if on_path else 1.5 + 4 / distance,
                color="#ff8c00" if on_path else "#9aa4b2",
                label=(
                    f"{left} ↔ {right}<br>{attrs['link_type']}"
                    f"<br>Distance: {distance:g}"
                    f"<br>{'Least-cost path' if on_path else 'Other link'}"
                ),
            )
        )

    node_x, node_y, node_text, node_hover, node_color, node_symbol, node_size = (
        [], [], [], [], [], [], []
    )
    for node, attrs in neighborhood.nodes(data=True):
        x, y = positions[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(str(node))
        node_hover.append(
            f"Customer {node}<br>Risk band: {attrs['risk_band']}"
            f"<br>Status: {attrs['status']}"
            f"<br>Confirmed fraud: {attrs['is_confirmed_fraud']}"
        )
        node_color.append("#d62728" if attrs["is_confirmed_fraud"] else "#3b82f6")
        node_symbol.append("star" if node == source else "diamond" if node == target else "circle")
        node_size.append(25 if node in (source, target) else 18)

    figure.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_text,
            textposition="top center",
            hovertext=node_hover,
            hovertemplate="%{hovertext}<extra></extra>",
            marker={
                "size": node_size,
                "color": node_color,
                "symbol": node_symbol,
                "line": {"width": 1.5, "color": "white"},
            },
            showlegend=False,
        )
    )

    total_distance = nx.path_weight(neighborhood, cheapest_path, "link_distance")
    figure.update_layout(
        title=(
            f"Account-link neighborhood: {source} → {target}"
            f"<br><sup>Least-cost path: {' → '.join(map(str, cheapest_path))}; "
            f"distance {total_distance:g}, {len(cheapest_path) - 1} hops</sup>"
        ),
        hovermode="closest",
        margin={"l": 20, "r": 20, "t": 90, "b": 45},
        xaxis={"visible": False},
        yaxis={"visible": False},
        plot_bgcolor="white",
        annotations=[
            {
                "text": (
                    "Orange = least-cost path · Red = confirmed fraud · "
                    "Star = source · Diamond = target · thicker grey = stronger link"
                ),
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": -0.08,
                "showarrow": False,
            }
        ],
    )
    return figure, cheapest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=int, default=700)
    parser.add_argument("--target", type=int, default=2800)
    parser.add_argument(
        "--output", type=Path, default=FIGURES_DIR / "account_network.html"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with psycopg.connect(**connection_settings()) as connection:
        nodes, edges = load_graph_data(connection)
    graph = build_graph(nodes, edges)
    figure, path = create_figure(graph, args.source, args.target)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(args.output, include_plotlyjs="cdn")
    print(f"Least-cost path: {' -> '.join(map(str, path))}")
    print(f"Saved interactive graph to {args.output.resolve()}")


if __name__ == "__main__":
    main()

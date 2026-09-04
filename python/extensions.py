"""Generate the two additional C4 extensions.

Outputs:
  figures/interactive_account_network.html
  figures/cohort_repayment.html
"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.express as px
import psycopg

from account_network import build_graph, load_graph_data
from data_access import REPO_ROOT, connection_settings


FIGURES_DIR = REPO_ROOT / "figures"
AS_OF_DATE = "2026-06-22"


def write_interactive_network(
    graph: nx.Graph, output: Path, initial_source: int = 700, initial_target: int = 2800
) -> None:
    """Write a browser control that recalculates highlighted endpoint paths."""
    component = graph.subgraph(nx.node_connected_component(graph, initial_source)).copy()
    positions = nx.spring_layout(component, seed=42, weight=None)
    nodes = []
    for node, attrs in component.nodes(data=True):
        x, y = positions[node]
        nodes.append(
            {
                "id": node,
                "x": round(float(x), 6),
                "y": round(float(y), 6),
                "risk": attrs["risk_band"],
                "status": attrs["status"],
                "fraud": bool(attrs["is_confirmed_fraud"]),
            }
        )
    edges = [
        {
            "a": left,
            "b": right,
            "type": attrs["link_type"],
            "distance": attrs["link_distance"],
        }
        for left, right, attrs in component.edges(data=True)
    ]
    paths: dict[str, dict[str, object]] = {}
    for source in component.nodes:
        for target in component.nodes:
            if source == target:
                continue
            path = nx.shortest_path(component, source, target, weight="link_distance")
            paths[f"{source}-{target}"] = {
                "path": path,
                "distance": nx.path_weight(component, path, "link_distance"),
            }

    payload = json.dumps({"nodes": nodes, "edges": edges, "paths": paths})
    options = "".join(f"<option value='{node}'>{node}</option>" for node in sorted(component.nodes))
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Interactive account-link explorer</title>
<script src="https://cdn.plot.ly/plotly-3.3.1.min.js"></script>
<style>body{{font-family:Arial,sans-serif;margin:24px;max-width:1200px}}label{{margin-right:18px}}
select{{font-size:16px;padding:5px}}#summary{{margin:14px 0;font-weight:600}}#graph{{height:680px}}</style></head>
<body><h1>Interactive account-link explorer</h1>
<p>Select any two accounts in account 700's connected component. The orange route is the least-cost path.</p>
<label>Source <select id="source">{options}</select></label>
<label>Target <select id="target">{options}</select></label>
<div id="summary"></div><div id="graph"></div>
<script>const DATA={payload};
const pos=Object.fromEntries(DATA.nodes.map(n=>[n.id,n]));
const source=document.getElementById('source'),target=document.getElementById('target');
source.value='{initial_source}';target.value='{initial_target}';
function draw(){{
 const s=Number(source.value),t=Number(target.value),key=`${{s}}-${{t}}`;
 if(s===t){{document.getElementById('summary').textContent='Choose two different accounts.';return;}}
 const selected=DATA.paths[key], pairs=new Set(selected.path.slice(1).map((v,i)=>
   [selected.path[i],v].sort((a,b)=>a-b).join('-')));
 const traces=DATA.edges.map(e=>{{const active=pairs.has([e.a,e.b].sort((a,b)=>a-b).join('-'));
  return {{x:[pos[e.a].x,pos[e.b].x],y:[pos[e.a].y,pos[e.b].y],mode:'lines',showlegend:false,
   line:{{color:active?'#f59e0b':'#9aa4b2',width:active?7:1.5+4/e.distance}},
   text:`${{e.a}} ↔ ${{e.b}}<br>${{e.type}}<br>Distance: ${{e.distance}}`,hoverinfo:'text'}};}});
 traces.push({{x:DATA.nodes.map(n=>n.x),y:DATA.nodes.map(n=>n.y),mode:'markers+text',
  text:DATA.nodes.map(n=>String(n.id)),textposition:'top center',showlegend:false,
  marker:{{size:DATA.nodes.map(n=>n.id===s||n.id===t?25:18),
   color:DATA.nodes.map(n=>n.fraud?'#d62728':'#3b82f6'),
   symbol:DATA.nodes.map(n=>n.id===s?'star':n.id===t?'diamond':'circle')}},
  hovertext:DATA.nodes.map(n=>`Customer ${{n.id}}<br>Risk: ${{n.risk}}<br>Status: ${{n.status}}<br>Fraud: ${{n.fraud}}`),hoverinfo:'text'}});
 Plotly.react('graph',traces,{{title:`Least-cost path: ${{selected.path.join(' → ')}}`,
  xaxis:{{visible:false}},yaxis:{{visible:false}},hovermode:'closest',plot_bgcolor:'white',margin:{{t:70,l:20,r:20,b:20}}}},{{responsive:true}});
 document.getElementById('summary').textContent=`Total distance ${{selected.distance}} · ${{selected.path.length-1}} hops`;
}}
source.addEventListener('change',draw);target.addEventListener('change',draw);draw();</script></body></html>"""
    output.write_text(html, encoding="utf-8")


def load_cohort_data(connection: psycopg.Connection) -> pd.DataFrame:
    """Calculate count-weighted on-time rates by signup cohort and age month."""
    sql = """
        SELECT
            DATE_TRUNC('quarter', c.signup_at)::date AS signup_cohort,
            (
                EXTRACT(YEAR FROM AGE(i.due_date, c.signup_at))::int * 12
                + EXTRACT(MONTH FROM AGE(i.due_date, c.signup_at))::int
            ) AS months_since_signup,
            COUNT(*) AS due_installments,
            COUNT(*) FILTER (
                WHERE i.paid_date <= i.due_date
                  AND i.paid_amount_usd >= i.amount_due_usd
            ) AS on_time_installments
        FROM customers c
        JOIN plans p ON p.customer_id = c.customer_id
        JOIN installments i ON i.plan_id = p.plan_id
        WHERE i.due_date <= %(as_of)s::date
          AND i.status <> 'scheduled'
        GROUP BY 1, 2
        ORDER BY 1, 2
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, {"as_of": AS_OF_DATE})
        return pd.DataFrame(
            cursor.fetchall(), columns=[column.name for column in cursor.description]
        )


def cohort_figure(data: pd.DataFrame):
    history = data.copy()
    history["signup_cohort"] = pd.to_datetime(history["signup_cohort"]).dt.strftime("%Y Q%q")
    # pandas has no quarter directive; create the display label explicitly.
    dates = pd.to_datetime(data["signup_cohort"])
    history["signup_cohort"] = dates.dt.year.astype(str) + " Q" + dates.dt.quarter.astype(str)
    history["on_time_rate"] = (
        history["on_time_installments"] / history["due_installments"]
    )
    figure = px.line(
        history,
        x="months_since_signup",
        y="on_time_rate",
        color="signup_cohort",
        markers=True,
        custom_data=["due_installments", "on_time_installments"],
        labels={
            "months_since_signup": "Months since customer signup",
            "on_time_rate": "On-time installment rate",
            "signup_cohort": "Signup cohort",
        },
        title=(
            "On-time repayment by signup cohort and account age"
            "<br><sup>Rate = installments fully paid by due date ÷ installments due; "
            "data through June 22, 2026.</sup>"
        ),
        template="plotly_white",
    )
    figure.update_traces(
        hovertemplate=(
            "Cohort: %{fullData.name}<br>Months since signup: %{x}<br>"
            "On-time rate: %{y:.1%}<br>On time / due: %{customdata[1]:,} / %{customdata[0]:,}"
            "<extra></extra>"
        )
    )
    figure.update_yaxes(tickformat=".0%", range=[0, 1])
    figure.update_layout(hovermode="x unified", margin={"t": 100})
    return figure


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(**connection_settings()) as connection:
        nodes, edges = load_graph_data(connection)
        cohort_data = load_cohort_data(connection)
    write_interactive_network(
        build_graph(nodes, edges), FIGURES_DIR / "interactive_account_network.html"
    )
    cohort_figure(cohort_data).write_html(
        FIGURES_DIR / "cohort_repayment.html", include_plotlyjs="cdn"
    )
    print(f"Saved interactive network: {(FIGURES_DIR / 'interactive_account_network.html').resolve()}")
    print(f"Saved cohort curve: {(FIGURES_DIR / 'cohort_repayment.html').resolve()}")


if __name__ == "__main__":
    main()

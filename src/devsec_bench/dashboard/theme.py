"""Restrained theme tokens and reusable presentation primitives."""

import html
from typing import Any

import plotly.graph_objects as go
import streamlit as st

COLORS = {
    "background": "#0B0F17",
    "surface": "#161E2D",
    "border": "#2A3546",
    "text": "#F1F5F9",
    "muted": "#94A3B8",
    "blue": "#3B82F6",
    "green": "#10B981",
    "amber": "#F59E0B",
    "red": "#EF4444",
}
STATUS_COLORS = {
    "Passed": "green",
    "Policy violation": "red",
    "Execution error": "red",
    "Timed out": "amber",
    "Budget exhausted": "amber",
    "Interrupted": "amber",
    "Evaluation failed": "red",
}

CSS = """
<style>
.stApp {background:#0B0F17;color:#F1F5F9}
[data-testid=stSidebar] {background:#111827;border-right:1px solid #2A3546}
.block-container {padding:4rem 2.2rem 3rem;max-width:1600px}
h1 {font-size:2rem!important;font-weight:650!important;letter-spacing:-.035em}
h2,h3 {letter-spacing:-.02em}
[data-testid=stCaptionContainer] {color:#94A3B8}
[data-testid=stMetric] {background:#161E2D;border:1px solid #2A3546;border-radius:9px;padding:1.1rem;min-height:115px}
[data-testid=stMetricLabel] {color:#94A3B8;font-size:.8rem}
[data-testid=stMetricValue] {font-size:1.85rem;font-weight:600;letter-spacing:-.03em;color:#F1F5F9}
[data-testid=stVerticalBlockBorderWrapper] > div {border-color:#2A3546!important;border-radius:9px}
[data-testid=stDataFrame] {border:1px solid #2A3546;border-radius:8px}
[data-testid=stSidebar] label:has(input:checked) {background:#1E293B;border-radius:6px}
.brand {display:flex;align-items:center;gap:12px;margin:0 0 22px}
.brand-mark {background:#1D4ED8;color:white;font-weight:750;font-size:14px;padding:10px;border-radius:7px;letter-spacing:-.5px}
.brand-name {font-size:15px;font-weight:650;line-height:1.35}
.brand-subtitle,.eyebrow {font-size:10px;color:#94A3B8;letter-spacing:.13em;text-transform:uppercase}
.eyebrow {margin-bottom:8px}
.status {display:inline-block;padding:4px 9px;border:1px solid #2A3546;border-radius:5px;font-size:11px;font-weight:600}
.mono {font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12px;color:#94A3B8}
@media(max-width:900px){.block-container{padding:4rem 1rem 2rem}h1{font-size:1.65rem!important}
div[data-testid=stHorizontalBlock]:has(div[data-testid=stPopover]){flex-wrap:wrap}
div[data-testid=stColumn]:has(div[data-testid=stPopover]){min-width:160px;flex:1 1 160px}
div[data-testid=stHorizontalBlock]:has(div[data-testid=stMetric]){flex-wrap:wrap}
div[data-testid=stColumn]:has(div[data-testid=stMetric]){min-width:160px;flex:1 1 160px}}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def status_badge(label: str) -> None:
    color = COLORS[STATUS_COLORS.get(label, "muted")]
    st.markdown(
        f'<span class="status" style="color:{color}">{html.escape(label)}</span>',
        unsafe_allow_html=True,
    )


def chart(figure: go.Figure, height: int = 280) -> None:
    figure.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, system-ui, sans-serif", "color": COLORS["muted"], "size": 11},
        margin={"l": 10, "r": 10, "t": 20, "b": 15},
        height=height,
        legend={"orientation": "h", "y": -0.22, "title": {"text": ""}},
        hoverlabel={"bgcolor": "#1E293B", "font_color": COLORS["text"]},
        colorway=[COLORS["blue"], COLORS["green"], COLORS["amber"], COLORS["red"]],
    )
    figure.update_xaxes(gridcolor=COLORS["border"], zeroline=False, showgrid=False, automargin=True)
    figure.update_yaxes(gridcolor=COLORS["border"], zeroline=False, automargin=True)
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})


def value(number: Any, kind: str = "number") -> str:
    if number is None:
        return "Unavailable"
    if kind == "percent":
        return f"{number:.1%}"
    if kind == "seconds":
        return f"{number:.3f}s"
    if kind == "cost":
        return f"${number:.4f}"
    return str(number)

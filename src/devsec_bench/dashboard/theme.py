"""Small editorial design system using native accessible Streamlit controls."""

import html
from typing import Any

import plotly.graph_objects as go
import streamlit as st

COLORS = {
    "canvas": "#F7F6F2",
    "background": "#F7F6F2",
    "surface": "#FFFFFF",
    "secondary": "#F0EFEA",
    "border": "#DEDCD5",
    "control_border": "#85877F",
    "text": "#222321",
    "muted": "#686A65",
    "accent": "#8C3B32",
    "green": "#37654D",
    "amber": "#7B5A20",
    "red": "#8C3B32",
    "blue": "#8C3B32",
}
STATUS_COLORS = {
    "Passed": "green",
    "Policy violation": "red",
    "Execution error": "red",
    "Timed out": "amber",
    "Budget exhausted": "amber",
    "Interrupted": "amber",
    "Evaluation failed": "red",
    "Pending": "muted",
}
CSS = """
<style>
.stApp{background:#F7F6F2;color:#222321}
.block-container{max-width:1180px;padding:3.8rem 2rem 2rem}
h1{font-size:2rem!important;letter-spacing:-.035em;font-weight:650!important}
h2{font-size:1.45rem!important;letter-spacing:-.025em}
h3{font-size:1.1rem!important;letter-spacing:-.01em}
[data-testid=stCaptionContainer]{color:#686A65;opacity:1}
.wordmark{font-size:15px;letter-spacing:.08em;font-weight:700;border-left:3px solid #8C3B32;padding-left:12px}
.wordmark span{font-weight:400;letter-spacing:.025em;margin-left:7px}
.eyebrow{color:#686A65;font-size:11px;letter-spacing:.08em;text-transform:uppercase}
.mono{font-family:ui-monospace,"Source Code Pro",Consolas,monospace;font-size:12px}
.status{font-size:13px;font-weight:650}
[data-testid=stMarkdownContainer] hr{border-color:#DEDCD5;margin:12px 0}
button,input,[data-baseweb=select]>div{border-radius:2px!important;box-shadow:none!important}
button,[data-testid=stTextInputRootElement],[data-testid=stNumberInputContainer],.react-aria-ComboBox [role=group]{border-color:#85877F!important}
.react-aria-ComboBox [role=group]{border-radius:2px}
button{min-height:40px}
button:focus-visible,input:focus-visible,[role=radio]:focus-visible{outline:2px solid #8C3B32!important;outline-offset:3px}
[data-testid=stDataFrame],[data-testid=stExpander]{border-radius:2px;border-color:#DEDCD5}
[data-testid=stAlert]{border-radius:2px;background:#F0EFEA;color:#222321}
[data-testid=stMetric]{background:none;border:none;padding:0}
[data-testid=stMetricValue]{font-size:1.35rem}
@media(max-width:640px){.block-container{padding:3.6rem 1rem 1.5rem}h1{font-size:1.65rem!important}
button{min-height:44px}[data-testid=stRadio] label p{font-size:.85rem}}
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
        font={
            "family": "Source Sans Pro, system-ui, sans-serif",
            "color": COLORS["text"],
            "size": 12,
        },
        margin={"l": 12, "r": 12, "t": 20, "b": 15},
        height=height,
        colorway=[COLORS["accent"]],
        showlegend=False,
    )
    figure.update_xaxes(gridcolor=COLORS["border"], zerolinecolor=COLORS["muted"], automargin=True)
    figure.update_yaxes(gridcolor=COLORS["border"], automargin=True)
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

import plotly.express as px
from utils.helper import format_rp_short

def plot_pie_status(df_pie_chart, active_period_str):
    fig = px.pie(
        df_pie_chart,
        names="Status",
        title=f"Komposisi Status Karyawan ({active_period_str})",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return fig

def plot_top_roles(top_roles, active_period_str):
    fig = px.bar(
        top_roles,
        x="Jumlah",
        y="Posisi",
        orientation="h",
        title=f"Top 10 Posisi Terbanyak Karyawan Aktif ({active_period_str})",
        color="Jumlah",
        color_continuous_scale="Blues",
    )
    fig.update_traces(textangle=0)
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    return fig

def plot_manpower_trend(trend_month):
    fig = px.bar(
        trend_month,
        x="Month",
        y="Parsed_Payment",
        title="Total Payment Amount per Bulan",
        text="Text_Format",
        color="Month",
        color_discrete_sequence=["#1F4E79", "#2CA02C"],
    )
    fig.update_traces(
        textangle=0,
        textposition="outside",
        hovertemplate="<b>Bulan:</b> %{x}<br><b>Total Payment:</b> Rp %{y:,.0f}<extra></extra>",
    )
    fig.update_layout(
        xaxis_title="Bulan",
        yaxis_title="Total Payment (Rp)",
        showlegend=False,
        xaxis={"categoryorder": "array", "categoryarray": trend_month["Month"].tolist()},
    )
    return fig

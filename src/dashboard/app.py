from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

DATA = Path("data/processed/telemetry.parquet")

ACCENT = "#E6B450"


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_parquet(DATA)
    df["LapTime"] = pd.to_timedelta(df["LapTime"]).dt.total_seconds()
    return df


def style(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F1F5F9"),
    )
    return fig


def driver_color(driver: str) -> str:
    return ACCENT if driver == "VER" else "#48CAE4"


def metric_card(df: pd.DataFrame) -> None:
    fastest_row = df.loc[df["Speed"].idxmax()]
    cols = st.columns(4)
    cols[0].metric("Top Speed", f"{fastest_row['Speed']:.1f} km/h")
    cols[1].metric("Max RPM", f"{df['RPM'].max():,.0f}")
    cols[2].metric("Peak Throttle", f"{df['Throttle'].max():.0f}%")
    cols[3].metric("Max Brake", f"{df['Brake'].max():.0f}%")


def replay_chart(df: pd.DataFrame, t: float) -> go.Figure:
    lap = df[df["SessionTime"] <= t]
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("Speed (km/h)", "RPM", "Throttle / Brake (%)"),
        vertical_spacing=0.06,
    )
    fig.add_trace(go.Scatter(x=lap["SessionTime"], y=lap["Speed"], name="Speed", line=dict(color=ACCENT)), row=1, col=1)
    fig.add_trace(go.Scatter(x=lap["SessionTime"], y=lap["RPM"], name="RPM", line=dict(color="#F4A261")), row=2, col=1)
    fig.add_trace(go.Scatter(x=lap["SessionTime"], y=lap["Throttle"], name="Throttle", line=dict(color="#2A9D8F")), row=3, col=1)
    fig.add_trace(go.Scatter(x=lap["SessionTime"], y=lap["Brake"], name="Brake", line=dict(color="#E76F51")), row=3, col=1)
    fig.add_vline(x=t, line_dash="dash", line_color="white", row="all")
    return style(fig)


def track_map(df: pd.DataFrame, other: pd.DataFrame | None = None) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["X"], y=df["Y"], mode="markers",
        marker=dict(size=7, color=df["Speed"], colorscale="turbo", showscale=True,
                    cmin=df["Speed"].min(), cmax=df["Speed"].max(),
                    colorbar=dict(title="Speed", len=0.8)),
        name=df["Driver"].iloc[0],
    ))
    if other is not None:
        fig.add_trace(go.Scatter(
            x=other["X"], y=other["Y"], mode="lines",
            line=dict(width=1, color="white", dash="dot"),
            name=f"{other['Driver'].iloc[0]} (other lap)",
        ))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return style(fig)


def lap_delta(df: pd.DataFrame, other: pd.DataFrame) -> go.Figure:
    merged = df.merge(other, on="SessionTime", suffixes=("_A", "_B"))
    delta = merged["Speed_A"] - merged["Speed_B"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=merged["SessionTime"], y=delta, mode="lines",
        line=dict(color=ACCENT, width=2),
        fill="tozeroy",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="white")
    return style(fig)


def show_replay(df: pd.DataFrame) -> None:
    max_t = df["SessionTime"].max()
    t = st.slider("Playback", 0.0, float(max_t), float(max_t), step=0.1,
                  help="Scrub the lap timeline — the charts replay the run.")
    metric_card(df[df["SessionTime"] <= t])
    st.plotly_chart(replay_chart(df, t), use_container_width=True)


def show_comparison(df: pd.DataFrame, drivers: list[str]) -> None:
    cols = st.columns(2)
    d1 = cols[0].selectbox("Driver A", drivers, key="comp_driver_a")
    d2 = cols[1].selectbox("Driver B", drivers, key="comp_driver_b")

    base = df[df["Driver"] == d1].sort_values("LapTime").iloc[[0]]
    comp = df[df["Driver"] == d2].sort_values("LapTime").iloc[[0]]
    t1, t2 = float(base["LapTime"]), float(comp["LapTime"])
    diff = t1 - t2

    st.markdown(f"**Fastest lap {d1}:** {t1:.3f}s  |  **Fastest lap {d2}:** {t2:.3f}s")
    delta_c = diff if diff != 0 else abs(diff)
    st.metric("Time delta (A − B)", f"{diff:+.3f}s", delta=f"{delta_c:.3f}s", delta_color="normal")

    st.plotly_chart(lap_delta(base, comp), use_container_width=True)


def show_pipeline() -> None:
    st.subheader("How the telemetry reaches this page")
    st.markdown("""
| Stage | What it does | Tooling |
|---|---|---|
| **Fetch** | Pulls real F1 telemetry (speed, RPM, throttle, brake, gear, position) | FastF1 API |
| **Validate** | Sanity-checks the data before it is admitted | Python asserts |
| **Resample** | Aligns all channels onto a fixed 10 Hz grid; fills gaps, forward-fills gear | pandas |
| **Store** | Telemetry persisted as a Parquet dataset | pyarrow |
| **Present** | This dashboard replays laps, compares drivers, and maps the track | Streamlit |

**Automation story:** a driver runs → data is captured, cleaned, stored and visualised without manual spreadsheet work.
The same schema accepts the team's own CAN/sensor feed later — only the fetch stage changes.
""")


def main() -> None:
    st.set_page_config(page_title="ERT Telemetry Lab", page_icon="🏎️", layout="wide")
    footer = st.sidebar.markdown("<div style='position:fixed;bottom:1rem'>Built for ENP Racing Team</div>",
                                 unsafe_allow_html=True)

    df = load_data()
    drivers = sorted(df["Driver"].unique())

    st.sidebar.title("Telemetry Lab")
    view = st.sidebar.radio("View", ["Replay", "Compare Lap Times", "Track Map", "Pipeline & Method"])
    
    driver = st.sidebar.selectbox("Driver", drivers, key="driver_select")
    lap_options = sorted(df[df["Driver"] == driver]["LapNumber"].unique())
    lap = st.sidebar.selectbox("Lap", lap_options, format_func=lambda x: f"Lap {int(x)}", key="lap_select")

    sub = df[(df["Driver"] == driver) & (df["LapNumber"] == float(lap))]

    st.title("ERT Telemetry Lab")
    st.caption(f"Formula Student telemetry showcase — {driver} · Lap {int(lap)}")

    if view == "Replay":
        show_replay(sub)
    elif view == "Compare Lap Times":
        show_comparison(df, drivers)
    elif view == "Track Map":
        lap_options_map = sorted(df[df["Driver"] == driver]["LapNumber"].unique())
        lap_map = st.sidebar.selectbox("Lap", lap_options_map, format_func=lambda x: f"Lap {int(x)}", key="map_lap_select")
        sub_map = df[(df["Driver"] == driver) & (df["LapNumber"] == float(lap_map))]
        st.plotly_chart(track_map(sub_map), use_container_width=True)
    elif view == "Pipeline & Method":
        show_pipeline()


if __name__ == "__main__":
    main()
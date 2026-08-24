import pandas as pd
import plotly.express as px
import streamlit as st

from auth import require_passcode
from data import ingest, schema as s
from data.transform import build_dashboard_df

st.set_page_config(page_title="Roleplay Dashboard", page_icon="\U0001f3ad", layout="wide")

# Viewers are in Thailand, but the app is not: Streamlit Community Cloud runs
# its containers in UTC, so a naive pd.Timestamp.now() reported a time 7 hours
# behind for everyone. Pin the display timezone rather than trusting the
# server's locale. (The Form's own timestamps already arrive in the form's
# timezone and are deliberately left as-is.)
DISPLAY_TZ = "Asia/Bangkok"

require_passcode()

# Cards: st.container(border=True, key=...) gets a stable ".st-key-<key>"
# class from Streamlit itself - the documented, version-stable hook for
# targeting a specific container with custom CSS (unlike guessing internal
# data-testid names, which change between Streamlit versions).
st.markdown(
    """
    <style>
    div[class*="st-key-card-"] {
        background-color: #FFFFFF;
        border-radius: 14px;
        padding: 1.1rem 1.4rem;
        border: 1px solid #E4E7EC;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def card(key: str):
    return st.container(border=True, key=f"card-{key}")


def clean_fig(fig):
    """Strip Plotly's own default plot/paper background so the chart blends
    into the white card instead of drawing its own gray rectangle inside it."""
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig


# Cached as one unit. The module-level load below runs on EVERY rerun -
# every widget click, by every viewer - and the classify/join/score pipeline
# is pure-Python, so it holds the GIL and serialises across viewers. Caching
# it makes that work happen once per TTL for the whole process instead of
# once per interaction per viewer. The TTL matches the responses feed; the
# roster keeps its own longer TTL on the underlying fetch.
@st.cache_data(ttl=600, show_spinner=False)
def load_dashboard() -> tuple[pd.DataFrame, pd.Timestamp]:
    df = build_dashboard_df(ingest.fetch_responses(), ingest.fetch_mapping())
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    # Returned alongside the frame so the header can report when the data
    # was actually fetched, rather than when the page happened to re-render.
    return df, pd.Timestamp.now(tz=DISPLAY_TZ)


def render_overview(df: pd.DataFrame) -> None:
    usable = df[~df["needs_review"]]
    channels = sorted(usable["Channel"].dropna().unique())
    selected = st.multiselect("Channel", channels, default=channels, key="overview_channel")
    filtered = usable[usable["Channel"].isin(selected)] if selected else usable

    col1, col2, col3, col4 = st.columns(4)
    with col1, card("kpi-total"):
        st.metric("Total responses", len(df))
    with col2, card("kpi-avg"):
        st.metric("Avg score", f"{filtered['score_pct'].mean():.1f}%" if len(filtered) else "—")
    with col3, card("kpi-pass"):
        st.metric("Pass rate", f"{filtered['passed'].mean() * 100:.1f}%" if len(filtered) else "—")
    with col4, card("kpi-review"):
        st.metric("Needs review", int(df["needs_review"].sum()))

    with st.expander("ℹ️ วิธีคำนวณค่าเหล่านี้"):
        st.markdown(
            "**Score trend over time**: ค่าเฉลี่ยของ Score (%) จากทุกแบบประเมินที่ถูกส่ง"
            "ในวันนั้น นับตาม **จำนวนครั้งที่ประเมิน ไม่ใช่นับต่อคน** "
            "(ถ้าพนักงานคนเดียวถูกประเมินหลายครั้งในวันเดียวกัน แต่ละครั้งจะถูกนำมาคิดเฉลี่ยแยกกัน) "
            "คำนวณเฉพาะแถวที่ข้อมูลถูกต้อง ไม่รวมแถวที่ต้อง Review\n\n"
            "**Pass rate by Channel/Region**: สัดส่วน (%) ของแบบประเมินที่ได้ Score ≥ 80% "
            "ต่อจำนวนแบบประเมินทั้งหมดในกลุ่มนั้น นับตามจำนวนครั้งที่ประเมินเช่นกัน ไม่ใช่นับต่อคน"
        )

    with card("trend"):
        st.subheader("Score trend over time")
        if len(filtered):
            trend = filtered.groupby("date")["score_pct"].mean().reset_index()
            fig = px.line(
                trend, x="date", y="score_pct", markers=True,
                labels={"score_pct": "Score (%)", "date": "Date"},
            )
            st.plotly_chart(clean_fig(fig), width="stretch")
        else:
            st.info("No data for the selected filters.")

    c1, c2 = st.columns(2)
    with c1, card("by-channel"):
        st.subheader("Pass rate by Channel")
        if len(filtered):
            by_channel = filtered.groupby("Channel")["passed"].mean().mul(100).reset_index()
            fig = px.bar(by_channel, x="Channel", y="passed", labels={"passed": "Passed rate (%)"})
            st.plotly_chart(clean_fig(fig), width="stretch")
    with c2, card("by-region"):
        st.subheader("Pass rate by Region")
        if len(filtered):
            by_region = filtered.groupby("REGION_(New)")["passed"].mean().mul(100).reset_index()
            fig = px.bar(by_region, x="REGION_(New)", y="passed", labels={"passed": "Passed rate (%)"})
            st.plotly_chart(clean_fig(fig), width="stretch")

    with st.expander(f"⚠️ Needs review ({int(df['needs_review'].sum())} rows)"):
        review_cols = [
            "timestamp", "evaluator_role", "evaluee_position", "sale_code_raw",
            "sale_code_confidence", "sale_code_extracted_name", "LOWER_FULL_Name_TH", "score_pct",
        ]
        st.dataframe(df.loc[df["needs_review"], review_cols], width="stretch")


def render_all_responses(df: pd.DataFrame) -> None:
    with st.expander("ℹ️ เกณฑ์การให้คะแนน"):
        legend = pd.DataFrame(
            {"Criterion": s.SCORE_CRITERIA_TH.keys(), "คำอธิบาย": s.SCORE_CRITERIA_TH.values()}
        )
        st.table(legend.set_index("Criterion"))

    # Rows that failed the roster lookup have NaN Channel/Position - give
    # them an explicit "(unmapped)" bucket instead of silently dropping
    # out of every filter's .isin() check (NaN never matches).
    work = df.copy()
    for col in ("evaluator_role", "evaluee_position", "Channel"):
        work[col] = work[col].fillna("(unmapped)")

    with card("responses-table"):
        # Border per-container rather than st.columns(border=True), so the
        # checkbox column can stay borderless while the three selects don't.
        f1, f2, f3, f4 = st.columns(4)
        with f1, st.container(border=True):
            roles = sorted(work["evaluator_role"].unique())
            sel_roles = st.multiselect(s.EVALUATOR_LABEL_TH, roles, default=roles, key="raw_roles")
        with f2, st.container(border=True):
            positions = sorted(work["evaluee_position"].unique())
            sel_positions = st.multiselect(s.POSITION_LABEL_TH, positions, default=positions, key="raw_positions")
        with f3, st.container(border=True):
            channels = sorted(work["Channel"].unique())
            sel_channels = st.multiselect("Channel", channels, default=channels, key="raw_channels")
        with f4:
            review_only = st.checkbox("Needs review only", key="raw_review_only")

        filtered = work[
            work["evaluator_role"].isin(sel_roles)
            & work["evaluee_position"].isin(sel_positions)
            & work["Channel"].isin(sel_channels)
        ]
        if review_only:
            filtered = filtered[filtered["needs_review"]]

        display = filtered[s.RESPONSE_TABLE_COLUMNS].rename(columns=s.DISPLAY_LABELS)
        st.dataframe(display, width="stretch", height=600)
        st.caption(f"{len(filtered)} of {len(df)} rows shown")


with st.spinner("Loading data..."):
    df, loaded_at = load_dashboard()

# Deliberately computed at render time rather than inside the cached
# function: the absolute stamp is frozen with the data, but the "N min old"
# must keep counting up as viewers interact, otherwise it would itself be
# stale. It measures the age of the responses feed (load_dashboard re-runs
# only after fetch_responses has expired, so the two stay in step); the
# roster rides its own hour-long TTL and can be older than this number.
age = pd.Timestamp.now(tz=DISPLAY_TZ) - loaded_at
age_minutes = int(age.total_seconds() // 60)
freshness = "just now" if age_minutes < 1 else f"{age_minutes} min old"
last_updated = loaded_at.strftime("%Y-%m-%d %H:%M (%Z)")

header_col, refresh_col = st.columns([5, 1])
with header_col:
    st.title("Roleplay Training Dashboard")
    st.caption(
        f"{len(df)} responses · data as of {last_updated} · {freshness} · "
        f"{int(df['needs_review'].sum())} need review"
    )
with refresh_col:
    if st.button("\U0001f504 Refresh data"):
        # Scoped rather than st.cache_data.clear(), which would also evict
        # the roster and force a re-download of the .xlsx (~1.6s) that has a
        # deliberate 60-min TTL because it changes rarely. Both clears are
        # needed and neither is sufficient alone: load_dashboard is built
        # from fetch_responses, so clearing only the frame would rebuild it
        # from still-cached responses, and clearing only the responses would
        # leave the cached frame in place. Process-wide, so this refreshes
        # for every viewer, not just the one who clicked.
        ingest.fetch_responses.clear()
        load_dashboard.clear()
        st.rerun()

# Deliberately not st.tabs: it renders every tab body server-side on every
# rerun (switching is client-side only), so the heavy All Responses table
# was being built even for viewers sitting on Overview. This trades instant
# client-side switching for never rendering the view nobody is looking at.
view = st.radio(
    "View", ["Overview", "All Responses"],
    horizontal=True, label_visibility="collapsed", key="view",
)

if view == "Overview":
    render_overview(df)
else:
    render_all_responses(df)

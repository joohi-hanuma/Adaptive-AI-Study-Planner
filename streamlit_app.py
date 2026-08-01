
"""
Streamlit UI for the Adaptive AI Study Planner.
 
Visual style matches a reference "AI Study Planner" dashboard: light
background, purple accent sidebar, stat tiles, a donut progress chart,
and card-based resource/tip/deadline widgets.
 
All underlying logic is unchanged from the previous version -- this
file only changes layout and styling. It still calls the exact same
LangGraph app defined in study_planner.py.
 
Run with:
    streamlit run streamlit_app.py
"""
 
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
 
from study_planner import build_graph, StudyPlannerState
 
# =====================================================================
# PAGE CONFIG
# =====================================================================
st.set_page_config(
    page_title="AI Study Planner",
    page_icon="🎓",
    layout="wide",
)
 
# ---------------------------------------------------------------
# Subject color chips (light bg + matching text, cycles per subject)
# ---------------------------------------------------------------
CHIP_PALETTE = [
    ("#EDE9FE", "#7C3AED"),  # violet
    ("#DBEAFE", "#2563EB"),  # blue
    ("#FEF3C7", "#B45309"),  # amber
    ("#D1FAE5", "#059669"),  # green
    ("#FCE7F3", "#DB2777"),  # pink
    ("#E0F2FE", "#0284C7"),  # sky
]
 
 
def chip_colors(subject: str):
    h = sum(ord(c) for c in (subject or "General"))
    return CHIP_PALETTE[h % len(CHIP_PALETTE)]
 
 
STATUS_STYLE = {
    "completed": ("#059669", "#D1FAE5", "✓ Completed"),
    "incomplete": ("#DC2626", "#FEE2E2", "✕ Incomplete"),
    "pending": ("#2563EB", "#DBEAFE", "◔ Upcoming"),
}
 
QUOTES = [
    ("Consistency is the key to success.", "Keep going!"),
    ("Small steps every day add up to big results.", "You've got this!"),
    ("Discipline beats motivation on the hard days.", "Stay steady."),
    ("Progress, not perfection.", "One session at a time."),
]
 
# =====================================================================
# GLOBAL CSS
# =====================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');
 
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3, h4, h5, h6 { font-family: 'Poppins', sans-serif; }
 
/* ---------------------------------------------------------------
   Animated gradient + floating blob background
   (pure CSS -- Streamlit can't run Framer Motion / JS animation
   libraries, but a soft moving blob field works fine in CSS alone)
--------------------------------------------------------------- */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #F5F3FF 0%, #EFF6FF 40%, #F0FDFA 100%);
    position: relative;
    overflow-x: hidden;
}
.blob-field { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.blob { position: absolute; border-radius: 50%; filter: blur(60px); opacity: 0.35; }
.blob-1 { width: 380px; height: 380px; top: -100px; left: -80px;
    background: radial-gradient(circle, #C4B5FD 0%, transparent 70%);
    animation: floatBlob 18s ease-in-out infinite; }
.blob-2 { width: 420px; height: 420px; top: 20%; right: -140px;
    background: radial-gradient(circle, #93C5FD 0%, transparent 70%);
    animation: floatBlob 22s ease-in-out infinite reverse; }
.blob-3 { width: 340px; height: 340px; bottom: -80px; left: 30%;
    background: radial-gradient(circle, #6EE7B7 0%, transparent 70%);
    animation: floatBlob 20s ease-in-out infinite; }
.blob-4 { width: 300px; height: 300px; bottom: 10%; right: 15%;
    background: radial-gradient(circle, #FDBA74 0%, transparent 70%);
    animation: floatBlob 16s ease-in-out infinite reverse; }
@keyframes floatBlob {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(30px, -25px) scale(1.08); }
    66% { transform: translate(-20px, 20px) scale(0.95); }
}
[data-testid="stMain"] > div { position: relative; z-index: 1; }
 
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
 
/* ---------------------------------------------------------------
   Sidebar -- dark glass with colorful gradient section tiles
--------------------------------------------------------------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(27,20,66,0.97) 0%, rgba(36,27,92,0.97) 100%);
    backdrop-filter: blur(12px);
}
/* Make sure the sidebar scrolls -- with many subjects the form is
   taller than the viewport, and this was previously getting clipped
   with no visible scrollbar. */
[data-testid="stSidebar"] > div {
    height: 100vh;
    overflow-y: auto !important;
}
[data-testid="stSidebar"] * { color: #EDEBFB !important; }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea {
    color: #1F2340 !important;
}
.sidebar-brand {
    display: flex; align-items: center; gap: 0.6rem;
    margin-bottom: 0.1rem;
}
.sidebar-brand .icon {
    font-size: 1.6rem;
    background: linear-gradient(135deg, #7C5CFC, #2563EB);
    border-radius: 12px;
    padding: 0.4rem 0.55rem;
    box-shadow: 0 4px 14px rgba(124,92,252,0.45);
}
.sidebar-brand .title { font-family:'Poppins',sans-serif; font-weight:700; font-size:1.15rem; }
.sidebar-tagline { color:#A79EE0 !important; font-size:0.8rem; margin-bottom:1.2rem; }
.sidebar-section-tile {
    display:inline-block; padding:0.35rem 0.8rem; border-radius:10px;
    font-weight:700; font-size:0.85rem; margin: 0.6rem 0 0.6rem 0;
}
.tile-violet { background: linear-gradient(135deg, #7C3AED, #A78BFA); box-shadow:0 3px 10px rgba(124,58,237,0.4); }
.tile-blue   { background: linear-gradient(135deg, #2563EB, #60A5FA); box-shadow:0 3px 10px rgba(37,99,235,0.4); }
 
/* ---------------------------------------------------------------
   Greeting header
--------------------------------------------------------------- */
.greet-row { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1.4rem; }
.greet-row h1 {
    font-size:1.9rem; font-weight:800; margin:0;
    background: linear-gradient(90deg, #7C3AED 0%, #2563EB 50%, #059669 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
.greet-row p { color:#6B7094; margin:0.15rem 0 0 0; }
.avatar-circle {
    width:46px; height:46px; border-radius:50%;
    background: linear-gradient(135deg, #7C5CFC, #EC4899); color:white;
    display:flex; align-items:center; justify-content:center; font-weight:700;
    font-family:'Poppins',sans-serif; font-size:1.1rem;
    box-shadow:0 4px 14px rgba(124,92,252,0.45);
}
 
/* ---------------------------------------------------------------
   Stat tiles -- each one a distinct soft gradient, glass border,
   hover-lift (CSS-only "premium card" feel)
--------------------------------------------------------------- */
.stat-card {
    border-radius:18px; padding:1.1rem 1.2rem;
    border:1px solid rgba(255,255,255,0.6);
    box-shadow:0 6px 18px rgba(31,35,64,0.08);
    backdrop-filter: blur(6px);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    animation: fadeInUp 0.4s ease both;
}
.stat-card:hover { transform: translateY(-4px); box-shadow:0 10px 26px rgba(31,35,64,0.14); }
.stat-card .stat-icon {
    width:38px; height:38px; border-radius:10px; display:flex;
    align-items:center; justify-content:center; font-size:1.15rem; margin-bottom:0.6rem;
}
.stat-card .stat-label { color:#6B7094; font-size:0.85rem; font-weight:600; }
.stat-card .stat-num { font-family:'Poppins',sans-serif; font-size:1.7rem; font-weight:800; color:#1F2340; }
.stat-card .stat-sub { color:#8B90AE; font-size:0.78rem; }
 
/* ---------------------------------------------------------------
   Bordered containers used as dashboard cards -- glass style
   (scoped to the MAIN area only -- must NOT apply inside the
   sidebar, or the Subject boxes there turn white-on-white)
--------------------------------------------------------------- */
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
    border-radius:18px !important;
    background: rgba(255,255,255,0.72) !important;
    backdrop-filter: blur(10px);
    border:1px solid rgba(255,255,255,0.7) !important;
    box-shadow:0 6px 20px rgba(31,35,64,0.07);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    animation: fadeInUp 0.45s ease both;
}
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow:0 10px 28px rgba(31,35,64,0.12);
}
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] h4 {
    margin:0 0 0.9rem 0; font-size:1.05rem;
}
 
/* Sidebar's own bordered Subject boxes -- keep dark & readable */
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,0.06) !important;
    border:1px solid rgba(255,255,255,0.18) !important;
    border-radius:12px !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] * {
    color: #EDEBFB !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] input,
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] textarea {
    color: #1F2340 !important;
}
 
/* per-card accent gradients (via Streamlit's container key -> st-key-*) */
div.st-key-card-timetable  { border-top:3px solid #7C3AED !important; }
div.st-key-card-progress   { border-top:3px solid #2563EB !important; }
div.st-key-card-resources  { border-top:3px solid #059669 !important; }
div.st-key-card-tip        { border-top:3px solid #B45309 !important; }
div.st-key-card-deadlines  { border-top:3px solid #DB2777 !important; }
div.st-key-card-goal       { border-top:3px solid #7C5CFC !important; }
 
/* ---------------------------------------------------------------
   Subject / status chips -- gradient pills
--------------------------------------------------------------- */
.chip {
    display:inline-block; padding:0.22rem 0.7rem; border-radius:999px;
    font-size:0.78rem; font-weight:700;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
 
/* Quote box */
.quote-box {
    background: linear-gradient(135deg, #F3F0FF, #EAF3FF);
    border-radius:12px; padding:0.9rem 1rem;
    color:#4C3FA8; font-size:0.88rem; font-style:italic; margin-top:0.9rem;
}
 
/* Deadline / resource rows */
.row-item { display:flex; justify-content:space-between; align-items:center;
    padding:0.55rem 0; border-bottom:1px solid rgba(31,35,64,0.06); }
.row-item:last-child { border-bottom:none; }
.row-title { font-weight:600; color:#1F2340; font-size:0.92rem; }
.row-sub { color:#8B90AE; font-size:0.78rem; }
 
/* Tip card */
.tip-box {
    background: linear-gradient(135deg, #FFF7ED, #FEF3C7);
    border-radius:12px; padding:0.9rem 1rem;
    color:#7C4A03; font-size:0.88rem; text-align:center;
}
 
/* Goal bar */
.goal-bar-bg { background:#EDECF5; border-radius:999px; height:10px; width:100%; overflow:hidden; }
.goal-bar-fill { background: linear-gradient(90deg, #7C5CFC, #2563EB, #059669); border-radius:999px; height:10px; }
 
/* ---------------------------------------------------------------
   Tabs -- each tab gets its own accent color
--------------------------------------------------------------- */
div[data-baseweb="tab-list"] button:nth-child(1) { color:#7C3AED !important; }
div[data-baseweb="tab-list"] button:nth-child(2) { color:#2563EB !important; }
div[data-baseweb="tab-list"] button:nth-child(3) { color:#B45309 !important; }
div[data-baseweb="tab-list"] button:nth-child(4) { color:#059669 !important; }
div[data-baseweb="tab-list"] button[aria-selected="true"] { font-weight:700; opacity:1; }
div[data-baseweb="tab-list"] button[aria-selected="false"] { opacity:0.55; }
 
/* Sidebar section headings get a lavender tint instead of plain white */
[data-testid="stSidebar"] h4 { color:#C9BFFF !important; }
 
/* ---------------------------------------------------------------
   Buttons -- gradient pill with hover glow (closest CSS-only
   equivalent of a "ripple" effect Streamlit can't natively do)
--------------------------------------------------------------- */
.stButton > button {
    border-radius:999px; font-weight:700; border:1px solid rgba(124,92,252,0.25);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stButton > button:hover { transform: translateY(-2px) scale(1.02); }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7C5CFC 0%, #2563EB 60%, #059669 120%);
    border:none; color:white;
    box-shadow: 0 6px 18px rgba(124,92,252,0.45);
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 8px 22px rgba(124,92,252,0.6);
}
</style>
 
<div class="blob-field">
    <div class="blob blob-1"></div>
    <div class="blob blob-2"></div>
    <div class="blob blob-3"></div>
    <div class="blob blob-4"></div>
</div>
""", unsafe_allow_html=True)
 
 
def subject_chip(subject: str) -> str:
    bg, fg = chip_colors(subject)
    return f'<span class="chip" style="background:{bg}; color:{fg};">{subject}</span>'
 
 
def status_chip(status: str) -> str:
    fg, bg, label = STATUS_STYLE.get(status, ("#6B7094", "#F1F1F7", status))
    return f'<span class="chip" style="background:{bg}; color:{fg};">{label}</span>'
 
 
# =====================================================================
# APP STATE
# =====================================================================
if "app" not in st.session_state:
    st.session_state.app = build_graph()
if "planner_state" not in st.session_state:
    st.session_state.planner_state = None
 
# =====================================================================
# SIDEBAR -- Student Input Collector (unchanged logic, new look)
# =====================================================================
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="icon">🎓</div>
        <div class="title">AI Study Planner</div>
    </div>
    <div class="sidebar-tagline">Plan Smarter. Study Better.</div>
    """, unsafe_allow_html=True)
 
    st.markdown('<div class="sidebar-section-tile tile-violet">📝 Your Study Details</div>', unsafe_allow_html=True)
    name = st.text_input("Name", "Student")
    num_subjects = st.number_input("Number of subjects", 1, 6, 2)
 
    subjects = []
    for i in range(int(num_subjects)):
        with st.container(border=True):
            st.markdown(f"**Subject {i+1}**")
            subj_name = st.text_input("Subject name", key=f"subj_{i}")
            topics_raw = st.text_area(
                "Topics (one per line)", key=f"topics_{i}", height=90,
            )
            deadline = st.date_input(
                "Deadline",
                value=date.today() + timedelta(days=14),
                key=f"deadline_{i}",
            )
            if subj_name and topics_raw:
                subjects.append({
                    "subject": subj_name,
                    "topics": [t.strip() for t in topics_raw.splitlines() if t.strip()],
                    "deadline": deadline.isoformat(),
                })
 
    st.markdown('<div class="sidebar-section-tile tile-blue">⏱️ Study Rhythm</div>', unsafe_allow_html=True)
    hours_per_day = st.slider("Available hours/day", 1.0, 8.0, 2.0, 0.5)
    session_minutes = st.slider("Preferred session length (min)", 15, 120, 45, 5)
    revision_pref = st.selectbox("Revision preference", ["weekly", "daily", "none"])
    test_freq = st.slider("Test frequency (days)", 1, 14, 7)
 
    generate = st.button("✨ Generate Study Plan", type="primary", use_container_width=True)
 
    st.markdown("---")
    st.markdown("🤖 **Hello, Student!**")
    st.caption("I'm your AI study assistant. Let's achieve your goals together!")
 
# =====================================================================
# RUN THE GRAPH  (unchanged logic)
# =====================================================================
if generate:
    initial_state: StudyPlannerState = {
        "student_name": name,
        "subjects": subjects,
        "available_hours_per_day": hours_per_day,
        "preferred_session_minutes": session_minutes,
        "revision_preference": revision_pref,
        "test_frequency_days": test_freq,
        "start_date": date.today().isoformat(),
        "iteration": 0,
    }
    with st.spinner("Agents are drafting your plan..."):
        st.session_state.planner_state = st.session_state.app.invoke(initial_state)
 
state = st.session_state.planner_state
 
# ---------------------------------------------------------------
# Greeting header (shown even before a plan exists)
# ---------------------------------------------------------------
hour = datetime.now().hour
if hour < 12:
    greeting, icon = "Good Morning", "☀️"
elif hour < 17:
    greeting, icon = "Good Afternoon", "🌤️"
else:
    greeting, icon = "Good Evening", "🌙"
 
display_name = state.get("student_name", name) if state else name
initial_letter = (display_name or "S")[0].upper()
 
g_col1, g_col2 = st.columns([5, 1])
with g_col1:
    st.markdown(f"""
    <div class="greet-row">
        <div>
            <h1>{greeting}, {display_name}! {icon}</h1>
            <p>Ready to continue your learning journey?</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
with g_col2:
    st.markdown(f'<div class="avatar-circle">{initial_letter}</div>', unsafe_allow_html=True)
 
if state is None:
    st.info("👈 Fill in your subjects on the left, then click **Generate Study Plan** to see your dashboard.")
    st.stop()
 
if not state.get("input_valid", True):
    st.error("Please fix the following before continuing:")
    for e in state.get("validation_errors", []):
        st.write(f"- {e}")
    st.stop()
 
all_tasks = state["timetable"] + state.get("assessments", [])
completed = [t for t in all_tasks if t["status"] == "completed"]
incomplete = [t for t in all_tasks if t["status"] == "incomplete"]
pending = [t for t in all_tasks if t["status"] == "pending"]
 
today_str = date.today().isoformat()
today_tasks = sorted(
    [t for t in state["timetable"] if t["date"] == today_str],
    key=lambda t: t["id"],
)
 
# ---------------------------------------------------------------
# Stat tiles
# ---------------------------------------------------------------
week_ago = (date.today() - timedelta(days=7)).isoformat()
hours_this_week = sum(
    t["duration_minutes"] for t in all_tasks
    if t["date"] >= week_ago and t["status"] in ("completed", "pending")
) / 60
completed_this_week = len([t for t in completed if t["date"] >= week_ago])
 
# simple streak: consecutive past days (from today backwards) that had
# tasks scheduled and all of them completed
streak = 0
day_cursor = date.today()
tasks_by_day = {}
for t in all_tasks:
    tasks_by_day.setdefault(t["date"], []).append(t)
while True:
    day_tasks = tasks_by_day.get(day_cursor.isoformat())
    if not day_tasks or day_cursor > date.today():
        day_cursor -= timedelta(days=1)
        if not tasks_by_day.get(day_cursor.isoformat()):
            break
        continue
    if all(t["status"] == "completed" for t in day_tasks):
        streak += 1
        day_cursor -= timedelta(days=1)
    else:
        break
 
stat_defs = [
    ("📚", "#EDE9FE", "#7C3AED", "Total Subjects", len(state.get("subjects", [])), "Active Subjects"),
    ("⏱️", "#DBEAFE", "#2563EB", "Study Hours", f"{hours_this_week:.1f}", "This Week"),
    ("✅", "#D1FAE5", "#059669", "Tasks Completed", completed_this_week, "This Week"),
    ("🔥", "#FEF3C7", "#B45309", "Current Streak", streak, "Days in a Row"),
]
cols = st.columns(4)
for col, (icon_, bg, fg, label, num, sub) in zip(cols, stat_defs):
    col.markdown(f"""
    <div class="stat-card" style="background:linear-gradient(160deg, {bg} 0%, #FFFFFF 75%); border-top:3px solid {fg};">
        <div class="stat-icon" style="background:{bg}; color:{fg};">{icon_}</div>
        <div class="stat-label">{label}</div>
        <div class="stat-num">{num}</div>
        <div class="stat-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)
 
st.write("")
 
# ---------------------------------------------------------------
# Today's Timetable  +  Progress Overview
# ---------------------------------------------------------------
main_col, side_col = st.columns([2.1, 1])
 
with main_col:
    with st.container(border=True, key="card-timetable"):
        st.markdown(f"""
        <h4 style="color:#7C3AED;">📅 Today's Study Timetable &nbsp;
        <span style="float:right; color:#8B90AE; font-size:0.85rem; font-weight:500;">
        {datetime.now().strftime('%b %d, %Y')}</span></h4>
        """, unsafe_allow_html=True)
 
        if not today_tasks:
            st.caption("No sessions scheduled for today.")
        else:
            for t in today_tasks:
                c1, c2, c3 = st.columns([3, 2, 2])
                with c1:
                    st.markdown(f"**{t['topic']}** &nbsp; {subject_chip(t['subject'])}",
                                unsafe_allow_html=True)
                    st.caption(f"{t['duration_minutes']} min")
                with c2:
                    st.markdown(status_chip(t["status"]), unsafe_allow_html=True)
                with c3:
                    new_status = st.selectbox(
                        "status", ["pending", "completed", "incomplete"],
                        index=["pending", "completed", "incomplete"].index(t["status"]),
                        key=f"today_status_{t['id']}", label_visibility="collapsed",
                    )
                    t["status"] = new_status
 
with side_col:
    total_n = len(all_tasks) or 1
    pct_completed = round(len(completed) / total_n * 100)
    pct_pending = round(len(pending) / total_n * 100)
    pct_incomplete = 100 - pct_completed - pct_pending
 
    with st.container(border=True, key="card-progress"):
        st.markdown('<h4 style="color:#2563EB;">📊 Progress Overview</h4>', unsafe_allow_html=True)
        fig = go.Figure(data=[go.Pie(
            labels=["Completed", "Upcoming", "Incomplete"],
            values=[len(completed), len(pending), len(incomplete)],
            hole=0.68,
            marker=dict(colors=["#059669", "#2563EB", "#DC2626"]),
            textinfo="none",
            sort=False,
        )])
        fig.update_layout(
            showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=200,
            annotations=[dict(text=f"{pct_completed}%", x=0.5, y=0.55, font_size=26,
                               showarrow=False, font_family="Poppins"),
                         dict(text="Overall Progress", x=0.5, y=0.38, font_size=11,
                              showarrow=False, font_color="#8B90AE")],
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
 
        st.markdown(f"""
        <div class="row-item"><span>🟢 Completed</span><b>{pct_completed}%</b></div>
        <div class="row-item"><span>🔵 Upcoming</span><b>{pct_pending}%</b></div>
        <div class="row-item"><span>🔴 Incomplete</span><b>{pct_incomplete}%</b></div>
        """, unsafe_allow_html=True)
 
        quote, sub = QUOTES[sum(ord(c) for c in display_name) % len(QUOTES)]
        st.markdown(f'<div class="quote-box">"{quote}"<br>— {sub}</div>', unsafe_allow_html=True)
 
st.write("")
 
# ---------------------------------------------------------------
# Resources  +  AI Study Tip  +  Upcoming Deadlines
# ---------------------------------------------------------------
r_col, t_col, d_col = st.columns(3)
 
with r_col:
    with st.container(border=True, key="card-resources"):
        st.markdown('<h4 style="color:#059669;">📖 Recommended Resources</h4>', unsafe_allow_html=True)
        res_items = list(state.get("resources_map", {}).items())[:3]
        if not res_items:
            st.caption("No resources generated yet.")
        for topic_key, res_list in res_items:
            subject, topic = topic_key.split("::")
            st.markdown(f"""
            <div class="row-item">
                <div><div class="row-title">{topic}</div><div class="row-sub">{subject}</div></div>
            </div>
            """, unsafe_allow_html=True)
            for r in res_list[:1]:
                st.caption(f"↳ {r}")
 
with t_col:
    with st.container(border=True, key="card-tip"):
        st.markdown('<h4 style="color:#B45309;">💡 AI Study Tip</h4>', unsafe_allow_html=True)
        if incomplete:
            tip_subject = incomplete[0]["subject"]
            tip = f"You have {len(incomplete)} incomplete session(s). Revisit **{tip_subject}** first — it's falling behind."
        elif today_tasks:
            tip = f"You have {len(today_tasks)} session(s) today. Tackle your hardest subject first while you're fresh."
        else:
            tip = "No sessions today — a good day to get ahead on upcoming topics!"
        st.markdown(f'<div class="tip-box">🤖<br><br>{tip}</div>', unsafe_allow_html=True)
 
with d_col:
    with st.container(border=True, key="card-deadlines"):
        st.markdown('<h4 style="color:#DB2777;">📆 Upcoming Deadlines</h4>', unsafe_allow_html=True)
        deadlines = []
        for s in state.get("subjects", []):
            try:
                d = datetime.fromisoformat(s["deadline"]).date()
                deadlines.append((s["subject"], d, (d - date.today()).days))
            except Exception:
                continue
        deadlines.sort(key=lambda x: x[2])
        if not deadlines:
            st.caption("No deadlines set.")
        for subj, d, days_left in deadlines[:4]:
            urgency_color = "#DC2626" if days_left <= 3 else "#B45309" if days_left <= 7 else "#059669"
            urgency_bg = "#FEE2E2" if days_left <= 3 else "#FEF3C7" if days_left <= 7 else "#D1FAE5"
            st.markdown(f"""
            <div class="row-item">
                <div><div class="row-title">{subj}</div><div class="row-sub">{d.strftime('%b %d, %Y')}</div></div>
                <span class="chip" style="background:{urgency_bg}; color:{urgency_color};">
                {days_left if days_left >= 0 else 0} days left</span>
            </div>
            """, unsafe_allow_html=True)
 
st.write("")
 
# ---------------------------------------------------------------
# Goal bar (nearest deadline subject)
# ---------------------------------------------------------------
if deadlines:
    goal_subject, goal_date, _ = deadlines[0]
    subject_tasks = [t for t in all_tasks if t["subject"] == goal_subject]
    goal_pct = round(
        len([t for t in subject_tasks if t["status"] == "completed"]) / (len(subject_tasks) or 1) * 100
    )
    with st.container(border=True, key="card-goal"):
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:1rem;">
            <div style="font-size:1.3rem;">🎯</div>
            <div style="flex:1;">
                <b>Goal:</b> Master {goal_subject} by {goal_date.strftime('%B %d, %Y')}
                <div class="goal-bar-bg" style="margin-top:0.5rem;">
                    <div class="goal-bar-fill" style="width:{goal_pct}%;"></div>
                </div>
            </div>
            <div style="font-weight:700; color:#7C5CFC; font-size:1.1rem;">{goal_pct}%</div>
        </div>
        """, unsafe_allow_html=True)
 
st.write("")
 
# =====================================================================
# TABS -- full editable views (unchanged logic, restyled)
# =====================================================================
tab1, tab2, tab3, tab4 = st.tabs(
    ["📅  Full Timetable", "📖  Resources", "📝  Assessments", "📈  Progress & Report"]
)
 
with tab1:
    st.markdown('<h5 style="color:#7C3AED;">📅 Full Timetable</h5>', unsafe_allow_html=True)
    tasks_by_date = {}
    for t in state["timetable"]:
        tasks_by_date.setdefault(t["date"], []).append(t)
 
    for d in sorted(tasks_by_date.keys()):
        st.markdown(f'<span style="color:#7C3AED; font-weight:700;">{d}</span>', unsafe_allow_html=True)
        for t in tasks_by_date[d]:
            with st.container(border=True):
                c1, c2 = st.columns([5, 2])
                with c1:
                    st.markdown(
                        f'{subject_chip(t["subject"])} &nbsp; <b>{t["topic"]}</b><br>'
                        f'<span style="color:#8B90AE; font-size:0.8rem;">{t["duration_minutes"]} min</span> '
                        f'&nbsp; {status_chip(t["status"])}',
                        unsafe_allow_html=True,
                    )
                with c2:
                    new_status = st.selectbox(
                        "status", ["pending", "completed", "incomplete"],
                        index=["pending", "completed", "incomplete"].index(t["status"]),
                        key=f"status_{t['id']}", label_visibility="collapsed",
                    )
                    t["status"] = new_status
 
with tab2:
    st.markdown('<h5 style="color:#2563EB;">📖 Resources</h5>', unsafe_allow_html=True)
    if not state.get("resources_map"):
        st.caption("No resources generated yet.")
    for topic_key, res_list in state.get("resources_map", {}).items():
        subject, topic = topic_key.split("::")
        with st.container(border=True):
            st.markdown(f'{subject_chip(subject)} &nbsp; <b>{topic}</b>', unsafe_allow_html=True)
            for r in res_list:
                st.write(f"— {r}")
 
with tab3:
    st.markdown('<h5 style="color:#B45309;">📝 Assessments</h5>', unsafe_allow_html=True)
    if not state.get("assessments"):
        st.caption("No assessments scheduled yet.")
    for a in state.get("assessments", []):
        with st.container(border=True):
            c1, c2 = st.columns([5, 2])
            with c1:
                st.markdown(
                    f'{subject_chip(a["subject"])} &nbsp; '
                    f'<span style="color:#8B90AE; font-size:0.8rem;">{a["date"]}</span><br>'
                    f'<b>{a["topic"]}</b> &nbsp; {status_chip(a["status"])}',
                    unsafe_allow_html=True,
                )
            with c2:
                new_status = st.selectbox(
                    "status", ["pending", "completed", "incomplete"],
                    index=["pending", "completed", "incomplete"].index(a["status"]),
                    key=f"status_{a['id']}", label_visibility="collapsed",
                )
                a["status"] = new_status
 
with tab4:
    st.markdown('<h5 style="color:#059669;">📈 Progress & Report</h5>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    for col, num, lbl, fg in [(c1, len(completed), "Completed", "#059669"),
                               (c2, len(incomplete), "Incomplete", "#DC2626"),
                               (c3, len(pending), "Pending", "#2563EB")]:
        col.markdown(f"""
        <div class="stat-card" style="text-align:center; border-top:3px solid {fg};">
            <div class="stat-num" style="color:{fg};">{num}</div><div class="stat-label">{lbl}</div>
        </div>
        """, unsafe_allow_html=True)
 
    st.write("")
    if st.button("🔄 Update Progress & Reschedule", type="primary"):
        state["all_tasks_done"] = False
        with st.spinner("Rescheduling incomplete sessions..."):
            st.session_state.planner_state = st.session_state.app.invoke(state)
        st.rerun()
 
    st.write("")
    st.markdown('<h6 style="color:#7C5CFC;">Progress Log</h6>', unsafe_allow_html=True)
    st.table(state.get("progress_log", []))
 
    if state.get("final_report"):
        st.markdown('<h6 style="color:#7C5CFC;">Final Report</h6>', unsafe_allow_html=True)
        report = state["final_report"]
        report_rows = [
            {"Metric": k.replace("_", " ").title(), "Value": v}
            for k, v in report.items()
        ]
        st.table(pd.DataFrame(report_rows).set_index("Metric"))

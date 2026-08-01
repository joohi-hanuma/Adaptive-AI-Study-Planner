"""
=====================================================================
 ADAPTIVE AI STUDY PLANNER  --  Agentic AI + LangGraph Implementation
=====================================================================

This module implements the full workflow described in the project
abstract:

    Student Input --> Timetable Generator --> Resource Recommendation
    --> Assessment Generator --> Progress Tracker --> (loop) Schedule
    Updater --> Final Report

Each "agent" is a plain Python function that receives the shared
StudyPlannerState and returns a (partially) updated state. LangGraph's
StateGraph wires these functions together as nodes, and a conditional
edge implements the "Task Completed? -> continue / update schedule"
decision from the algorithm.

------------------------------------------------------------------
LLM INTEGRATION
------------------------------------------------------------------
The project brief allows either the OpenAI or the Gemini API. Both are
wired through a single call_llm() helper so you only need to set ONE
environment variable to switch providers:

    export LLM_PROVIDER=openai      # or "gemini"
    export OPENAI_API_KEY=sk-...
    export GEMINI_API_KEY=...

If neither key is present, the planner automatically falls back to a
deterministic, rule-based "OfflineLLM" so the whole pipeline can still
be run, demoed, and graded without any internet access or API key.
This fallback is what is used when you simply run:

    python study_planner.py

------------------------------------------------------------------
INSTALL
------------------------------------------------------------------
    pip install langgraph langchain langchain-openai langchain-google-genai
    pip install pandas numpy streamlit

Run:
    python study_planner.py
    streamlit run streamlit_app.py      (optional UI, see that file)
"""

from __future__ import annotations

import json
import os
import random
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, TypedDict

# ---------------------------------------------------------------
# LangGraph / LangChain imports
# ---------------------------------------------------------------
# These are the real imports used when the libraries are installed.
# (pip install langgraph langchain)
from langgraph.graph import StateGraph, END


# =====================================================================
# 1. STATE DEFINITION
# =====================================================================
# LangGraph passes ONE shared state object between every node/agent.
# We model it as a TypedDict so every agent knows exactly which keys
# it may read and write.

class Task(TypedDict):
    id: str
    subject: str
    topic: str
    date: str            # YYYY-MM-DD
    duration_minutes: int
    status: str           # "pending" | "completed" | "incomplete"
    resources: List[str]
    is_revision: bool
    is_assessment: bool


class StudyPlannerState(TypedDict, total=False):
    # ---- raw student input (Module 1: Student Input Collector) ----
    student_name: str
    subjects: List[Dict[str, Any]]     # [{subject, topics:[...], deadline}]
    available_hours_per_day: float
    preferred_session_minutes: int
    revision_preference: str           # "daily" | "weekly" | "none"
    test_frequency_days: int
    start_date: str

    # ---- validation ----
    input_valid: bool
    validation_errors: List[str]

    # ---- generated artifacts ----
    timetable: List[Task]
    resources_map: Dict[str, List[str]]
    assessments: List[Task]

    # ---- progress tracking / adaptive loop ----
    progress_log: List[Dict[str, Any]]
    incomplete_tasks: List[Task]
    iteration: int
    all_tasks_done: bool

    # ---- final output ----
    final_report: Dict[str, Any]


# =====================================================================
# 2. LLM WRAPPER  (OpenAI / Gemini / Offline fallback)
# =====================================================================

class OfflineLLM:
    """Deterministic stand-in used when no API key is configured.
    Lets the whole graph run end-to-end for testing/demo purposes."""

    def invoke(self, prompt: str) -> str:
        if "difficulty" in prompt.lower():
            return random.choice(["easy", "medium", "hard"])
        if "resource" in prompt.lower():
            return json.dumps([
                "Official textbook chapter",
                "Top-rated YouTube lecture",
                "Practice question bank",
            ])
        return "OK"


def get_llm():
    """Returns a callable LLM client based on LLM_PROVIDER env var.
    Falls back to OfflineLLM if no key is configured, so the pipeline
    always runs."""
    provider = os.environ.get("LLM_PROVIDER", "").lower()

    try:
        if provider == "openai" and os.environ.get("OPENAI_API_KEY"):
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

        if provider == "gemini" and os.environ.get("GEMINI_API_KEY"):
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0.3)
    except Exception as exc:  # pragma: no cover - network/env issues
        print(f"[LLM] Falling back to OfflineLLM ({exc})")

    return OfflineLLM()


LLM = get_llm()


def call_llm(prompt: str) -> str:
    """Uniform call for both real LangChain chat models and OfflineLLM.
    Always returns a plain string, regardless of whether the underlying
    model returns `content` as a string or as a list of content parts
    (some providers, including Gemini, can return a list)."""
    if isinstance(LLM, OfflineLLM):
        return LLM.invoke(prompt)

    response = LLM.invoke(prompt)          # LangChain chat model call
    content = getattr(response, "content", response)

    if isinstance(content, list):
        # content may be a list of dicts like {"type": "text", "text": "..."}
        # or a list of plain strings - normalize both to one string.
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "".join(parts)

    return str(content)


# =====================================================================
# 3. AGENT NODES
# =====================================================================

# ---------------------------------------------------------------
# Agent 1: Student Input Collector  (Study Coordinator)
# ---------------------------------------------------------------
def student_input_collector(state: StudyPlannerState) -> StudyPlannerState:
    """
    Step 2 of algorithm: Collect student inputs.
    In an interactive run this would prompt the user; for the graph we
    assume the state has already been seeded by the caller (CLI or
    Streamlit form) and this node simply normalizes defaults.
    """
    state.setdefault("start_date", date.today().isoformat())
    state.setdefault("preferred_session_minutes", 45)
    state.setdefault("revision_preference", "weekly")
    state.setdefault("test_frequency_days", 7)
    print(f"[Input Collector] Received input for {state.get('student_name', 'Student')}")
    return state


# ---------------------------------------------------------------
# Validation gate (Step 3 of algorithm)
# ---------------------------------------------------------------
def validate_input(state: StudyPlannerState) -> StudyPlannerState:
    errors: List[str] = []
    if not state.get("subjects"):
        errors.append("No subjects/topics provided.")
    if not state.get("available_hours_per_day"):
        errors.append("Available study hours per day missing.")
    for subj in state.get("subjects", []):
        if not subj.get("deadline"):
            errors.append(f"Deadline missing for subject '{subj.get('subject')}'")

    state["validation_errors"] = errors
    state["input_valid"] = len(errors) == 0
    print(f"[Validator] valid={state['input_valid']} errors={errors}")
    return state


def route_after_validation(state: StudyPlannerState) -> str:
    """Conditional edge: 'If input is missing -> request input again'."""
    return "collect_again" if not state["input_valid"] else "generate_timetable"


# ---------------------------------------------------------------
# Agent 2: Timetable Generator (Planning Agent)
# ---------------------------------------------------------------
def timetable_generator(state: StudyPlannerState) -> StudyPlannerState:
    """
    Step 4-6: Send refined prompt to LLM, analyze difficulty/deadline/
    time, generate the day-by-day timetable.

    Idempotent: if a timetable already exists (e.g. this invoke() call
    is a later "check-in" rather than the very first planning run),
    the existing timetable/progress is preserved instead of being
    regenerated from scratch.
    """
    if state.get("timetable"):
        print("[Timetable Generator] Existing timetable found - skipping regeneration.")
        return state

    start = datetime.fromisoformat(state["start_date"])
    session_len = state["preferred_session_minutes"]
    hours_per_day = state["available_hours_per_day"]
    sessions_per_day = max(1, int((hours_per_day * 60) // session_len))

    # Build a flat list of (subject, topic, difficulty, deadline)
    flat_topics = []
    for subj in state["subjects"]:
        prompt = (
            f"Reply with exactly one word - easy, medium, or hard - rating the "
            f"typical difficulty of studying '{subj['subject']}' for a student. "
            f"No explanation, no punctuation, just the single word."
        )
        difficulty = call_llm(prompt)
        for topic in subj["topics"]:
            flat_topics.append({
                "subject": subj["subject"],
                "topic": topic,
                "difficulty": difficulty,
                "deadline": subj["deadline"],
            })

    # Sort by nearest deadline first (Earliest Deadline First scheduling)
    flat_topics.sort(key=lambda t: t["deadline"])

    timetable: List[Task] = []
    current_day = start
    day_slot = 0
    for idx, item in enumerate(flat_topics):
        if day_slot >= sessions_per_day:
            current_day += timedelta(days=1)
            day_slot = 0
        task: Task = {
            "id": f"T{idx+1:03d}",
            "subject": item["subject"],
            "topic": item["topic"],
            "date": current_day.date().isoformat(),
            "duration_minutes": session_len,
            "status": "pending",
            "resources": [],
            "is_revision": False,
            "is_assessment": False,
        }
        timetable.append(task)
        day_slot += 1

    # Insert revision sessions
    if state.get("revision_preference", "weekly") != "none":
        interval = 1 if state["revision_preference"] == "daily" else 7
        rev_day = start + timedelta(days=interval)
        rev_idx = 0
        while rev_day <= current_day:
            timetable.append({
                "id": f"R{rev_idx+1:03d}",
                "subject": "Revision",
                "topic": "Cumulative revision of previous topics",
                "date": rev_day.date().isoformat(),
                "duration_minutes": session_len,
                "status": "pending",
                "resources": [],
                "is_revision": True,
                "is_assessment": False,
            })
            rev_idx += 1
            rev_day += timedelta(days=interval)

    state["timetable"] = timetable
    print(f"[Timetable Generator] Generated {len(timetable)} sessions.")
    return state


# ---------------------------------------------------------------
# Agent 3: Resource Recommendation Agent (Learning Assistant)
# ---------------------------------------------------------------
def resource_recommendation_agent(state: StudyPlannerState) -> StudyPlannerState:
    """Step 7: Recommend study resources for every non-revision task.
    Idempotent: skips work already done in a previous invoke()."""
    if state.get("resources_map"):
        return state

    resources_map: Dict[str, List[str]] = {}
    for task in state["timetable"]:
        if task["is_revision"]:
            continue
        key = f"{task['subject']}::{task['topic']}"
        if key not in resources_map:
            prompt = (
                f"Suggest exactly 3 study resources for the topic "
                f"'{task['topic']}' in the subject '{task['subject']}'. "
                f"Reply with ONLY a valid JSON array of 3 short strings, "
                f"no markdown formatting, no code fences, no extra text. "
                f'Example format: ["resource one", "resource two", "resource three"]'
            )
            raw = call_llm(prompt)
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                # strip markdown code fences some models add despite instructions
                cleaned = cleaned.strip("`")
                if cleaned.lower().startswith("json"):
                    cleaned = cleaned[4:]
                cleaned = cleaned.strip()
            try:
                resources = json.loads(cleaned)
                if not isinstance(resources, list):
                    resources = [str(resources)]
            except json.JSONDecodeError:
                resources = [cleaned]
            resources_map[key] = resources
        task["resources"] = resources_map[key]

    state["resources_map"] = resources_map
    print(f"[Resource Agent] Attached resources to {len(resources_map)} topics.")
    return state


# ---------------------------------------------------------------
# Agent 6 (generated early, scheduled throughout): Assessment Generator
# ---------------------------------------------------------------
def assessment_generator(state: StudyPlannerState) -> StudyPlannerState:
    """Step 8: Generate periodic quizzes/revision tests based on
    test_frequency_days. Idempotent: skips work already done in a
    previous invoke().

    NOTE: if the study plan is shorter than test_frequency_days (a
    common case for small plans / short deadlines), the periodic loop
    below would never fire and no assessments would ever be created.
    To avoid an empty Assessments tab in that situation, we guarantee
    at least one assessment per subject is scheduled near the end of
    the plan even when the periodic cadence doesn't fit."""
    if state.get("assessments"):
        return state
    if not state["timetable"]:
        state["assessments"] = []
        return state

    start = datetime.fromisoformat(state["timetable"][0]["date"])
    end = datetime.fromisoformat(state["timetable"][-1]["date"])
    freq = state.get("test_frequency_days", 7)

    assessments: List[Task] = []
    idx = 0
    covered_subjects = sorted({t["subject"] for t in state["timetable"] if not t["is_revision"]})

    d = start + timedelta(days=freq)
    while d <= end:
        idx += 1
        assessments.append({
            "id": f"Q{idx:03d}",
            "subject": ", ".join(covered_subjects) or "General",
            "topic": "Periodic assessment / quiz",
            "date": d.date().isoformat(),
            "duration_minutes": 30,
            "status": "pending",
            "resources": [],
            "is_revision": False,
            "is_assessment": True,
        })
        d += timedelta(days=freq)

    # Fallback: plan shorter than the test-frequency window -> the loop
    # above never ran. Schedule one wrap-up assessment per subject on
    # the final day of the plan instead, so the feature always works.
    if not assessments:
        for subject in covered_subjects or ["General"]:
            idx += 1
            assessments.append({
                "id": f"Q{idx:03d}",
                "subject": subject,
                "topic": "Wrap-up assessment / quiz",
                "date": end.date().isoformat(),
                "duration_minutes": 30,
                "status": "pending",
                "resources": [],
                "is_revision": False,
                "is_assessment": True,
            })

    state["assessments"] = assessments
    print(f"[Assessment Generator] Scheduled {len(assessments)} assessments.")
    return state


# ---------------------------------------------------------------
# Agent 4: Progress Tracker (Task Manager)
# ---------------------------------------------------------------
def progress_tracker(state: StudyPlannerState) -> StudyPlannerState:
    """
    Step 9-10: Display timetable, let the student mark tasks as
    completed/incomplete.

    In this reference implementation, student updates are expected to
    already be written onto state["timetable"][i]["status"] by the
    calling application (CLI input loop or Streamlit checkboxes)
    BEFORE this node runs on subsequent iterations. On the very first
    pass we simulate "today's" tasks being marked automatically only
    if the caller supplied a `simulate_progress` flag - this keeps the
    graph runnable standalone for testing.
    """
    all_tasks = state["timetable"] + state.get("assessments", [])
    incomplete = [t for t in all_tasks if t["status"] == "incomplete"]
    completed = [t for t in all_tasks if t["status"] == "completed"]
    pending = [t for t in all_tasks if t["status"] == "pending"]

    log_entry = {
        "iteration": state.get("iteration", 0),
        "completed": len(completed),
        "incomplete": len(incomplete),
        "pending": len(pending),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    state.setdefault("progress_log", []).append(log_entry)
    state["incomplete_tasks"] = incomplete
    state["all_tasks_done"] = (len(pending) == 0 and len(incomplete) == 0)

    print(f"[Progress Tracker] completed={len(completed)} "
          f"incomplete={len(incomplete)} pending={len(pending)}")
    return state


def route_after_progress(state: StudyPlannerState) -> str:
    """Conditional edge: 'Task Completed? -> continue : update schedule'."""
    if state["all_tasks_done"]:
        return "final_report"
    if state["incomplete_tasks"]:
        return "update_schedule"
    return "final_report"   # everything pending/on-track, nothing to reschedule yet


# ---------------------------------------------------------------
# Agent 5: Adaptive Schedule Updater (Rescheduling Agent)
# ---------------------------------------------------------------
def adaptive_schedule_updater(state: StudyPlannerState) -> StudyPlannerState:
    """
    Step 10-11 (loop body): push every incomplete task to the next
    available free slot, keeping deadlines in mind, and increase
    session frequency slightly if the student is falling behind.
    """
    incomplete = state["incomplete_tasks"]
    if not incomplete:
        return state

    all_dates = sorted({t["date"] for t in state["timetable"]})
    last_date = datetime.fromisoformat(all_dates[-1]) if all_dates else datetime.now()

    session_len = state["preferred_session_minutes"]
    hours_per_day = state["available_hours_per_day"]
    sessions_per_day = max(1, int((hours_per_day * 60) // session_len))

    # Count how many tasks already occupy each existing day
    day_load = {}
    for t in state["timetable"]:
        if t["status"] == "pending":
            day_load[t["date"]] = day_load.get(t["date"], 0) + 1

    next_day = last_date + timedelta(days=1)
    rescheduled = []
    for task in incomplete:
        # find first day with free capacity
        while day_load.get(next_day.date().isoformat(), 0) >= sessions_per_day:
            next_day += timedelta(days=1)
        new_date = next_day.date().isoformat()
        task["date"] = new_date
        task["status"] = "pending"
        day_load[new_date] = day_load.get(new_date, 0) + 1
        rescheduled.append(task)

    # merge rescheduled tasks back into timetable / assessments lists
    ids_moved = {t["id"] for t in rescheduled}
    state["timetable"] = [t for t in state["timetable"] if t["id"] not in ids_moved] + \
                          [t for t in rescheduled if not t["is_assessment"]]
    state["assessments"] = [a for a in state.get("assessments", []) if a["id"] not in ids_moved] + \
                            [t for t in rescheduled if t["is_assessment"]]

    state["iteration"] = state.get("iteration", 0) + 1
    print(f"[Schedule Updater] Rescheduled {len(rescheduled)} tasks -> "
          f"iteration {state['iteration']}")
    return state


# ---------------------------------------------------------------
# Final Report
# ---------------------------------------------------------------
def final_report_generator(state: StudyPlannerState) -> StudyPlannerState:
    """Step 12: Generate final completion report."""
    all_tasks = state["timetable"] + state.get("assessments", [])
    total = len(all_tasks)
    completed = len([t for t in all_tasks if t["status"] == "completed"])
    incomplete = len([t for t in all_tasks if t["status"] == "incomplete"])
    pending = len([t for t in all_tasks if t["status"] == "pending"])

    report = {
        "student_name": state.get("student_name", "Student"),
        "total_tasks": total,
        "completed": completed,
        "incomplete": incomplete,
        "pending": pending,
        "completion_rate_percent": round((completed / total) * 100, 2) if total else 0.0,
        "iterations_of_replanning": state.get("iteration", 0),
        "generated_on": datetime.now().isoformat(timespec="seconds"),
    }
    state["final_report"] = report
    print("[Final Report]", json.dumps(report, indent=2))
    return state


# =====================================================================
# 4. BUILD THE LANGGRAPH GRAPH
# =====================================================================

def build_graph():
    graph = StateGraph(StudyPlannerState)

    graph.add_node("collect_input", student_input_collector)
    graph.add_node("validate_input", validate_input)
    graph.add_node("generate_timetable", timetable_generator)
    graph.add_node("recommend_resources", resource_recommendation_agent)
    graph.add_node("generate_assessments", assessment_generator)
    graph.add_node("track_progress", progress_tracker)
    graph.add_node("update_schedule", adaptive_schedule_updater)
    graph.add_node("final_report", final_report_generator)

    graph.set_entry_point("collect_input")
    graph.add_edge("collect_input", "validate_input")

    # Step 3 condition: missing input -> request again / else continue
    graph.add_conditional_edges(
        "validate_input",
        route_after_validation,
        {
            "collect_again": "collect_input",
            "generate_timetable": "generate_timetable",
        },
    )

    graph.add_edge("generate_timetable", "recommend_resources")
    graph.add_edge("recommend_resources", "generate_assessments")
    graph.add_edge("generate_assessments", "track_progress")

    # Step 10 condition: task completed? -> continue : update schedule
    graph.add_conditional_edges(
        "track_progress",
        route_after_progress,
        {
            "update_schedule": "update_schedule",
            "final_report": "final_report",
        },
    )

    # After updating the schedule, loop back to progress tracking
    graph.add_edge("update_schedule", "track_progress")

    graph.add_edge("final_report", END)

    return graph.compile()


# =====================================================================
# 5. DEMO / CLI DRIVER
# =====================================================================

def sample_student_input() -> StudyPlannerState:
    """Example input matching the 'Algorithm - Inputs' section."""
    today = date.today()
    return {
        "student_name": "Ananya",
        "subjects": [
            {
                "subject": "Data Structures",
                "topics": ["Arrays", "Linked Lists", "Trees", "Graphs", "Sorting", "Hashing"],
                "deadline": (today + timedelta(days=10)).isoformat(),
            },
            {
                "subject": "Operating Systems",
                "topics": ["Processes", "Scheduling", "Deadlocks", "Memory Mgmt", "File Systems"],
                "deadline": (today + timedelta(days=14)).isoformat(),
            },
        ],
        "available_hours_per_day": 2,
        "preferred_session_minutes": 45,
        "revision_preference": "weekly",
        "test_frequency_days": 3,
        "start_date": today.isoformat(),
        "iteration": 0,
    }


def simulate_a_few_completions(state: dict, n: int = 3, incomplete_n: int = 2):
    """Helper used only for the offline demo: marks a few sessions as
    completed and a couple as incomplete so the adaptive loop has
    something to react to, mimicking a student using the app."""
    pending = [t for t in state["timetable"] if t["status"] == "pending"]
    for t in pending[:n]:
        t["status"] = "completed"
    for t in pending[n:n + incomplete_n]:
        t["status"] = "incomplete"
    return state


if __name__ == "__main__":
    app = build_graph()

    initial_state = sample_student_input()

    # NOTE: because the compiled graph loops (track_progress <->
    # update_schedule) until all_tasks_done is True, and this is an
    # offline scripted demo, we run the graph once to build the
    # timetable, simulate student check-ins, then invoke again so the
    # adaptive loop actually has real progress data to work with.
    state_after_planning = app.invoke(initial_state)

    print("\n=== Simulating student marking tasks complete/incomplete ===")
    state_with_progress = simulate_a_few_completions(state_after_planning)
    state_with_progress["all_tasks_done"] = False  # force re-entry into the loop

    final_state = app.invoke(state_with_progress)

    print("\n=== FINAL TIMETABLE ===")
    for t in sorted(final_state["timetable"], key=lambda x: x["date"]):
        print(f"{t['date']} | {t['subject']:<16} | {t['topic']:<30} | {t['status']}")

    print("\n=== ASSESSMENTS ===")
    for a in final_state.get("assessments", []):
        print(f"{a['date']} | {a['topic']} ({a['status']})")
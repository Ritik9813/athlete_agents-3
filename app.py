"""Athlete AI Team - five lanes, five specialists. Run: streamlit run app.py"""
import json
import os
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import exports
import storage
import tools as T
from agents import (AGENT_MAP, AGENTS, captain_stream, generate_weekly_plan, get_llm,
                    route_question, run_team, stream_agent)
from styles import CSS

load_dotenv()

# Streamlit >= 1.50 uses width="stretch"; older versions use use_container_width=True.
_ver = tuple(int(p) for p in st.__version__.split(".")[:2] if p.isdigit())
STRETCH = {"width": "stretch"} if _ver >= (1, 50) else {"use_container_width": True}

st.set_page_config(page_title="Athlete AI Team", page_icon="🏅", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
from agents import AGENTS as _A
st.markdown("<style>" + "".join(f".c-{a.key}{{--c:{a.color}}}" for a in _A) + "</style>",
            unsafe_allow_html=True)

SPORTS = ["Running", "Football", "Cricket", "Basketball", "Swimming", "Sprinting", "Weightlifting",
          "Kabaddi", "Badminton", "Tennis", "Cycling", "Other"]
LEVELS = ["Beginner", "Intermediate", "Advanced", "Elite"]
DIETS = ["No restriction", "Vegetarian", "Vegan", "Eggetarian", "Non-vegetarian"]
LANGS = ["English", "Hindi", "Punjabi", "Hinglish", "Spanish", "French", "German", "Arabic"]
MODELS = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]
IMG_TYPES = ["png", "jpg", "jpeg", "webp"]

DEFAULTS = dict(name="Alex", age=22, gender="Male", height=175, weight=70, sport="Running",
                level="Intermediate", goal="Improve speed and stamina for the upcoming season", days=5,
                diet="No restriction", injuries="None", allergies="None", language="English")
for k, v in DEFAULTS.items():
    st.session_state.setdefault(f"p_{k}", v)


def load_profile_cb():
    sel = st.session_state.get("load_sel")
    if sel and sel != "-":
        for k, v in storage.load_profile(sel).items():
            if k in DEFAULTS:
                st.session_state[f"p_{k}"] = v


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.subheader("Connection")
    api_key = st.text_input("Google API key", value=os.getenv("GOOGLE_API_KEY", ""), type="password",
                            help="Free key: https://aistudio.google.com/apikey")
    model = st.selectbox("Gemini model", MODELS)
    temperature = st.slider("Creativity", 0.0, 1.0, 0.5, 0.05)

    st.subheader("Athlete")
    st.text_input("Name", key="p_name")
    c1, c2 = st.columns(2)
    c1.number_input("Age", 10, 70, key="p_age")
    c2.selectbox("Gender", ["Male", "Female", "Other"], key="p_gender")
    c3, c4 = st.columns(2)
    c3.number_input("Height (cm)", 120, 230, key="p_height")
    c4.number_input("Weight (kg)", 30, 200, key="p_weight")
    st.selectbox("Sport", SPORTS, key="p_sport")
    st.select_slider("Level", LEVELS, key="p_level")
    st.text_area("Main goal", key="p_goal")
    st.slider("Training days per week", 1, 7, key="p_days")
    st.selectbox("Diet", DIETS, key="p_diet")
    st.text_input("Injuries or limits", key="p_injuries")
    st.text_input("Food allergies", key="p_allergies")
    st.selectbox("Reply language", LANGS, key="p_language")

    st.subheader("Saved profiles")
    st.selectbox("Load a profile", ["-", *storage.list_profiles()], key="load_sel", on_change=load_profile_cb)
    if st.button("Save this profile", **STRETCH):
        storage.save_profile(st.session_state.p_name, {k: st.session_state[f"p_{k}"] for k in DEFAULTS})
        st.toast("Profile saved")

S = st.session_state
name = S.p_name.strip() or "Athlete"
profile = {"Name": name, "Age": S.p_age, "Gender": S.p_gender, "Height": f"{S.p_height} cm",
           "Weight": f"{S.p_weight} kg", "Sport": S.p_sport, "Level": S.p_level, "Goal": S.p_goal,
           "Training days per week": S.p_days, "Diet": S.p_diet, "Injuries": S.p_injuries,
           "Allergies": S.p_allergies, "Reply language": S.p_language}
bmi_val = S.p_weight / ((S.p_height / 100) ** 2)
results = S.get("results")


def extra_tools(key: str) -> list:
    return [storage.make_progress_tool(name)] if key == "analyst" else []


def show_tools(used: list):
    if used:
        with st.expander(f"Tools used ({len(used)})"):
            for u in used:
                st.markdown(f'<span class="tool">{u["tool"]}</span>', unsafe_allow_html=True)
                st.json({"input": u["args"], "output": u["result"]}, expanded=False)


def banner(a):
    st.markdown(f'<div class="rh c-{a.key}"><span class="ic">{a.icon}</span>'
                f"<div><b>{a.name}</b><small>{a.tagline}</small></div></div>", unsafe_allow_html=True)


# ------------------------------------------------------------------ hero
lanes = "".join(
    f'<div class="lane c-{a.key} {"done" if results else ""}"><span class="n">{i}</span>'
    f'<span class="ic">{a.icon}</span><span class="t"><b>{a.name}</b><small>{a.tagline}</small></span>'
    f'<span class="s">{"Plan ready" if results else "On the blocks"}</span></div>'
    for i, a in enumerate(AGENTS, 1))
st.markdown(f"""
<div class="hero"><div><h1>ATHLETE<br>AI TEAM</h1>
<p>Five specialists plan training, food, recovery, mindset and progress for {name}.</p>
<div class="chips"><span class="chip">{S.p_sport}</span><span class="chip">{S.p_level}</span>
<span class="chip">{S.p_days} days a week</span><span class="chip">BMI {bmi_val:.1f}</span></div></div>
<div class="lanes">{lanes}</div></div>""", unsafe_allow_html=True)
st.write("")

if not api_key:
    st.info("Add your Google API key in the sidebar to start the team.")
    st.stop()

llm = get_llm(api_key, model, temperature)
tabs = st.tabs(["Team plan", "Weekly schedule", "Ask the team", "One-on-one", "Progress", "Calculators"])

# ------------------------------------------------------------------ 1. team plan
with tabs[0]:
    if st.button(f"Build {name}'s plan with all 5 agents", type="primary", **STRETCH):
        with st.spinner("All five lanes are running in parallel..."):
            try:
                S.results = run_team(llm, profile, extra={"analyst": extra_tools("analyst")})
                S.pop("brief", None)
                st.rerun()
            except Exception as e:
                st.error(f"The team could not finish: {e}. Check your API key and model, then try again.")
    if results:
        for t, a in zip(st.tabs([f"{a.icon} {a.name}" for a in AGENTS]), AGENTS):
            with t:
                banner(a)
                st.markdown(results[a.key]["text"])
                show_tools(results[a.key]["used"])
        st.divider()
        if st.button("Write the one-page team brief", **STRETCH):
            S.brief = st.write_stream(captain_stream(
                llm, "Write the team's one-page brief: top 5 priorities, the week at a glance, and red flags.",
                {a.name: results[a.key]["text"] for a in AGENTS}, profile))
        elif S.get("brief"):
            st.markdown(S.brief)
        st.download_button("Download full report (.md)", exports.report_markdown(name, AGENTS, results, S.get("brief", "")),
                           file_name=f"{name}_plan.md", **STRETCH)
    else:
        st.caption("Fill in the athlete on the left, then start the team.")

# ------------------------------------------------------------------ 2. weekly schedule
with tabs[1]:
    st.caption("The Training Coach returns a structured week you can chart and add to your calendar.")
    if st.button("Generate weekly schedule", type="primary", **STRETCH):
        with st.spinner("Coach is planning the week..."):
            try:
                S.plan = generate_weekly_plan(llm, profile)
            except Exception as e:
                st.error(f"Could not build the schedule: {e}. Try again or switch model.")
    plan = S.get("plan")
    if plan:
        st.markdown(plan["summary"])
        icon = {"Rest": "😴", "Low": "🟢", "Medium": "🟡", "High": "🔴"}
        df = pd.DataFrame([{"Day": s["day"], "Focus": s["focus"],
                            "Intensity": f'{icon[s["intensity"]]} {s["intensity"]}',
                            "Minutes": s["duration_min"]} for s in plan["sessions"]])
        left, right = st.columns([3, 2])
        left.dataframe(df, hide_index=True, **STRETCH)
        right.bar_chart(df.set_index("Day")["Minutes"])
        for s in plan["sessions"]:
            with st.expander(f'{s["day"]}: {s["focus"]} ({s["duration_min"]} min)'):
                st.markdown(f"**Warm-up:** {s['warmup']}")
                st.markdown("**Main work**\n" + "\n".join(f"- {m}" for m in s["main_work"]))
                st.markdown(f"**Cool-down:** {s['cooldown']}")
        start = date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)
        d1, d2 = st.columns(2)
        d1.download_button(f"Add to calendar (.ics, week of {start:%d %b})", exports.plan_to_ics(plan, start),
                           file_name="training_week.ics", mime="text/calendar", **STRETCH)
        d2.download_button("Download as JSON", json.dumps(plan, indent=2),
                           file_name="training_week.json", **STRETCH)

# ------------------------------------------------------------------ 3. ask the team
with tabs[2]:
    st.caption("Ask anything. The Team Captain picks the right specialists, they answer in parallel, "
               "then the Captain merges their advice.")
    q = st.text_area("Your question", placeholder="I have a 10K in 6 weeks and my left knee aches after long runs...")
    photo = st.file_uploader("Optional photo (meal, exercise form)", type=IMG_TYPES, key="ask_img")
    if st.button("Ask the team", type="primary", **STRETCH) and q.strip():
        images = [(photo.type, photo.getvalue())] if photo else None
        try:
            with st.status("Team Captain is choosing specialists...", expanded=True) as status:
                decision = route_question(llm, q, profile)
                chosen = [k for k in decision.agents if k in AGENT_MAP] or ["coach"]
                st.markdown("".join(f'<span class="pick c-{k}">{AGENT_MAP[k].icon} '
                                    f"{AGENT_MAP[k].name}</span>" for k in chosen), unsafe_allow_html=True)
                st.caption(decision.reason)
                status.update(label="Specialists are answering...")
                answers = run_team(llm, profile, chosen, q, images, {"analyst": extra_tools("analyst")})
                status.update(label="Specialists finished", state="complete", expanded=False)
            for k in chosen:
                with st.expander(f"{AGENT_MAP[k].icon} {AGENT_MAP[k].name}"):
                    st.markdown(answers[k]["text"])
                    show_tools(answers[k]["used"])
            st.subheader("Captain's answer")
            S.ask_final = st.write_stream(captain_stream(
                llm, q, {AGENT_MAP[k].name: answers[k]["text"] for k in chosen}, profile))
        except Exception as e:
            st.error(f"The team could not answer: {e}. Check your API key and try again.")

# ------------------------------------------------------------------ 4. one-on-one
with tabs[3]:
    key = st.radio("Agent", [a.key for a in AGENTS], horizontal=True, label_visibility="collapsed",
                   format_func=lambda k: f"{AGENT_MAP[k].icon} {AGENT_MAP[k].name}")
    agent = AGENT_MAP[key]
    chats = S.setdefault("chats", {})
    history = chats.setdefault(key, [])
    banner(agent)
    hint = {"nutrition": "Attach a meal photo and ask for a calorie estimate.",
            "coach": "Attach a photo of your exercise form for feedback."}.get(key, "")
    if history and st.button("Clear this chat"):
        chats[key] = []
        st.rerun()
    if not history:
        st.caption(f"Ask the {agent.name.lower()} anything. {hint}")
    for role, text in history:
        with st.chat_message(role, avatar=agent.icon if role == "assistant" else None):
            st.markdown(text)
    msg = st.chat_input(f"Message the {agent.name}", accept_file=True, file_type=IMG_TYPES)
    if msg:
        text = msg.text or "Please look at the attached photo."
        images = [(f.type, f.getvalue()) for f in msg.files]
        with st.chat_message("user"):
            st.markdown(text)
            for f in msg.files:
                st.image(f, width=220)
        with st.chat_message("assistant", avatar=agent.icon):
            used = []
            try:
                answer = st.write_stream(stream_agent(llm, agent, profile, history, text, images,
                                                      extra_tools(key), used))
                history += [("user", text + (" [photo attached]" if images else "")), ("assistant", answer)]
                show_tools(used)
            except Exception as e:
                st.error(f"No reply: {e}. Check your API key and try again.")

# ------------------------------------------------------------------ 5. progress
with tabs[4]:
    logs = storage.get_logs(name)
    top = st.columns(4)
    if logs:
        df = pd.DataFrame(logs)
        df["day"] = pd.to_datetime(df["day"])
        wk = df[df["day"] >= pd.Timestamp.today() - pd.Timedelta(days=7)]
        top[0].metric("Latest weight", f'{df.iloc[-1]["weight_kg"]:.1f} kg')
        top[1].metric("Avg sleep (7d)", f'{wk["sleep_h"].mean():.1f} h' if len(wk) else "-")
        top[2].metric("Avg readiness (7d)", f'{wk["readiness"].mean():.0f}/100' if len(wk) else "-")
        top[3].metric("Training (7d)", f'{int(wk["workout_min"].sum())} min' if len(wk) else "-")
        c1, c2 = st.columns(2)
        c1.caption("Weight (kg)")
        c1.line_chart(df.set_index("day")["weight_kg"])
        c2.caption("Readiness score")
        c2.line_chart(df.set_index("day")["readiness"])
        c3, c4 = st.columns(2)
        c3.caption("Sleep (hours)")
        c3.bar_chart(df.set_index("day")["sleep_h"])
        c4.caption("Training minutes")
        c4.bar_chart(df.set_index("day")["workout_min"])
    else:
        st.info("No entries yet. Log today below, or load demo data to see the charts.")

    with st.expander("Log today", expanded=not logs):
        with st.form("log_form", clear_on_submit=True):
            a, b, c = st.columns(3)
            d = a.date_input("Date", date.today())
            w = b.number_input("Weight (kg)", 30.0, 200.0, float(S.p_weight), 0.1)
            sl = c.number_input("Sleep (hours)", 0.0, 14.0, 7.5, 0.5)
            a, b, c, e = st.columns(4)
            hr = a.number_input("Resting HR", 30, 120, 58)
            wm = b.number_input("Workout (min)", 0, 300, 60, 5)
            rpe = c.slider("Effort (RPE 1-10)", 1, 10, 6)
            mood = e.slider("Mood (1-5)", 1, 5, 4)
            notes = st.text_input("Notes")
            if st.form_submit_button("Save entry", type="primary"):
                storage.add_log(name, d, w, sl, hr, wm, rpe, mood, notes)
                st.rerun()
    b1, b2, b3 = st.columns(3)
    if b1.button("Load 14 days of demo data", **STRETCH):
        storage.add_demo_data(name)
        st.rerun()
    if b2.button("Clear this athlete's log", **STRETCH):
        storage.clear_logs(name)
        st.rerun()
    if b3.button("Ask the Analyst to review my log", type="primary", **STRETCH):
        used = []
        with st.chat_message("assistant", avatar=AGENT_MAP["analyst"].icon):
            st.write_stream(stream_agent(
                llm, AGENT_MAP["analyst"], profile, [],
                "Review my logged data for the last 14 days: trends, red flags, and three changes to make next week.",
                None, extra_tools("analyst"), used))
            show_tools(used)

# ------------------------------------------------------------------ 6. calculators
with tabs[5]:
    st.caption("The same tools the agents call, available directly.")
    l, r = st.columns(2)
    with l.container(border=True):
        st.markdown("**Calories and macros**")
        act = st.selectbox("Activity", list(T.ACTIVITY), index=2, key="c_act")
        goal = st.selectbox("Goal", ["lose", "maintain", "gain"], index=1, key="c_goal")
        o = T.calorie_needs.invoke({"weight_kg": S.p_weight, "height_cm": S.p_height, "age": S.p_age,
                                    "gender": "female" if S.p_gender == "Female" else "male",
                                    "activity": act, "goal": goal})
        m = st.columns(4)
        for col, (lbl, k) in zip(m, [("Target kcal", "target_kcal"), ("Protein g", "protein_g"),
                                     ("Carbs g", "carbs_g"), ("Fat g", "fat_g")]):
            col.metric(lbl, o[k])
    with r.container(border=True):
        st.markdown("**Heart-rate zones**")
        rhr = st.number_input("Resting heart rate", 30, 120, 60, key="c_rhr")
        o = T.heart_rate_zones.invoke({"age": S.p_age, "resting_hr": rhr})
        st.dataframe(pd.DataFrame(o["zones"]), hide_index=True, **STRETCH)
        st.caption(f'Estimated max heart rate: {o["max_hr"]} bpm')
    l, r = st.columns(2)
    with l.container(border=True):
        st.markdown("**One-rep max**")
        x1, x2 = st.columns(2)
        lw = x1.number_input("Weight lifted (kg)", 1.0, 500.0, 80.0, 2.5, key="c_lw")
        lr = x2.number_input("Reps", 1, 20, 5, key="c_lr")
        o = T.one_rep_max.invoke({"weight_kg": lw, "reps": lr})
        st.metric("Estimated 1RM", f'{o["one_rep_max_kg"]} kg')
        st.dataframe(pd.DataFrame(o["percentages_kg"].items(), columns=["Percent", "kg"]),
                     hide_index=True, **STRETCH)
    with r.container(border=True):
        st.markdown("**Race pace and predictions**")
        x1, x2 = st.columns(2)
        dist = x1.number_input("Distance (km)", 0.5, 100.0, 5.0, 0.5, key="c_dist")
        mins = x2.number_input("Time (minutes)", 1.0, 600.0, 25.0, 0.5, key="c_min")
        o = T.race_pace.invoke({"distance_km": dist, "time_minutes": mins})
        y1, y2 = st.columns(2)
        y1.metric("Pace per km", o["pace_per_km"])
        y2.metric("Speed", f'{o["speed_kmh"]} km/h')
        st.dataframe(pd.DataFrame(o["predictions"].items(), columns=["Race", "Predicted"]),
                     hide_index=True, **STRETCH)

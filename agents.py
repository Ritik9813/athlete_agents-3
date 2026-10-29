"""Five specialist agents + Team Captain, built with LangChain and Google Gemini.

Features: tool calling, streaming, image input, parallel runs, routing, structured output.
"""
import base64
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Iterator, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

import tools as T
from schemas import RouteDecision, WeeklyPlan

BASE_RULES = (
    "You belong to an AI sports-support team. Be specific, practical and encouraging. Use markdown "
    "with short sections. Never diagnose: for sharp pain, dizziness, chest symptoms or an injury that "
    "does not settle, tell the athlete to see a doctor. Use your tools for any calculation instead of "
    "guessing numbers. Reply in the language named under 'Reply language' in the profile."
)


@dataclass(frozen=True)
class Agent:
    key: str
    name: str
    icon: str
    color: str
    tagline: str
    system: str
    task: str
    tool_names: tuple = ()


AGENTS: list[Agent] = [
    Agent("coach", "Training Coach", "🏋️", "#E4572E", "Builds your weekly training plan",
          "You are an elite strength and conditioning coach. Design safe, progressive, sport-specific "
          "training with exercises, sets, reps, intensity and rest. You can analyse exercise-form photos.",
          "Create a 7-day training plan, day by day, matched to the athlete's sport, level, goal and "
          "training days. Include heart-rate zones for the cardio work.",
          ("heart_rate_zones", "one_rep_max", "race_pace")),
    Agent("nutrition", "Nutritionist", "🥗", "#2A9D8F", "Fuels performance with smart meals",
          "You are a certified sports nutritionist. Give practical meals, macros, hydration and "
          "supplement guidance. Respect diet and allergies. You can estimate calories from meal photos.",
          "Create a one-day sample meal plan (pre-workout, post-workout, meals, snacks) with calorie and "
          "macro targets and hydration advice.",
          ("calorie_needs", "bmi")),
    Agent("recovery", "Recovery & Injury Specialist", "🩺", "#3A6FF0", "Keeps you healthy and recovering",
          "You are a sports physiotherapist focused on injury prevention, mobility, sleep and recovery. "
          "Always consider the injury history.",
          "Give a recovery routine: mobility and stretching, sleep targets, injury-prevention drills and "
          "warning signs to watch for.",
          ("heart_rate_zones",)),
    Agent("mind", "Mental Performance Coach", "🧠", "#8E5CE0", "Focus, confidence and motivation",
          "You are a sports psychologist. Teach focus, visualisation, confidence, stress control and habit "
          "building with short, warm, practical exercises.",
          "Give a mental training plan: pre-competition routine, a visualisation script, a breathing drill "
          "and one weekly habit.",
          ()),
    Agent("analyst", "Performance Analyst", "📊", "#E0428A", "Sets KPIs and reads your progress",
          "You are a sports performance data analyst. Define measurable KPIs, benchmarks and testing "
          "schedules. Read the athlete's logged data with get_progress_log before judging progress, and "
          "say clearly when there is not enough data.",
          "Define 5-7 KPIs, how and when to measure them, 8-week targets, and a simple tracking template. "
          "If progress data exists, comment on it.",
          ("bmi", "race_pace", "one_rep_max")),
]
AGENT_MAP = {a.key: a for a in AGENTS}


# ---------------------------------------------------------------- helpers
def get_llm(api_key: str, model: str, temperature: float) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=temperature)


def profile_to_text(p: dict) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in p.items() if v not in (None, ""))


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(c if isinstance(c, str) else c.get("text", "") for c in content
                       if isinstance(c, str) or c.get("type") == "text")
    return ""


def _human(question: str, images: Optional[list] = None) -> HumanMessage:
    if not images:
        return HumanMessage(question)
    parts = [{"type": "text", "text": question}]
    for mime, data in images:
        b64 = base64.b64encode(data).decode()
        parts.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    return HumanMessage(parts)


def to_messages(history):
    return [HumanMessage(c) if r == "user" else AIMessage(c) for r, c in history]


def _system(agent: Agent, profile: dict) -> SystemMessage:
    return SystemMessage(f"{BASE_RULES}\n\n{agent.system}\n\nAthlete profile:\n{profile_to_text(profile)}")


# ---------------------------------------------------------------- agent loop
def stream_agent(llm, agent: Agent, profile: dict, history, question: str, images=None,
                 extra_tools=(), used: Optional[list] = None, max_steps: int = 5) -> Iterator[str]:
    """Stream an agent's answer, running tool calls between model turns.
    Tool calls are appended to `used` as {tool, args, result}."""
    tool_map = {t.name: t for t in [*(T.TOOLS[n] for n in agent.tool_names), *extra_tools]}
    model = llm.bind_tools(list(tool_map.values())) if tool_map else llm
    messages = [_system(agent, profile), *to_messages(history), _human(question, images)]

    for _ in range(max_steps):
        full = None
        for chunk in model.stream(messages):
            full = chunk if full is None else full + chunk
            piece = _text(chunk.content)
            if piece:
                yield piece
        if full is None or not getattr(full, "tool_calls", None):
            return
        messages.append(full)
        for call in full.tool_calls:
            try:
                result = tool_map[call["name"]].invoke(call["args"])
            except Exception as e:  # report tool errors back to the model
                result = {"error": str(e)}
            if used is not None:
                used.append({"tool": call["name"], "args": call["args"], "result": result})
            messages.append(ToolMessage(content=json.dumps(result, default=str), tool_call_id=call["id"]))
    yield "\n\n_(Stopped after the maximum number of tool steps.)_"


def run_agent(llm, agent: Agent, profile: dict, question: str, images=None, extra_tools=()) -> dict:
    used: list = []
    text = "".join(stream_agent(llm, agent, profile, [], question, images, extra_tools, used))
    return {"text": text, "used": used}


def run_team(llm, profile: dict, keys=None, question: Optional[str] = None, images=None,
             extra: Optional[dict] = None) -> dict:
    """Run agents in parallel. With no question each agent does its own default task."""
    chosen = [AGENT_MAP[k] for k in (keys or AGENT_MAP)]
    extra = extra or {}

    def work(a: Agent):
        return a.key, run_agent(llm, a, profile, question or a.task, images, extra.get(a.key, ()))

    with ThreadPoolExecutor(max_workers=len(chosen)) as pool:
        return dict(pool.map(work, chosen))


# ---------------------------------------------------------------- captain / router
def route_question(llm, question: str, profile: dict) -> RouteDecision:
    roster = "\n".join(f"- {a.key}: {a.name} - {a.tagline}" for a in AGENTS)
    msgs = [SystemMessage("You are the Team Captain. Pick the 1-3 specialists best placed to answer "
                          f"the athlete's question.\n{roster}"),
            HumanMessage(f"Profile:\n{profile_to_text(profile)}\n\nQuestion: {question}")]
    return llm.with_structured_output(RouteDecision).invoke(msgs)


CAPTAIN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are the Team Captain of an athlete support team. Merge the specialists' answers into "
               "one clear, well-organised reply. Resolve any conflicts, say who advised what, and end with "
               "a short numbered action list. Reply in the language named under 'Reply language'.\n\n"
               "Athlete profile:\n{profile}"),
    ("human", "Request: {question}\n\nSpecialist answers:\n{answers}"),
])


def captain_stream(llm, question: str, answers: dict, profile: dict) -> Iterator[str]:
    body = "\n\n".join(f"### {name}\n{text}" for name, text in answers.items())
    chain = CAPTAIN_PROMPT | llm | StrOutputParser()
    return chain.stream({"question": question, "answers": body, "profile": profile_to_text(profile)})


# ---------------------------------------------------------------- structured plan
def generate_weekly_plan(llm, profile: dict) -> dict:
    coach = AGENT_MAP["coach"]
    msgs = [_system(coach, profile),
            HumanMessage("Create this athlete's training week as structured data: exactly 7 sessions, "
                         "Monday to Sunday, respecting their training days per week (use Rest for other days).")]
    plan = llm.with_structured_output(WeeklyPlan).invoke(msgs)
    return plan.model_dump()

"""Offline tests: no API key needed. A fake model stands in for Gemini."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessageChunk

import exports
import storage
import tools as T
from agents import AGENT_MAP, run_agent, run_team
from schemas import WeeklyPlan


class FakeLLM:
    """First turn asks for a tool, second turn answers with the tool result in mind."""

    def bind_tools(self, tools):
        return self

    def stream(self, messages):
        if not any(m.type == "tool" for m in messages):
            yield AIMessageChunk(content="", tool_calls=[{"name": "bmi", "args": {"weight_kg": 70, "height_cm": 175}, "id": "1"}])
        else:
            yield AIMessageChunk(content="Your BMI ")
            yield AIMessageChunk(content="is fine.")


def test_calorie_needs():
    o = T.calorie_needs.invoke({"weight_kg": 70, "height_cm": 175, "age": 22, "gender": "male",
                                "activity": "moderate", "goal": "maintain"})
    assert o["bmr"] == 1689 and o["target_kcal"] == o["maintenance_kcal"]


def test_zones_and_orm_and_pace():
    z = T.heart_rate_zones.invoke({"age": 30, "resting_hr": 60})
    assert z["max_hr"] == 187 and len(z["zones"]) == 5
    assert T.one_rep_max.invoke({"weight_kg": 100, "reps": 5})["one_rep_max_kg"] == 116.7
    p = T.race_pace.invoke({"distance_km": 5, "time_minutes": 25})
    assert p["pace_per_km"] == "5:00" and p["predictions"]["10K"].startswith("52")


def test_agent_tool_loop():
    out = run_agent(FakeLLM(), AGENT_MAP["nutrition"], {"Name": "A"}, "hi")
    assert out["text"] == "Your BMI is fine."
    assert out["used"][0]["tool"] == "bmi" and out["used"][0]["result"]["bmi"] == 22.9


def test_run_team_parallel():
    res = run_team(FakeLLM(), {"Name": "A"})
    assert set(res) == {"coach", "nutrition", "recovery", "mind", "analyst"}


def test_storage_and_readiness(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA", tmp_path)
    monkeypatch.setattr(storage, "DB", tmp_path / "t.db")
    monkeypatch.setattr(storage, "PROFILES", tmp_path / "p")
    storage.add_demo_data("Zed", 5)
    assert len(storage.get_logs("Zed")) == 5
    assert storage.readiness(8, 5, 1) == 100
    tool = storage.make_progress_tool("Zed")
    assert tool.invoke({"days": 14})["entries"] == 5
    storage.save_profile("Zed", {"name": "Zed"})
    assert storage.list_profiles() == ["Zed"] and storage.load_profile("Zed")["name"] == "Zed"
    storage.clear_logs("Zed")
    assert storage.get_logs("Zed") == []


def test_ics_export():
    plan = {"summary": "s", "sessions": [
        {"day": "Monday", "focus": "Tempo, run", "intensity": "High", "duration_min": 50,
         "warmup": "jog", "main_work": ["4x1km"], "cooldown": "walk"},
        {"day": "Tuesday", "focus": "Rest", "intensity": "Rest", "duration_min": 0,
         "warmup": "", "main_work": [], "cooldown": ""}]}
    WeeklyPlan(**plan)
    ics = exports.plan_to_ics(plan, date(2026, 10, 5))
    assert ics.count("BEGIN:VEVENT") == 1 and "DTSTART:20261005T060000" in ics and "Tempo\\, run" in ics

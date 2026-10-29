"""Pydantic schemas used for structured (JSON) output from Gemini."""
from typing import Literal

from pydantic import BaseModel, Field

AgentKey = Literal["coach", "nutrition", "recovery", "mind", "analyst"]


class Session(BaseModel):
    day: str = Field(description="Day name, Monday to Sunday")
    focus: str = Field(description="Short title, e.g. 'Tempo run' or 'Rest and mobility'")
    intensity: Literal["Rest", "Low", "Medium", "High"]
    duration_min: int = Field(description="Total minutes, 0 for a full rest day")
    warmup: str
    main_work: list[str] = Field(description="Exercises or drills with sets, reps, distance or time")
    cooldown: str


class WeeklyPlan(BaseModel):
    summary: str = Field(description="Two sentences on the idea behind this week")
    sessions: list[Session] = Field(description="Exactly 7 sessions, Monday to Sunday")


class RouteDecision(BaseModel):
    agents: list[AgentKey] = Field(description="1 to 3 specialists best placed to answer")
    reason: str = Field(description="One sentence on why these specialists were chosen")

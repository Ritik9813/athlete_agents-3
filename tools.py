"""LangChain tools the agents can call for exact numbers instead of guessing."""
from typing import Literal, Optional

from langchain_core.tools import tool

ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "very_active": 1.725, "athlete": 1.9}


def _hms(minutes: float) -> str:
    s = int(round(minutes * 60))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


@tool
def calorie_needs(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: Literal["male", "female"],
    activity: Literal["sedentary", "light", "moderate", "very_active", "athlete"],
    goal: Literal["lose", "maintain", "gain"] = "maintain",
) -> dict:
    """Daily calorie and macro targets (Mifflin-St Jeor). Use for any nutrition numbers."""
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if gender == "male" else -161)
    tdee = bmr * ACTIVITY[activity]
    target = tdee + {"lose": -400, "maintain": 0, "gain": 300}[goal]
    protein = weight_kg * (1.6 if goal == "maintain" else 2.0)
    fat = target * 0.25 / 9
    carbs = (target - protein * 4 - fat * 9) / 4
    return {
        "bmr": round(bmr), "maintenance_kcal": round(tdee), "target_kcal": round(target),
        "protein_g": round(protein), "carbs_g": round(carbs), "fat_g": round(fat),
    }


@tool
def bmi(weight_kg: float, height_cm: float) -> dict:
    """Body mass index, category and the healthy weight range for this height."""
    h = height_cm / 100
    value = weight_kg / h**2
    cat = ("Underweight" if value < 18.5 else "Healthy range" if value < 25
           else "Overweight" if value < 30 else "Obese")
    return {"bmi": round(value, 1), "category": cat,
            "healthy_weight_kg": [round(18.5 * h * h, 1), round(24.9 * h * h, 1)],
            "note": "BMI ignores muscle mass, so muscular athletes can read high."}


@tool
def heart_rate_zones(age: int, resting_hr: int = 60, max_hr: Optional[int] = None) -> dict:
    """Five training heart-rate zones using the Karvonen method."""
    mx = max_hr or round(208 - 0.7 * age)
    reserve = mx - resting_hr
    names = ["Zone 1 Recovery", "Zone 2 Endurance", "Zone 3 Tempo", "Zone 4 Threshold", "Zone 5 VO2 max"]
    edges = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    zones = [{"zone": n, "bpm": f"{round(resting_hr + reserve * edges[i])}-{round(resting_hr + reserve * edges[i + 1])}"}
             for i, n in enumerate(names)]
    return {"max_hr": mx, "resting_hr": resting_hr, "zones": zones}


@tool
def one_rep_max(weight_kg: float, reps: int) -> dict:
    """Estimated one-rep max (Epley) and working weights at common percentages."""
    orm = weight_kg if reps <= 1 else weight_kg * (1 + reps / 30)
    table = {f"{p}%": round(orm * p / 100, 1) for p in (60, 70, 80, 85, 90, 95)}
    return {"one_rep_max_kg": round(orm, 1), "percentages_kg": table}


@tool
def race_pace(distance_km: float, time_minutes: float) -> dict:
    """Pace, speed and predicted times for 5K, 10K, half and full marathon (Riegel formula)."""
    pace = time_minutes / distance_km
    preds = {n: _hms(time_minutes * (d / distance_km) ** 1.06)
             for n, d in [("5K", 5), ("10K", 10), ("Half marathon", 21.0975), ("Marathon", 42.195)]}
    return {"pace_per_km": _hms(pace), "speed_kmh": round(60 / pace, 2), "predictions": preds}


TOOLS = {t.name: t for t in [calorie_needs, bmi, heart_rate_zones, one_rep_max, race_pace]}

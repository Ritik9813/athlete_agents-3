"""Export helpers: Markdown report and calendar (.ics) file."""
from datetime import date, datetime, timedelta


def report_markdown(name: str, agents, results: dict, brief: str = "") -> str:
    out = f"# Athlete plan for {name} ({date.today()})\n\n"
    if brief:
        out += f"## Team brief\n\n{brief}\n\n---\n\n"
    for a in agents:
        if a.key in results:
            out += f"## {a.icon} {a.name}\n\n{results[a.key]['text']}\n\n---\n\n"
    return out


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def plan_to_ics(plan: dict, start: date, hour: int = 6) -> str:
    """One calendar event per non-rest session, starting on `start` (a Monday)."""
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Athlete AI Team//EN"]
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    for i, s in enumerate(plan["sessions"]):
        if s["intensity"] == "Rest" or s["duration_min"] <= 0:
            continue
        begin = datetime.combine(start + timedelta(days=i), datetime.min.time()).replace(hour=hour)
        end = begin + timedelta(minutes=s["duration_min"])
        desc = f"Warm-up: {s['warmup']}\nMain: " + "; ".join(s["main_work"]) + f"\nCool-down: {s['cooldown']}"
        lines += ["BEGIN:VEVENT", f"UID:athlete-{i}-{stamp}@athlete-ai-team", f"DTSTAMP:{stamp}",
                  f"DTSTART:{begin:%Y%m%dT%H%M%S}", f"DTEND:{end:%Y%m%dT%H%M%S}",
                  f"SUMMARY:{_esc(s['focus'] + ' (' + s['intensity'] + ')')}",
                  f"DESCRIPTION:{_esc(desc)}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)

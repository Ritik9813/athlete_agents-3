# Athlete AI Team

Five specialist AI agents for athletes, built with **LangChain + `langchain-google-genai` (Gemini)** and a Streamlit interface.

| Lane | Agent | Tools it can call |
|---|---|---|
| 1 | Training Coach | heart_rate_zones, one_rep_max, race_pace |
| 2 | Nutritionist | calorie_needs, bmi |
| 3 | Recovery & Injury Specialist | heart_rate_zones |
| 4 | Mental Performance Coach | none |
| 5 | Performance Analyst | bmi, race_pace, one_rep_max, get_progress_log |

## Features
- **Team plan**: all 5 agents run in parallel, then the Team Captain writes a one-page brief.
- **Weekly schedule**: structured JSON output rendered as a table and chart; export to calendar (.ics) or JSON.
- **Ask the team**: a router picks 1-3 specialists, they answer in parallel, the Captain merges their advice.
- **One-on-one chat**: streaming replies, per-agent memory, photo input (meal photo for calories, exercise-form photo for the coach).
- **Tool calling**: agents call real calculators instead of guessing numbers; the calls are shown under "Tools used".
- **Progress tracker**: SQLite log of weight, sleep, resting HR, effort and mood, with charts and a readiness score. The Analyst reads this log through a tool.
- **Calculators tab**: calories and macros, heart-rate zones, 1RM, race pace and predictions.
- **Saved profiles**, reply language (English, Hindi, Punjabi, Hinglish and more), Markdown report download.
- Offline tests with a fake model (`pytest`), Dockerfile.

## Run
```bash
pip install -r requirements.txt
cp .env.example .env        # add GOOGLE_API_KEY, or paste it in the sidebar
streamlit run app.py
```
Free API key: https://aistudio.google.com/apikey

Tests (no key needed): `python -m pytest -q tests`

Docker: `docker build -t athlete-ai . && docker run -p 8501:8501 -e GOOGLE_API_KEY=... athlete-ai`

## Files
```
app.py        Streamlit interface (6 tabs)
agents.py     agents, tool-calling loop, router, Captain, structured plan
tools.py      LangChain tools (calculators)
schemas.py    Pydantic schemas for structured output
storage.py    SQLite progress log + profile files
exports.py    Markdown report and .ics calendar
styles.py     CSS theme
tests/        offline tests
```

## Notes
Not medical advice. The agents tell athletes to see a doctor for pain or persistent injury.
The readiness score is a simple heuristic (sleep 40%, mood 30%, effort 30%), not a clinical measure.

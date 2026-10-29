"""Global CSS for the Streamlit app."""
CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@1,800;1,900&family=Barlow:wght@400;500;600&display=swap');
:root{--ink:#0E1B3D;--blue:#1B2A6B;--paper:#EEF2F8;--line:#D5DDEB}
html,body,[class*="css"],.stMarkdown,.stTextInput,.stButton{font-family:'Barlow',sans-serif}
.block-container{padding-top:1.6rem;max-width:1200px}
#MainMenu,footer,header[data-testid="stHeader"]{visibility:hidden;height:0}

/* ---------- hero ---------- */
.hero{display:grid;grid-template-columns:1.05fr 1fr;gap:28px;align-items:center;
 background:#fff;border:1px solid var(--line);border-radius:26px;padding:30px 34px;
 box-shadow:0 18px 40px -28px rgba(27,42,107,.45)}
.hero h1{font-family:'Barlow Condensed',sans-serif;font-style:italic;font-weight:900;
 font-size:4.4rem;line-height:.92;margin:0;color:var(--blue);letter-spacing:-.5px;padding:0}
.hero p{margin:14px 0 18px;font-size:1.08rem;color:#3c4a6e;max-width:30ch}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:var(--paper);border:1px solid var(--line);border-radius:999px;
 padding:5px 13px;font-size:.85rem;font-weight:600;color:var(--blue)}

/* ---------- lanes ---------- */
.lanes{display:flex;flex-direction:column;gap:9px}
.lane{--c:#999;display:flex;align-items:center;gap:12px;padding:9px 14px 9px 9px;
 border-radius:999px 16px 16px 999px;background:
 linear-gradient(90deg,color-mix(in srgb,var(--c) 16%,white),#fff 70%);
 border:1px solid color-mix(in srgb,var(--c) 35%,white)}
.lane .n{width:34px;height:34px;border-radius:50%;background:var(--c);color:#fff;
 display:grid;place-items:center;font-family:'Barlow Condensed';font-style:italic;
 font-weight:900;font-size:1.25rem;flex:none}
.lane .ic{font-size:1.35rem}
.lane .t{flex:1;line-height:1.15}
.lane .t b{display:block;font-size:.98rem;color:var(--ink)}
.lane .t small{color:#5b6888;font-size:.78rem}
.lane .s{font-size:.75rem;font-weight:700;color:var(--c);white-space:nowrap}
.lane.done{background:linear-gradient(90deg,var(--c),color-mix(in srgb,var(--c) 55%,white));
 border-color:var(--c)}
.lane.done .t b,.lane.done .t small,.lane.done .s{color:#fff}
.lane.done .n{background:#fff;color:var(--c)}

/* ---------- result header ---------- */
.rh{display:flex;align-items:center;gap:12px;padding:14px 18px;border-radius:16px;
 background:var(--c);color:#fff;margin:6px 0 14px}
.rh .ic{font-size:1.7rem}
.rh b{font-family:'Barlow Condensed';font-style:italic;font-weight:900;font-size:1.6rem;line-height:1}
.rh small{display:block;opacity:.85}

/* ---------- widgets ---------- */
.stTabs [data-baseweb="tab-list"]{gap:6px;background:#fff;border:1px solid var(--line);
 padding:5px;border-radius:14px}
.stTabs [data-baseweb="tab"]{border-radius:10px;font-weight:600;padding:8px 14px}
.stTabs [aria-selected="true"]{background:var(--blue);color:#fff}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none}
.stButton>button[kind="primary"]{background:var(--blue);border:0;border-radius:14px;
 padding:.85rem 1rem;font-weight:700;font-size:1.05rem;transition:transform .15s}
.stButton>button[kind="primary"]:hover{transform:translateY(-1px);background:#23378a}
.stDownloadButton>button{border-radius:14px;font-weight:600}
[data-testid="stSidebar"]{background:#fff;border-right:1px solid var(--line)}
[data-testid="stChatMessage"]{background:#fff;border:1px solid var(--line);border-radius:16px}
.stTabs [data-baseweb="tab"]:focus-visible,.stButton>button:focus-visible{outline:3px solid #6f86ff}
@media (max-width:860px){.hero{grid-template-columns:1fr;padding:22px}.hero h1{font-size:3.2rem}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}

.tool{display:inline-block;background:var(--paper);border:1px solid var(--line);border-radius:8px;
 padding:2px 9px;margin:2px 4px 2px 0;font-size:.8rem;font-weight:600;color:var(--blue)}
.pick{display:inline-flex;align-items:center;gap:6px;background:var(--c);color:#fff;
 border-radius:999px;padding:5px 14px;font-weight:600;margin:0 6px 6px 0}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px 16px}
</style>"""

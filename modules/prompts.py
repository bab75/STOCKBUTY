# modules/prompts.py · Research Studio
# Pick a stock from the list or a mover button, choose a question, check it on the Prompt Radar,
# then one click copies the full research brief and opens your AI. Paste and submit it in the AI chat.
import csv
import datetime as dt
import html
import io
import json
import re
from urllib.parse import quote

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modules.question_bank import (
    ICON_LEGEND, RULES, LAYOUTS, PROMPTS, get_prompt, build_prompt, build_link,
)

PROMPT_OPTIMIZER_URL = "https://academy.techpresso.co/free-tools/prompt-optimizer"
CATEGORIES = ["Start here", "Company", "Market & trend", "Analysts & investors", "Risk", "Advanced"]
HORIZONS = ["1 month", "3 to 12 months", "1 to 3 years"]
RISKS = ["Low", "Medium", "High"]
LEVEL_ICON = {"Beginner": "🟢", "Intermediate": "🟡", "Advanced": "🔴"}

# name, address prefix, whether the question can be pre-filled in the address, colour
ENGINES = [
    ("ChatGPT", "https://chatgpt.com/?q=", True, "#34d399,#0d9488"),
    ("Claude", "https://claude.ai/new?q=", True, "#fb923c,#ea580c"),
    ("Google AI Mode", "https://www.google.com/search?udm=50&q=", True, "#60a5fa,#2563eb"),
    ("Copilot", "https://copilot.microsoft.com/?q=", True, "#c084fc,#7c3aed"),
    ("Perplexity", "https://www.perplexity.ai/search?q=", True, "#22d3ee,#0891b2"),
    ("Gemini", "https://gemini.google.com/app", False, "#818cf8,#4f46e5"),
    ("Google Search", "https://www.google.com/search?q=", True, "#4ade80,#16a34a"),
]
LINK_LIMIT = 1900


# ------------------------------------------------------------------ helpers
def _price_value(value):
    if value is None:
        return None
    try:
        cleaned = str(value).strip().replace("$", "").replace(",", "").replace("%", "")
        if not cleaned or cleaned.lower() in {"n/a", "na", "none", "nan", "-", "not found"}:
            return None
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def file_snapshot_line(s, file_date):
    pct = "n/a" if s.get("pct") is None else format(s["pct"], "+.2f") + "%"
    return (f"FILE SNAPSHOT (Nasdaq file, {file_date or 'date not in filename'}): last ${s.get('last') or 'n/a'}, "
            f"change {pct}. Treat as a dated reference and verify the live price first.")


def _gsearch(q):
    return "https://www.google.com/search?q=" + quote(q)


def wiki_groups(t, c):
    name = c or t
    return {
        "📰 News": [
            ("Google News", "https://news.google.com/search?q=" + quote(t + " stock"), "Headlines from many outlets."),
            ("Yahoo Finance news", "https://finance.yahoo.com/quote/" + quote(t) + "/news/", "Company-tagged articles."),
        ],
        "🏛️ Filings": [
            ("SEC EDGAR search", "https://www.sec.gov/edgar/search/",
             f"Search {t} or '{name}'. 10-K annual, 10-Q quarterly, 8-K events, Form 4 insider trades."),
            ("Investor relations", _gsearch(name + " investor relations"), "Results, presentations and guidance."),
        ],
        "🎯 Analysts": [
            ("Yahoo Finance analysis", "https://finance.yahoo.com/quote/" + quote(t) + "/analysis/", "Estimates and targets."),
            ("Analyst ratings search", _gsearch(t + " analyst rating price target"), "Brokerage notes and rating changes."),
        ],
        "📺 YouTube": [
            ("YouTube analysis", "https://www.youtube.com/results?search_query=" + quote(t + " stock analysis"),
             "Creator analysis. Sort by upload date."),
            ("YouTube earnings calls", "https://www.youtube.com/results?search_query=" + quote(t + " earnings call"),
             "Earnings call replays are primary material."),
        ],
        "📱 Social": [
            ("Reddit", "https://www.reddit.com/search/?q=" + quote("$" + t) + "&sort=new", "Retail discussion, newest first."),
            ("X / Twitter", "https://x.com/search?q=" + quote("$" + t) + "&src=typed_query&f=live",
             "Live posts. Look for named, dated sources."),
            ("StockTwits", "https://stocktwits.com/symbol/" + quote(t), "Trader messages tagged to the ticker."),
        ],
        "⚖️ Events & legal": [
            ("Lawsuits and probes", _gsearch(name + " lawsuit investigation"), "Court cases and regulator actions."),
            ("Contracts", _gsearch(name + " new contract announcement"), "Deals, launches, partnerships."),
            ("Tariffs and supply", _gsearch(name + " tariffs supply chain"), "Trade exposure and shipping risk."),
            ("Earnings date", _gsearch(t + " next earnings date"), "Confirm on the company's own site."),
        ],
    }


# ------------------------------------------------------------------ Prompt Radar
RADAR = [
    ("Role", "🎭", r"\bROLE\b|\b(act as|you are|analyst|strategist|researcher)\b", "Add a role line."),
    ("Protocol", "🧪", r"\bPROTOCOL\b", "Include the protocol steps for this question."),
    ("Company", "🏷️", r"\[TICKER\]|\[COMPANY|\[MOVERS\]|\b[A-Z]{2,5}\b", "Name the company and ticker."),
    ("Time frame", "🗓️", r"\b(20\d\d|today|as of|horizon|last \d+|next \d+|quarter|year|month|days?)\b",
     "Add a time frame, for example: last 30 days, as of today."),
    ("Grades", "🅰️", r"\bgrade|\bA to D\b|\bEVIDENCE\b", "Ask every claim to carry an evidence grade."),
    ("Sources", "🔗", r"\b(source|link|cite|filing|dated)\b", "Ask for a dated source and link for every number."),
    ("No guessing", "🛡️", r"\b(not found|never guess|do not invent|unverified|could not verify)\b",
     "Ask for NOT FOUND where evidence is missing."),
    ("Quality gate", "🔬", r"\bQUALITY GATE\b|\bbase rate\b", "Include the quality gate."),
    ("Output contract", "📋", r"\bOUTPUT CONTRACT\b|\bCHECKS RUN\b", "Include the output contract."),
    ("Both sides", "⚖️", r"\b(both sides|for and against|bear|counter|against)\b",
     "Ask for the case against as well as the case for."),
    ("Research only", "🧭", r"\b(research only|not financial advice|not a recommendation)\b",
     "Add the research-only boundary."),
    ("No blanks", "🧩", None, "Fill in every [BRACKETED] item before sending."),
]
_BLANK = re.compile(r"\[[A-Z][A-Z0-9 ()/,&'-]{2,}\]")


def radar_report(text):
    out = []
    for label, icon, pat, fix in RADAR:
        if pat is None:
            ok = _BLANK.search(text) is None
        else:
            ok = re.search(pat, text, re.IGNORECASE) is not None
        out.append((label, icon, ok, fix))
    return out


def radar_additions(report):
    fixes = [fix for _, _, ok, fix in report if not ok and "blanks" not in fix.lower()]
    return ("\n\nPROMPT RADAR ADDITIONS\n" + "\n".join("- " + f for f in fixes)) if fixes else ""


def link_budget_html(length):
    pct = min(100, int(length / LINK_LIMIT * 100))
    tone = "#4ade80" if pct < 80 else ("#fbbf24" if pct < 100 else "#ff6b81")
    return (f"<div class='pr-budget'><div class='pr-bar'><span style='width:{pct}%;background:{tone}'></span></div>"
            f"<div class='pr-bnote'>Address budget {pct}% used. The full brief is copied to your clipboard, not sent in the address.</div></div>")


# ------------------------------------------------------------------ one-click copy and open
def action_bar(full_text, link_text, height=190):
    """Each AI button copies the FULL brief to the clipboard, then opens that AI.
    The window is opened first, so browsers allow it. Copy falls back to a hidden text box."""
    full_js = json.dumps(full_text).replace("</", "<\\/")
    link_js = json.dumps(link_text).replace("</", "<\\/")
    engines_js = json.dumps([{"n": n, "u": u, "p": p} for n, u, p, _ in ENGINES])
    buttons = []
    for i, (n, _, _, grad) in enumerate(ENGINES):
        buttons.append(f"<button class='eb' style='background:linear-gradient(135deg,{grad})' "
                       f"onclick='go({i})'>{html.escape(n)}</button>")
    page = f"""
<style>
body{{margin:0;background:transparent;font-family:Inter,system-ui,sans-serif}}
.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}}
.eb{{height:52px;border:0;border-radius:15px;color:#06101f;font-weight:900;font-size:14px;cursor:pointer;
 box-shadow:0 10px 22px rgba(0,0,0,.35);transition:transform .15s}}
.eb:hover{{transform:translateY(-3px)}}
.cp{{width:100%;height:46px;margin-top:10px;border:1px solid rgba(253,224,71,.6);border-radius:15px;font-weight:900;
 color:#1a1200;background:linear-gradient(135deg,#fde047,#facc15 50%,#f59e0b);cursor:pointer;font-size:14px}}
#st{{font-size:12.5px;color:#e2e8f0;margin-top:8px;min-height:18px;line-height:1.45}}
</style>
<div class='grid'>{''.join(buttons)}</div>
<button class='cp' onclick='copyOnly()'>📋 Copy the full research brief</button>
<div id='st'></div>
<script>
const FULL={full_js};
const LINK={link_js};
const E={engines_js};
const S=document.getElementById('st');
function copyText(t){{
  return navigator.clipboard.writeText(t).then(()=>true).catch(()=>{{
    const a=document.createElement('textarea');a.value=t;a.style.position='fixed';a.style.opacity='0';
    document.body.appendChild(a);a.select();const ok=document.execCommand('copy');a.remove();return ok;
  }});
}}
async function copyOnly(){{
  const ok=await copyText(FULL);
  S.textContent= ok ? 'Full research brief copied ✓. Paste it into the AI message box and press Send.' : 'Copy was blocked. Use the Question box above and select all.';
}}
async function go(i){{
  const e=E[i];
  const w=window.open('about:blank','_blank');
  const ok=await copyText(FULL);
  const url = e.p ? e.u+encodeURIComponent(LINK) : e.u;
  if(w){{ w.location.href=url; }}
  S.textContent = ok
    ? 'Full brief copied ✓. In '+e.n+', paste the complete brief into the message box'+(e.p?' (replace the short prefilled instruction if needed).':'.')
    : 'Copy was blocked. Press the copy button, then paste into '+e.n+'.';
}}
</script>"""
    components.html(page, height=height)


def copy_button(text, label):
    """Single copy button for other sections (comparison, movers)."""
    payload = json.dumps(text).replace("</", "<\\/")
    lab = html.escape(label)
    components.html(
        "<style>body{margin:0;background:transparent}</style>"
        "<button id='cp' style='width:100%;height:50px;border:1px solid rgba(253,224,71,.6);border-radius:16px;"
        "font-weight:800;color:#1a1200;background:linear-gradient(135deg,#fde047,#facc15 50%,#f59e0b);cursor:pointer;"
        "font-size:15px;font-family:Inter,system-ui'>" + lab + "</button>"
        "<script>const tx=" + payload + ";const b=document.getElementById('cp');"
        "b.onclick=async()=>{try{await navigator.clipboard.writeText(tx);b.textContent='Copied ✓';}"
        "catch(e){b.textContent='Copy blocked: use the text box';}"
        "setTimeout(()=>{b.textContent='" + lab + "';},2000);};</script>", height=62)


def _short_link(ticker, company):
    name = company or ticker or "the stock"
    return (f"Research {ticker or 'the stock'} ({name}). The full research brief was copied to my clipboard. "
            "Paste it below this line. Follow its protocol, grade every claim A to D, give dated links, "
            "write NOT FOUND if unverifiable. Research only, not financial advice.")


def _mover_link():
    return ("Research the stocks in my daily-file mover list. The full mover brief was copied to my clipboard. "
            "Paste it below this line. Give a dated cause for each move, grade every claim A to D, "
            "write NOT FOUND if unverifiable. Research only, not financial advice.")


# ------------------------------------------------------------------ comparison
def consolidation_prompt(boxes, ticker):
    blocks = [f"--- ANSWER {i} ---\n{b.strip()}" for i, b in enumerate(boxes, start=1) if b.strip()]
    body = "\n\n".join(blocks) if blocks else "[PASTE AT LEAST ONE AI ANSWER IN THE BOXES]"
    return (
        f"I asked different AI tools about {ticker or '[TICKER]'}. Compare their answers.\n\n"
        "Give me: (1) a table of points with columns Point | Answer 1 | Answer 2 | Answer 3 | Agreement "
        "(🟢 all, 🟡 some, 🔴 none); (2) what they all agree on, with grades, dates and links; (3) where they disagree, and which "
        "side has a grade A or B source; (4) claims with no source, marked ⚠️ UNVERIFIED; (5) an overall lean (🟢 UP, 🟡 MIXED, "
        "🔴 DOWN) based only on agreed, sourced points; (6) three checks I should do before deciding. Add no new facts.\n\n"
        + body + "\n\n" + RULES
    )


# ------------------------------------------------------------------ market movers
UP_RGB, DOWN_RGB = "52,211,153", "251,113,133"
AXIS = dict(labelColor="#94a3b8", titleColor="#94a3b8", gridColor="#1e293b", domainColor="#334155")


def _kpi(label, value, sub, tone):
    return (f"<div class='ps-kpi {tone}'><div class='ps-kpi-l'>{html.escape(label)}</div>"
            f"<div class='ps-kpi-v'>{html.escape(value)}</div><div class='ps-kpi-s'>{html.escape(sub)}</div></div>")


def _tiles_html(sel, selected):
    m = max(float(sel["pct"].abs().max()), 1.0)
    tiles = []
    for _, r in sel.iterrows():
        v = float(r["pct"])
        alpha = 0.14 + 0.5 * min(abs(v) / m, 1.0)
        rgb = UP_RGB if v >= 0 else DOWN_RGB
        cls = " ps-sel" if r["ticker"] == selected else ""
        tiles.append(
            f"<div class='ps-tile{cls}' style='background:rgba({rgb},{alpha:.2f})'>"
            f"<span class='ps-tk'>{html.escape(str(r['ticker']))}</span>"
            f"<span class='ps-tp'>{v:+.2f}%</span>"
            f"<span class='ps-tn'>{html.escape(str(r['name'])[:24])}</span></div>")
    return "<div class='ps-tiles'>" + "".join(tiles) + "</div>"


def _pick_mover(sym):
    """Runs before the widgets are drawn, so it may set the picker and the ticker."""
    snap = st.session_state.get("ps_snap", {})
    st.session_state["ps_pick"] = sym
    st.session_state["ps_ticker"] = sym
    st.session_state["ps_company"] = snap.get(sym, {}).get("name", "")


def _pulse(snap, file_date, selected, hide_under5=True):
    rows, excluded_under5, unknown = [], 0, 0
    for ticker, item in snap.items():
        if item.get("pct") is None:
            continue
        price = _price_value(item.get("last"))
        if price is not None and price < 5:
            excluded_under5 += 1
            if hide_under5:
                continue
        elif price is None:
            unknown += 1
        rows.append({"ticker": ticker, "name": item.get("name", "") or ticker, "pct": float(item["pct"]), "price": price})
    if not rows:
        st.info("No stocks match the price filter, or the file has no % change data.")
        return ""

    df_all = pd.DataFrame(rows)
    fc = st.columns([2.2, 1.3, 1.2])
    search = fc[0].text_input("Find ticker or company", placeholder="e.g. NVDA or Micron",
                              key="ps_mover_search").strip().lower()
    floor = fc[1].slider("Minimum move (%)", 0.0, 100.0, 0.0, 0.5, key="ps_move_floor")
    sort_mode = fc[2].selectbox("Sort by", ["Biggest movers", "Gainers first", "Losers first"], key="ps_sort_mode")

    df = df_all.copy()
    if search:
        df = df[df["ticker"].str.lower().str.contains(search, regex=False)
                | df["name"].str.lower().str.contains(search, regex=False)]
    if floor > 0:
        df = df[df["pct"].abs() >= floor]
    if df.empty:
        st.warning("No stocks match these filters. Clear the search or lower the minimum move.")
        return ""
    if sort_mode != "Biggest movers":
        df = df.sort_values("pct", ascending=(sort_mode == "Losers first"))

    n = len(df)
    up, down = int((df.pct > 0).sum()), int((df.pct < 0).sum())
    flat = n - up - down
    best, worst = df.loc[df.pct.idxmax()], df.loc[df.pct.idxmin()]
    st.markdown("<div class='ps-kpis'>" + (
        _kpi("🟢 Advancers", f"{up:,}", f"{up / n * 100:.0f}% of {n:,}", "up")
        + _kpi("🔴 Decliners", f"{down:,}", f"{down / n * 100:.0f}% of view", "down")
        + _kpi("🔵 Unchanged", f"{flat:,}", "no move in view", "flat")
        + _kpi("🧭 Median", f"{df.pct.median():+.2f}%", "typical stock", "flat")
        + _kpi("🚀 Top gainer", f"{best.ticker} {best.pct:+.1f}%", str(best['name'])[:26], "up")
        + _kpi("📉 Top loser", f"{worst.ticker} {worst.pct:+.1f}%", str(worst['name'])[:26], "down")) + "</div>",
        unsafe_allow_html=True)

    c = st.columns([1.2, 1])
    mode = c[0].radio("Display", ["Top movers", "Gainers", "Losers"], horizontal=True, key="ps_mode")
    k = c[1].slider("Stocks per side", 4, 20, 8, key="ps_k")
    if mode == "Gainers":
        sel = df.nlargest(k, "pct")
    elif mode == "Losers":
        sel = df.nsmallest(k, "pct")
    else:
        sel = pd.concat([df.nlargest(k, "pct"), df.nsmallest(k, "pct")]).drop_duplicates("ticker")
    sel = sel.sort_values("pct", ascending=False)

    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"<div class='ps-sub'>🏁 {mode} · {len(sel)} shown · press a Check button below</div>",
                    unsafe_allow_html=True)
        st.markdown(_tiles_html(sel, selected), unsafe_allow_html=True)
    with right:
        st.markdown("<div class='ps-sub'>📊 Distribution of daily moves</div>", unsafe_allow_html=True)
        try:
            chart = (alt.Chart(df).transform_calculate(c="max(-15, min(15, datum.pct))")
                     .mark_bar(color="#a78bfa", opacity=0.85)
                     .encode(x=alt.X("c:Q", bin=alt.Bin(step=1, extent=[-15, 15]),
                                     title="Change % (capped at ±15)", axis=alt.Axis(**AXIS)),
                             y=alt.Y("count()", title="Stocks", axis=alt.Axis(**AXIS)))
                     .properties(height=250, background="transparent").configure_view(stroke=None))
            st.altair_chart(chart, use_container_width=True)
        except Exception as exc:
            st.warning(f"The chart could not be drawn: {exc}")

    st.markdown("<div class='ps-sub'>👉 Check a mover</div>", unsafe_allow_html=True)
    grid = st.columns(4)
    for i, (_, r) in enumerate(sel.iterrows()):
        grid[i % 4].button(f"Check {r['ticker']} · {r['pct']:+.1f}%", key=f"mv_{r['ticker']}",
                           on_click=_pick_mover, args=(r["ticker"],), use_container_width=True)

    st.caption(f"Source: your file ({file_date or 'date not in filename'}). {len(df_all):,} stocks with change data. "
               f"{excluded_under5:,} under $5 in the file; {unknown:,} with no readable price. Not live.")
    return "\n".join(f"{r.ticker} {r.pct:+.2f}% ({r['name']})" for _, r in sel.iterrows())


# ------------------------------------------------------------------ callbacks
def _on_pick():
    snap = st.session_state.get("ps_snap", {})
    s = st.session_state.get("ps_pick", "")
    if s:
        st.session_state["ps_ticker"] = s
        st.session_state["ps_company"] = snap.get(s, {}).get("name", "")


def _on_ticker():
    snap = st.session_state.get("ps_snap", {})
    t = st.session_state.get("ps_ticker", "").strip().upper()
    st.session_state["ps_ticker"] = t
    st.session_state["ps_company"] = snap.get(t, {}).get("name", "")
    st.session_state["ps_pick"] = t if t in snap else ""


def _on_fav():
    pid = st.session_state.get("ps_pid")
    favs = st.session_state["ps_favs"]
    st.session_state["ps_favs"] = [x for x in favs if x != pid] if pid in favs else favs + [pid]


def _on_save_edit():
    st.session_state["ps_saved"] = st.session_state.get("ps_editor", "")
    st.session_state["ps_flash"] = "Saved. The buttons now copy this version."


def _on_reset_edit():
    st.session_state["ps_editor"] = st.session_state.get("ps_base", "")
    st.session_state["ps_saved"] = st.session_state.get("ps_base", "")


def _on_add_missing():
    text = st.session_state.get("ps_editor", "")
    add = radar_additions(radar_report(text))
    if add:
        st.session_state["ps_editor"] = text + add
        st.session_state["ps_saved"] = text + add
        st.session_state["ps_flash"] = "Added the missing parts. Review them, then save."


def _save_decision():
    reason = st.session_state.get("ps_reason", "").strip()
    change = st.session_state.get("ps_change", "").strip()
    if not reason or not change:
        st.session_state["ps_dflash"] = "Write your reason and what would change your mind first."
        return
    st.session_state["ps_journal"].append({
        "date": dt.date.today().isoformat(),
        "ticker": st.session_state.get("ps_ticker", ""),
        "view": st.session_state.get("ps_stance", "⚪ No view"),
        "confidence": st.session_state.get("ps_conf", 3),
        "reason": reason,
        "change_my_mind": change,
        "review_on": str(st.session_state.get("ps_review", dt.date.today() + dt.timedelta(days=30))),
        "price_then": float(st.session_state.get("ps_price", 0.0)),
    })
    st.session_state["ps_reason"] = ""
    st.session_state["ps_change"] = ""
    st.session_state["ps_dflash"] = "Decision saved. Come back on the review date and enter the price."


def judge(stance, move):
    if move is None:
        return "Not judged"
    if "Lean up" in stance:
        return "Correct" if move > 0 else "Missed"
    if "Lean down" in stance:
        return "Correct" if move < 0 else "Missed"
    return "Not judged"


def _init():
    defaults = {"ps_seed": "", "ps_ticker": "", "ps_company": "", "ps_pick": "", "ps_favs": [], "ps_recent": [],
                "ps_journal": [], "ps_saved": "", "ps_editor": "", "ps_base": "", "ps_sig": None,
                "ps_flash": "", "ps_dflash": "", "ps_snap": {}, "ps_hide_under5": True}
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


# ------------------------------------------------------------------ CSS
CSS = """
<style>
.ps-hero{padding:24px 26px;border-radius:24px;margin-bottom:14px;position:relative;overflow:hidden;
 background:radial-gradient(circle at 15% 0%,rgba(250,204,21,.16),transparent 42%),
 radial-gradient(circle at 92% 100%,rgba(167,139,250,.2),transparent 48%),linear-gradient(120deg,#0b1020,#1e1b4b,#3b0764);
 border:1px solid rgba(250,204,21,.3);box-shadow:0 26px 60px rgba(0,0,0,.45)}
.ps-kicker{font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:#fde047;font-weight:900}
.ps-title{font-size:28px;font-weight:900;color:#fff;margin-top:4px}
.ps-sub-hero{color:#e2e8f0;font-size:14px;margin-top:6px;line-height:1.55;max-width:820px}
.ps-rail{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.ps-chip{padding:7px 13px;border-radius:999px;background:rgba(255,255,255,.07);color:#e2e8f0;font-size:12px;font-weight:700;border:1px solid rgba(255,255,255,.16)}
.ps-chip b{display:inline-grid;place-items:center;width:19px;height:19px;border-radius:50%;margin-right:6px;background:#facc15;color:#1a1200;font-size:11px}
.ps-step{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#fde047;font-weight:900;margin:2px 0 8px}
.ps-help{font-size:13px;color:#dbe4f0;line-height:1.55;margin:0 0 8px}
.ps-sub{font-size:13px;font-weight:800;color:#f1f5f9;margin:6px 0 8px}
.ps-stock{border-radius:18px;padding:14px 16px;margin-top:8px;background:linear-gradient(160deg,rgba(30,41,75,.9),rgba(12,20,38,.9));border:1px solid rgba(148,163,184,.22)}
.ps-sym{font-size:20px;font-weight:900;color:#fff}
.ps-nm{color:#e2e8f0;font-size:13px;margin:2px 0 8px}
.ps-row{display:flex;gap:10px;flex-wrap:wrap;font-size:13px;color:#f1f5f9;font-weight:700}
.ps-row span{padding:4px 10px;border-radius:999px;background:rgba(255,255,255,.06)}
.up{color:#4ade80}.down{color:#f87171}.flat{color:#bfdbfe}
.ps-kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin:6px 0 12px}
.ps-kpi{border-radius:16px;padding:12px 14px;background:rgba(15,23,42,.75);border:1px solid rgba(148,163,184,.2)}
.ps-kpi.up{border-color:rgba(52,211,153,.4)}.ps-kpi.down{border-color:rgba(251,113,133,.4)}
.ps-kpi-l{font-size:11px;color:#cbd5e1;text-transform:uppercase;letter-spacing:.08em;font-weight:800}
.ps-kpi-v{font-size:16px;font-weight:900;color:#fff;margin-top:4px;overflow-wrap:anywhere}
.ps-kpi-s{font-size:11px;color:#cbd5e1;margin-top:2px;overflow-wrap:anywhere}
.ps-tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:9px;max-height:400px;overflow-y:auto;padding:2px}
.ps-tile{display:flex;flex-direction:column;align-items:flex-start;gap:2px;padding:11px 12px;border-radius:14px;min-height:80px;
 border:1px solid rgba(148,163,184,.22);color:#fff;transition:transform .18s,box-shadow .18s}
.ps-tile:hover{transform:translateY(-3px) rotateX(4deg);box-shadow:0 14px 26px rgba(0,0,0,.4)}
.ps-sel{border:2px solid #facc15;box-shadow:0 0 20px rgba(250,204,21,.4)}
.ps-tk{font-weight:900;font-size:14px}.ps-tp{font-weight:800;font-size:14px}.ps-tn{font-size:11px;color:#e2e8f0;line-height:1.3}
.ps-card{border-radius:18px;padding:14px 16px;margin:6px 0;background:linear-gradient(160deg,#18233f,#0b1120);border:1px solid rgba(148,163,184,.25)}
.ps-ptitle{font-size:16px;font-weight:900;color:#fff}
.ps-rank{display:inline-grid;place-items:center;min-width:30px;height:24px;padding:0 8px;border-radius:999px;background:#facc15;color:#1a1200;font-size:12px;font-weight:900;margin-right:8px}
.ps-tags{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0}
.ps-tag{font-size:11px;font-weight:800;padding:3px 9px;border-radius:999px;background:rgba(255,255,255,.08);color:#f1f5f9;border:1px solid rgba(255,255,255,.16)}
.ps-tag.src{color:#ddd6fe;border-color:rgba(196,181,253,.45)}
.ps-note{font-size:12.5px;color:#e2e8f0;line-height:1.55}
.ps-filter-summary{min-height:42px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:10px 14px;border-radius:14px;
 background:linear-gradient(120deg,rgba(167,139,250,.14),rgba(34,211,238,.08));border:1px solid rgba(167,139,250,.28);color:#f1f5f9;font-size:12.5px;font-weight:700}
.ps-filter-number{font-size:20px;font-weight:950;color:#fde047}
.ps-filter-sep{color:#94a3b8}
.pr-radar{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin:8px 0}
.pr-dot{padding:9px 8px;border-radius:12px;font-size:12px;font-weight:800;color:#f1f5f9;text-align:center;border:1px solid rgba(148,163,184,.25);background:rgba(15,23,42,.7)}
.pr-dot.ok{border-color:rgba(74,222,128,.7);box-shadow:0 0 14px rgba(74,222,128,.25);color:#bbf7d0}
.pr-dot.miss{border-color:rgba(251,113,133,.7);box-shadow:0 0 14px rgba(251,113,133,.2);color:#fecdd3}
.pr-score{display:flex;align-items:center;gap:14px;padding:12px 14px;border-radius:16px;background:rgba(15,23,42,.75);border:1px solid rgba(148,163,184,.25);margin:6px 0}
.pr-score b{font-size:26px;color:#fff}
.pr-budget{margin:6px 0 2px}
.pr-bar{height:8px;border-radius:999px;background:rgba(148,163,184,.22);overflow:hidden}
.pr-bar span{display:block;height:100%;border-radius:999px}
.pr-bnote{font-size:11.5px;color:#cbd5e1;margin-top:4px}
.ps-stat{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}
.ps-stat div{flex:1;min-width:120px;padding:12px 14px;border-radius:16px;background:rgba(250,204,21,.1);border:1px solid rgba(250,204,21,.3);color:#fef3c7;font-size:12px}
.ps-stat strong{display:block;font-size:22px;color:#fde047}
.ps-guide{border-radius:16px;padding:14px 16px;margin:6px 0 12px;background:rgba(167,139,250,.1);border:1px solid rgba(167,139,250,.35);color:#f1f5f9;font-size:13px;line-height:1.6}
.ps-guide b{color:#fde047}
div[data-testid="stButton"] button{border-radius:12px;font-weight:800;transition:transform .15s,box-shadow .15s}
div[data-testid="stButton"] button:hover{transform:translateY(-1px);box-shadow:0 8px 20px rgba(139,92,246,.2)}
@media(max-width:1000px){.ps-kpis{grid-template-columns:repeat(3,minmax(0,1fr))}.pr-radar{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:600px){.ps-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.ps-title{font-size:23px}}
</style>
"""


# ------------------------------------------------------------------ page
def render(snap=None, default_ticker="", file_date=""):
    _init()
    st.markdown(CSS, unsafe_allow_html=True)
    snap = snap or {}
    st.session_state["ps_snap"] = snap
    all_syms = sorted(snap.keys())

    if default_ticker and st.session_state["ps_seed"] != default_ticker:
        d = default_ticker.strip().upper()
        st.session_state["ps_seed"] = default_ticker
        st.session_state["ps_ticker"] = d
        st.session_state["ps_company"] = snap.get(d, {}).get("name", "")
        st.session_state["ps_pick"] = d if d in snap else ""

    def _price(sym):
        return _price_value(snap.get(sym, {}).get("last"))

    under5 = [s for s in all_syms if _price(s) is not None and _price(s) < 5]
    unknown = [s for s in all_syms if _price(s) is None]

    st.markdown(
        "<div class='ps-hero'><div class='ps-kicker'>🧠 Research studio</div>"
        "<div class='ps-title'>Ask · Check · Compare · Decide</div>"
        "<div class='ps-sub-hero'>Pick a stock, choose a question, check it on the Prompt Radar, then one click copies "
        "the full research brief and opens your AI. Paste the brief into the chat and submit it. Compare answers, then record your own decision. "
        "Research and education only.</div>"
        "<div class='ps-rail'><span class='ps-chip'><b>1</b>Stock</span><span class='ps-chip'><b>2</b>Movers</span>"
        "<span class='ps-chip'><b>3</b>Sources</span><span class='ps-chip'><b>4</b>Question</span>"
        "<span class='ps-chip'><b>5</b>Ask AI</span><span class='ps-chip'><b>6</b>Compare</span>"
        "<span class='ps-chip'><b>7</b>Decide</span></div></div>", unsafe_allow_html=True)

    # ---- Step 1: stock panel
    with st.container(border=True):
        st.markdown("<div class='ps-step'>Step 1 · Choose a stock</div>", unsafe_allow_html=True)
        fc = st.columns([1.5, 2.5])
        fc[0].checkbox("Hide stocks below $5", key="ps_hide_under5",
                       help="Removes under-$5 stocks from the list and movers. Your file is not changed.")
        hide_under5 = st.session_state["ps_hide_under5"]
        syms = [s for s in all_syms if not (hide_under5 and s in under5)]
        fc[1].markdown(
            f"<div class='ps-filter-summary'><span class='ps-filter-number'>{len(syms):,}</span> stocks in the list"
            f"<span class='ps-filter-sep'>·</span>{len(under5):,} under $5"
            f"<span class='ps-filter-sep'>·</span>{len(unknown):,} price unknown</div>", unsafe_allow_html=True)
        if st.session_state["ps_pick"] not in [""] + syms:
            st.session_state["ps_pick"] = ""
        c = st.columns([2, 2, 2])
        if syms:
            c[0].selectbox("From your file", [""] + syms, key="ps_pick", on_change=_on_pick,
                           format_func=lambda s: "Choose a stock…" if not s else
                           f"{s} · {'' if snap[s].get('pct') is None else format(snap[s]['pct'], '+.2f') + '%'} · "
                           f"{str(snap[s].get('name', ''))[:34]}")
        else:
            c[0].caption("Upload your Nasdaq file on the Analyzer page to pick stocks here.")
        c[1].text_input("Ticker (press Enter)", key="ps_ticker", placeholder="e.g. NVDA", on_change=_on_ticker)
        c[2].text_input("Company name", key="ps_company", placeholder="fills in from your file")
        ticker = st.session_state["ps_ticker"].strip().upper()
        company = st.session_state["ps_company"].strip()
        if ticker in snap:
            s = snap[ticker]
            p = s.get("pct")
            cls = "flat" if p in (None, 0) else ("up" if p > 0 else "down")
            pct = "n/a" if p is None else f"{p:+.2f}%"
            st.markdown(
                f"<div class='ps-stock'><div class='ps-sym'>{html.escape(ticker)}</div>"
                f"<div class='ps-nm'>{html.escape(str(s.get('name', '')))}</div>"
                f"<div class='ps-row'><span>Last ${html.escape(str(s.get('last') or 'n/a'))}</span>"
                f"<span class='{cls}'>{pct}</span><span>Ease {html.escape(str(s.get('ease', 'n/a')))}</span>"
                f"<span>File {html.escape(file_date or 'date not in filename')}</span></div></div>", unsafe_allow_html=True)
            if hide_under5 and ticker in under5:
                st.warning("This stock is under $5. It is hidden from the list and movers while the filter is on, "
                           "but you can still research it by typing the ticker.")
        elif ticker:
            st.markdown(f"<div class='ps-stock'><div class='ps-sym'>{html.escape(ticker)}</div>"
                        "<div class='ps-nm'>Not in your file. Research uses the ticker only.</div></div>",
                        unsafe_allow_html=True)

    tabs = st.tabs(["📊 Movers", "🔗 Sources", "🧭 Questions", "🤖 Ask AI", "⚖️ Compare", "📓 Decide and learn"])

    # ---- Movers
    movers_text = ""
    with tabs[0]:
        if snap:
            movers_text = _pulse(snap, file_date, ticker, hide_under5=hide_under5)
        else:
            st.info("Upload your Nasdaq file on the Analyzer page to see the movers.")
        if movers_text:
            with st.expander("🤖 Ask AI why these stocks moved", expanded=True):
                mover_brief = build_prompt(get_prompt("why_moved"), "", "", "", "", {"movers": movers_text})
                action_bar(mover_brief, _mover_link(), height=190)

    # ---- Sources
    with tabs[1]:
        if not ticker:
            st.info("Choose or type a ticker in Step 1 to open its sources.")
        else:
            st.markdown("<div class='ps-help'>Each link opens a live page. Check the date before you decide what it means.</div>",
                        unsafe_allow_html=True)
            for title, links in wiki_groups(ticker, company).items():
                with st.expander(f"{title} · {len(links)} links"):
                    for label, url, note in links:
                        st.markdown(f"**[{label} ↗]({url})**  \n<span class='ps-note'>{html.escape(note)}</span>",
                                    unsafe_allow_html=True)

    # ---- Questions
    with tabs[2]:
        st.markdown("<div class='ps-help'>Start at <b>#1</b> and work down. Each question has its own protocol and rules. "
                    "Finish with <b>#20 360° Complete Research</b>.</div>", unsafe_allow_html=True)
        r = st.columns([3, 2, 2])
        q = r[0].text_input("Search questions", placeholder="news, analysts, red flags, social…", key="ps_q")
        cat = r[1].selectbox("Category", ["All"] + CATEGORIES, key="ps_cat")
        show = r[2].selectbox("Show", ["All", "★ Favourites", "Recent"], key="ps_show")
        pool = PROMPTS
        if q.strip():
            needle = q.strip().lower()
            pool = [x for x in pool if needle in (x["name"] + " " + x["purpose"]).lower()]
        if cat != "All":
            pool = [x for x in pool if x["cat"] == cat]
        if show == "★ Favourites":
            pool = [x for x in pool if x["id"] in st.session_state["ps_favs"]]
        elif show == "Recent":
            rec = st.session_state["ps_recent"]
            pool = sorted([x for x in pool if x["id"] in rec], key=lambda x: rec.index(x["id"]))

        if not pool:
            st.info("No questions match. Clear the search or choose All.")
        else:
            pid = st.selectbox("Question", [x["id"] for x in pool],
                               format_func=lambda i: f"#{get_prompt(i)['rank']} {get_prompt(i)['icon']} {get_prompt(i)['name']}",
                               key="ps_pid")
            p = get_prompt(pid)
            st.session_state["ps_recent"] = ([pid] + [x for x in st.session_state["ps_recent"] if x != pid])[:8]
            tags = (f"<span class='ps-tag'>{LEVEL_ICON[p['level']]} {p['level']}</span>"
                    f"<span class='ps-tag src'>📚 {html.escape(p['src'])}</span>"
                    f"<span class='ps-tag'>🧪 {html.escape(p['protocol'])}</span>")
            st.markdown(f"<div class='ps-card'><div class='ps-ptitle'><span class='ps-rank'>#{p['rank']}</span>"
                        f"{p['icon']} {html.escape(p['name'])}</div><div class='ps-tags'>{tags}</div>"
                        f"<div class='ps-note'><b>Purpose:</b> {html.escape(p['purpose'])}</div>"
                        f"<div class='ps-note' style='margin-top:4px'><b>You get:</b> {html.escape(p['gets'])}</div>"
                        f"<div class='ps-note' style='margin-top:4px'><b>Watch out:</b> {html.escape(p['watch'])}</div>"
                        f"<div class='ps-note' style='margin-top:6px'><b>Rules for this question:</b> "
                        f"{html.escape(' · '.join(p['rules']))}</div></div>", unsafe_allow_html=True)
            st.button("★ Unfavourite" if pid in st.session_state["ps_favs"] else "☆ Add to favourites",
                      key="ps_favbtn", on_click=_on_fav)

            with st.container(border=True):
                st.markdown("<div class='ps-step'>Your settings</div>", unsafe_allow_html=True)
                s1 = st.columns(2)
                horizon = s1[0].selectbox("Time horizon", HORIZONS, key="ps_hz")
                risk = s1[1].selectbox("Risk comfort", RISKS, index=1, key="ps_risk")
                needs = p.get("needs", [])
                extra = {}
                if "thesis" in needs:
                    extra["thesis"] = st.text_input("Your idea in one sentence", key="ps_thesis",
                                                    placeholder="e.g. Demand for its chips keeps growing")
                if "ticker2" in needs:
                    extra["ticker2"] = st.text_input("Second ticker", key="ps_t2", placeholder="e.g. AMD").strip().upper()
                if "sector" in needs:
                    extra["sector"] = st.text_input("Sector or industry", key="ps_sector",
                                                    placeholder="e.g. semiconductors, banking, shipping")
                if "movers" in needs:
                    extra["movers"] = movers_text
                    st.caption("Uses the movers list from the Movers tab." if movers_text
                               else "Upload your Nasdaq file to fill in the movers list.")

            question = build_prompt(p, ticker, company, horizon, risk, extra)
            if ticker in snap:
                question = file_snapshot_line(snap[ticker], file_date) + "\n\n" + question
            sig = (pid, ticker, company, horizon, risk, repr(extra))
            if st.session_state["ps_sig"] != sig:
                st.session_state["ps_sig"] = sig
                st.session_state["ps_base"] = question
                st.session_state["ps_saved"] = question
                st.session_state["ps_editor"] = question
            st.success("Brief ready. Open Ask AI, choose an editor, paste the copied full brief into its message box, and press Send. Each question has its own protocol and output format.")

    # ---- Ask AI
    with tabs[3]:
        if st.session_state.get("ps_flash"):
            st.success(st.session_state.pop("ps_flash"))
        if not st.session_state.get("ps_base"):
            st.info("Pick a question in the Questions tab first.")
        else:
            st.markdown("<div class='ps-step'>1 · Check the brief</div>", unsafe_allow_html=True)
            st.text_area("Brief (edit if you want, then save)", key="ps_editor", height=220)
            e = st.columns([1, 1, 3])
            e[0].button("💾 Save changes", type="primary", key="ps_save_edit", on_click=_on_save_edit, use_container_width=True)
            e[1].button("↺ Reset", key="ps_reset_edit", on_click=_on_reset_edit, use_container_width=True)
            e[2].caption(f"{len(st.session_state['ps_editor']):,} characters. Click Save changes after editing; AI buttons copy the saved version.")

            saved = st.session_state.get("ps_saved", "")
            report = radar_report(saved)
            passed = sum(1 for _, _, ok, _ in report if ok)
            score = round(passed / len(report) * 100)
            st.markdown("<div class='ps-step' style='margin-top:14px'>2 · Prompt Radar</div>", unsafe_allow_html=True)
            tone = "#4ade80" if score >= 80 else ("#fbbf24" if score >= 50 else "#ff6b81")
            st.markdown(f"<div class='pr-score'><b style='color:{tone}'>{score}</b>"
                        f"<div class='ps-note'>{passed} of {len(report)} checks pass. Missing checks show their fix on hover.</div></div>",
                        unsafe_allow_html=True)
            tiles = "".join(
                f"<div class='pr-dot {'ok' if ok else 'miss'}' title='{html.escape(fix, quote=True)}'>{icon} {html.escape(label)}"
                f"<br><span style='font-size:11px;font-weight:700'>{'present' if ok else 'missing'}</span></div>"
                for label, icon, ok, fix in report)
            st.markdown(f"<div class='pr-radar'>{tiles}</div>", unsafe_allow_html=True)
            if any(not ok for _, _, ok, _ in report):
                st.button("✨ Add the missing checks", key="ps_addmissing", on_click=_on_add_missing)

            st.markdown("<div class='ps-step' style='margin-top:14px'>3 · Send it</div>", unsafe_allow_html=True)
            selected_pid = st.session_state.get("ps_pid")
            try:
                selected_prompt = get_prompt(selected_pid) if selected_pid else None
            except (StopIteration, TypeError):
                selected_prompt = None
            link = (
                build_link(selected_prompt, ticker, company)
                if selected_prompt
                else _short_link(ticker, company)
            )
            st.markdown(link_budget_html(len(link)), unsafe_allow_html=True)
            action_bar(saved, link, height=190)
            with st.expander("Preview exactly what gets copied"):
                st.code(saved, language=None)
            st.caption("Each AI button copies the FULL selected brief and opens the chosen AI with a short, task-specific instruction. "
                       "Paste the copied full brief into the AI message box and press Send. This app cannot silently submit prompts to external AI sites. "
                       "Gemini opens without prefilled text, so paste the copied brief there.")

    # ---- Compare
    with tabs[4]:
        st.markdown("<div class='ps-guide'><b>Why compare?</b> Each AI searches differently and can be wrong or out of date. "
                    "Ask the same brief to two or three AIs and paste each answer into its own box. A point they all agree on, "
                    "with a grade A or B source, is far more reliable than one answer alone.</div>", unsafe_allow_html=True)
        a = st.columns(3)
        boxes = [a[i].text_area(f"Answer from AI {i + 1}", key=f"ps_a{i + 1}", height=230,
                                placeholder="Paste the AI's full answer here") for i in range(3)]
        cons = consolidation_prompt(boxes, ticker)
        with st.expander("Show the comparison request"):
            st.code(cons, language=None)
        copy_button(cons, "📋 Copy the comparison request")

    # ---- Decide and learn
    with tabs[5]:
        st.markdown("<div class='ps-help'>Write your view before you read the AI's direction. Come back on the review date "
                    "and enter the price to see how your call did.</div>", unsafe_allow_html=True)
        if st.session_state.get("ps_dflash"):
            msg = st.session_state.pop("ps_dflash")
            (st.warning if msg.startswith("Write") else st.success)(msg)
        d = st.columns([2, 1])
        d[0].radio("My view", ["🟢 Lean up", "🟡 Mixed, wait", "🔴 Lean down", "⚪ No view"], horizontal=True, key="ps_stance")
        d[1].slider("Confidence (1 to 5)", 1, 5, 3, key="ps_conf")
        st.text_area("Why? Name the two strongest facts, with dates.", key="ps_reason", height=90)
        st.text_area("What would change my mind?", key="ps_change", height=70)
        e2 = st.columns(3)
        e2[0].date_input("Review on", value=dt.date.today() + dt.timedelta(days=30), key="ps_review")
        e2[1].number_input("Price today ($)", min_value=0.0, step=0.01, key="ps_price")
        e2[2].button("✅ Save decision", type="primary", key="ps_decide", on_click=_save_decision, use_container_width=True)

        journal = st.session_state["ps_journal"]
        st.markdown("<div class='ps-step' style='margin-top:14px'>Your record</div>", unsafe_allow_html=True)
        if not journal:
            st.caption("No decisions saved yet.")
        else:
            judged = []
            for i, j in enumerate(journal):
                st.markdown(
                    f"<div class='ps-card'><b>{html.escape(j['ticker'] or 'Stock')}</b> · {j['date']} · "
                    f"<b>{html.escape(j['view'])}</b> (confidence {j['confidence']}/5)<br>"
                    f"<span class='ps-note'>Reason: {html.escape(j['reason'])}<br>"
                    f"Would change my mind: {html.escape(j['change_my_mind'])}<br>"
                    f"Review on {j['review_on']} · price then ${j['price_then']:.2f}</span></div>", unsafe_allow_html=True)
                now = st.number_input(f"Price on review date, decision {i + 1} ($)", min_value=0.0, step=0.01, key=f"ps_now_{i}")
                if now > 0 and j["price_then"] > 0:
                    move = (now / j["price_then"] - 1) * 100
                    verdict = judge(j["view"], move)
                    judged.append(verdict)
                    icon = "🟢" if verdict == "Correct" else ("🔴" if verdict == "Missed" else "⚪")
                    st.caption(f"Price moved {move:+.2f}% · {icon} {verdict}")
            done = [v for v in judged if v in ("Correct", "Missed")]
            right_n = sum(1 for v in done if v == "Correct")
            acc = f"{right_n / len(done) * 100:.0f}%" if done else "—"
            st.markdown(f"<div class='ps-stat'><div><strong>{len(journal)}</strong>decisions saved</div>"
                        f"<div><strong>{len(done)}</strong>judged so far</div>"
                        f"<div><strong>{acc}</strong>hit rate</div></div>", unsafe_allow_html=True)
            st.caption("Mixed and no-view decisions are not judged. A small sample says little, so keep recording.")
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=list(journal[0].keys()))
            w.writeheader()
            w.writerows(journal)
            st.download_button("⬇ Download my decisions (CSV)", buf.getvalue(), file_name="my_decisions.csv", mime="text/csv")

        with st.expander("📚 Learn: the evidence grades and the scientist's checks"):
            st.markdown("""
**Evidence grades:** A = SEC filing or company release. B = reputable outlet or data provider. C = named analyst or expert.
D = social media or unnamed source, always unverified.

**Scientist's checks:** a *base rate* asks how often a similar event moved this stock before. A *pre-mortem* assumes the view
failed and asks why. A *falsification test* names the fact that would prove the view wrong. Good research passes all three.

**Words:** *analyst target* = a price an analyst expects in 12 months (an opinion). *Free cash flow* = cash left after running
and investing in the business. *Form 4* = a delayed filing of an insider's trade.
""")

    st.caption("Research and education only. AI answers can be wrong or out of date. Check every source link yourself. "
               "This is not financial advice, and no outcome is guaranteed.")
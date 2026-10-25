from __future__ import annotations

import datetime as dt
import html
import io
import json
import re
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

from modules.question_bank import PROMPTS, build_prompt, build_link, get_prompt
from modules import prompts as legacy_prompts

st.set_page_config(page_title="Equity Intelligence | AI Research Studio", page_icon="◈", layout="wide", initial_sidebar_state="expanded")

# ---------------------------- Theme ----------------------------
CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root{--bg:#070b16;--panel:#0d1426;--panel2:#111c33;--line:rgba(148,163,184,.16);--text:#eef4ff;--muted:#91a0bc;--cyan:#5ee7ff;--violet:#a78bfa;--green:#4ade80}
.stApp{background:radial-gradient(ellipse at 18% 0%,rgba(40,87,180,.22),transparent 36%),radial-gradient(ellipse at 88% 8%,rgba(124,58,237,.18),transparent 30%),var(--bg);color:var(--text);font-family:'DM Sans',sans-serif}
.block-container{max-width:1600px;padding-top:1.2rem;padding-bottom:2rem}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0b1223,#080d19);border-right:1px solid var(--line)}
[data-testid="stSidebar"] *{font-family:'DM Sans',sans-serif}
[data-testid="stHeader"]{background:rgba(7,11,22,.7)}
h1,h2,h3,.display{font-family:'Space Grotesk',sans-serif!important;letter-spacing:-.035em}
.hero{position:relative;overflow:hidden;border:1px solid rgba(103,232,249,.2);border-radius:26px;padding:27px 30px;background:linear-gradient(112deg,rgba(13,25,51,.98),rgba(25,24,64,.88) 62%,rgba(11,35,58,.96));box-shadow:0 20px 70px rgba(0,0,0,.28);margin-bottom:18px}
.hero:before{content:'';position:absolute;width:380px;height:380px;right:-90px;top:-210px;border-radius:50%;background:radial-gradient(circle,rgba(94,231,255,.25),rgba(167,139,250,.1) 42%,transparent 70%);filter:blur(5px)}
.hero:after{content:'';position:absolute;right:7%;bottom:-95px;width:280px;height:180px;border-radius:50%;border:1px solid rgba(94,231,255,.17);box-shadow:0 0 0 20px rgba(94,231,255,.025),0 0 0 42px rgba(167,139,250,.025),0 0 70px rgba(94,231,255,.12);transform:rotate(-15deg)}
.kicker{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--cyan);font-weight:800;margin-bottom:9px}
.hero h1{font-size:clamp(30px,3.5vw,47px);line-height:1.06;margin:0 0 12px;color:#f8fbff;max-width:800px}
.hero p{color:#b9c7e3;font-size:14px;max-width:770px;line-height:1.65;margin:0}
.pillrow{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px;position:relative;z-index:1}.pill{font-size:11px;padding:7px 10px;border:1px solid rgba(148,163,184,.2);border-radius:99px;background:rgba(7,13,28,.42);color:#dce7ff}
.section-title{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:20px;color:#f1f5ff;margin:10px 0 3px}
.section-sub{font-size:12px;color:var(--muted);margin-bottom:13px}
.panel{background:linear-gradient(150deg,rgba(17,28,51,.88),rgba(10,16,31,.9));border:1px solid var(--line);border-radius:19px;padding:17px 18px;box-shadow:0 12px 36px rgba(0,0,0,.16);height:100%}
.metric{background:linear-gradient(145deg,rgba(20,34,62,.95),rgba(11,18,35,.95));border:1px solid var(--line);border-radius:17px;padding:15px 16px;min-height:102px}
.metric .label{font-size:11px;color:#9aa9c5;text-transform:uppercase;letter-spacing:.09em;font-weight:700}.metric .value{font-family:'Space Grotesk',sans-serif;font-size:26px;color:#f8fbff;font-weight:700;margin-top:5px}.metric .hint{font-size:11px;color:#6ee7f9;margin-top:2px}
.prompt-card{border:1px solid rgba(148,163,184,.16);background:linear-gradient(145deg,rgba(18,29,53,.88),rgba(11,17,33,.94));border-radius:17px;padding:14px 15px;min-height:116px}
.prompt-card .name{font-weight:800;font-size:14px;color:#f2f6ff;margin:7px 0 5px}.prompt-card .desc{font-size:11px;color:#9cabc6;line-height:1.5}.tag{display:inline-block;border:1px solid rgba(94,231,255,.24);border-radius:99px;padding:3px 7px;color:#8beaff;font-size:9px;letter-spacing:.07em;text-transform:uppercase;font-weight:800}
.stButton>button{border-radius:12px!important;border:1px solid rgba(148,163,184,.2)!important;background:linear-gradient(135deg,rgba(32,48,79,.96),rgba(19,29,52,.96))!important;color:#eff6ff!important;font-weight:700!important;min-height:42px;transition:all .15s ease}
.stButton>button:hover{border-color:rgba(94,231,255,.55)!important;box-shadow:0 0 24px rgba(94,231,255,.1);transform:translateY(-1px)}
.stButton>button[kind="primary"]{background:linear-gradient(115deg,#3b82f6,#8b5cf6)!important;border:0!important;color:white!important;box-shadow:0 9px 26px rgba(91,91,230,.25)}
.stTextInput input,.stTextArea textarea,.stNumberInput input,.stSelectbox div[data-baseweb="select"],.stMultiSelect div[data-baseweb="select"]{background:#0b1427!important;border-color:rgba(148,163,184,.2)!important;border-radius:11px!important;color:#edf4ff!important}
.stTabs [data-baseweb="tab-list"]{gap:8px;background:rgba(10,16,31,.6);padding:6px;border:1px solid var(--line);border-radius:14px}
.stTabs [data-baseweb="tab"]{border-radius:10px;color:#aebbd4;padding:8px 14px}.stTabs [aria-selected="true"]{background:rgba(59,130,246,.2);color:#f8fbff}
div[data-testid="stExpander"]{background:rgba(14,23,43,.55);border:1px solid var(--line);border-radius:13px}
.small-muted{font-size:11px;color:#8c9ab4}.status-good{color:#4ade80;font-weight:800}.status-warn{color:#fbbf24;font-weight:800}
hr{border-color:rgba(148,163,184,.13)}
footer{visibility:hidden}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

DEFAULT_STOCKS = {
    "AAPL":"Apple", "MSFT":"Microsoft", "NVDA":"NVIDIA", "AMZN":"Amazon", "GOOGL":"Alphabet",
    "META":"Meta Platforms", "TSLA":"Tesla", "AMD":"Advanced Micro Devices", "AVGO":"Broadcom",
    "NFLX":"Netflix", "ORCL":"Oracle", "CRM":"Salesforce", "MU":"Micron Technology", "PLTR":"Palantir",
    "JPM":"JPMorgan Chase", "LLY":"Eli Lilly", "COST":"Costco", "WMT":"Walmart", "XOM":"Exxon Mobil",
    "SPY":"SPDR S&P 500 ETF", "QQQ":"Invesco QQQ ETF", "VOO":"Vanguard S&P 500 ETF", "VTI":"Vanguard Total Stock Market ETF",
    "BABA":"Alibaba", "TSM":"Taiwan Semiconductor", "SHOP":"Shopify", "SONY":"Sony Group", "SAP":"SAP SE",
}
ENGINES = {
    "ChatGPT": "https://chatgpt.com/?q=",
    "Claude": "https://claude.ai/new?q=",
    "Perplexity": "https://www.perplexity.ai/search?q=",
    "Google AI search": "https://www.google.com/search?udm=50&q=",
    "Copilot": "https://copilot.microsoft.com/?q=",
    "Google Search": "https://www.google.com/search?q=",
    "Gemini (paste brief)": "https://gemini.google.com/app",
}


def normalize_symbols(values):
    out = []
    for value in values:
        symbol = re.sub(r"[^A-Za-z0-9.\-^=]", "", str(value).strip()).upper()
        if 1 <= len(symbol) <= 15 and symbol not in out:
            out.append(symbol)
    return out


def load_symbols(uploaded_file):
    if uploaded_file is None:
        return []
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            frame = pd.read_csv(uploaded_file)
        elif name.endswith(('.xlsx', '.xls')):
            frame = pd.read_excel(uploaded_file)
        elif name.endswith('.json'):
            raw = json.load(uploaded_file)
            if isinstance(raw, list):
                if raw and isinstance(raw[0], dict):
                    frame = pd.DataFrame(raw)
                else:
                    return normalize_symbols(raw)
            else:
                frame = pd.DataFrame(raw)
        else:
            raw = uploaded_file.getvalue().decode("utf-8", errors="ignore").splitlines()
            return normalize_symbols([x.split(",")[0] for x in raw if x.strip()])
        col = next((c for c in frame.columns if str(c).strip().lower() in {"ticker", "symbol", "stock", "stocks", "code"}), frame.columns[0] if len(frame.columns) else None)
        return normalize_symbols(frame[col].dropna().tolist()) if col is not None else []
    except Exception as exc:
        st.warning(f"Could not read that stock file: {exc}")
        return []


def radar_report(prompt_text):
    tests = [
        ("Role", bool(re.search(r"\b(role|analyst|researcher|act as)\b", prompt_text, re.I))),
        ("Protocol", "PROTOCOL" in prompt_text.upper()),
        ("Time frame", bool(re.search(r"\b(today|20\d\d|last \d+|next \d+|quarter|year|month|horizon)\b", prompt_text, re.I))),
        ("Evidence grades", bool(re.search(r"evidence grades|grade every claim|grade:|\bgrade\b", prompt_text, re.I))),
        ("Source links", bool(re.search(r"source|link|citation|filing", prompt_text, re.I))),
        ("No guessing", bool(re.search(r"not found|never guess|could not verify", prompt_text, re.I))),
        ("Both sides", bool(re.search(r"bear|against|counter|both sides", prompt_text, re.I))),
        ("Quality gate", "QUALITY GATE" in prompt_text.upper()),
        ("Output contract", "OUTPUT CONTRACT" in prompt_text.upper()),
        ("Research boundary", bool(re.search(r"not financial advice|research and education only", prompt_text, re.I))),
        ("Unfilled placeholders", not bool(re.search(r"\[[A-Z][A-Z0-9 ()/,&'-]{2,}\]", prompt_text))),
    ]
    return tests


@st.cache_data(ttl=300, show_spinner=False)
def get_market_snapshot(symbols):
    """Optional market snapshot. Uses Yahoo Finance via yfinance only when installed/network works."""
    try:
        import yfinance as yf
        rows = []
        for symbol in list(symbols)[:12]:
            try:
                hist = yf.Ticker(symbol).history(period="5d", auto_adjust=False)
                if hist.empty or "Close" not in hist:
                    continue
                close = hist["Close"].dropna()
                if close.empty:
                    continue
                latest = float(close.iloc[-1])
                previous = float(close.iloc[-2]) if len(close) > 1 else latest
                rows.append({"Symbol": symbol, "Price": latest, "Change %": ((latest / previous) - 1) * 100 if previous else 0,
                             "As of": str(close.index[-1].date())})
            except Exception:
                continue
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


def metric(label, value, hint):
    st.markdown(f"<div class='metric'><div class='label'>{html.escape(label)}</div><div class='value'>{html.escape(str(value))}</div><div class='hint'>{html.escape(hint)}</div></div>", unsafe_allow_html=True)


# ---------------------------- Sidebar ----------------------------
with st.sidebar:
    st.markdown("<div style='padding:9px 4px 18px'><div style='font-size:11px;letter-spacing:.2em;color:#5ee7ff;font-weight:900'>◈ EQUITY INTELLIGENCE</div><div style='font-family:Space Grotesk;font-size:22px;font-weight:800;margin-top:7px;color:#f4f7ff'>Research OS</div><div class='small-muted'>AI-powered public-market research</div></div>", unsafe_allow_html=True)
    page = st.radio("WORKSPACE", ["Research Studio", "Classic Research Studio", "Stock Universe", "Research History", "About & Setup"], label_visibility="collapsed")
    st.divider()
    st.markdown("<div class='small-muted'>RESEARCH SETTINGS</div>", unsafe_allow_html=True)
    horizon = st.selectbox("Investment horizon", ["1 month", "3 to 12 months", "1 to 3 years"], index=1, key="global_horizon")
    risk = st.select_slider("Risk comfort", options=["Low", "Medium", "High"], value="Medium", key="global_risk")
    st.caption("Public information only · No brokerage login")

# ---------------------------- Data & selection ----------------------------
if "custom_symbols" not in st.session_state:
    st.session_state.custom_symbols = []
if "research_history" not in st.session_state:
    st.session_state.research_history = []
if "generated_prompt" not in st.session_state:
    st.session_state.generated_prompt = ""

with st.sidebar:
    uploaded = st.file_uploader("Import stock list", type=["csv", "xlsx", "xls", "json", "txt"], key="stock_import")
    if uploaded is not None and st.button("Add imported symbols", use_container_width=True):
        incoming = load_symbols(uploaded)
        st.session_state.custom_symbols = normalize_symbols(st.session_state.custom_symbols + incoming)
        st.success(f"Added {len(incoming)} symbols")
    manual = st.text_input("Add symbols", placeholder="e.g. NVDA, TSM, SAP", key="manual_symbols")
    if st.button("Add to universe", use_container_width=True):
        st.session_state.custom_symbols = normalize_symbols(st.session_state.custom_symbols + manual.replace(";", ",").split(","))
        st.rerun()

symbols = normalize_symbols(list(DEFAULT_STOCKS.keys()) + st.session_state.custom_symbols)
company_map = {**DEFAULT_STOCKS, **{s: s for s in st.session_state.custom_symbols}}

# ---------------------------- Main pages ----------------------------
if page == "Research Studio":
    st.markdown("<div class='hero'><div class='kicker'>◈ Intelligence workspace / v1.0</div><h1>Research the market.<br><span style='background:linear-gradient(90deg,#67e8f9,#a78bfa);-webkit-background-clip:text;color:transparent'>Think beyond the ticker.</span></h1><p>Build structured, evidence-first equity research briefs. Select a stock, choose a research protocol, inspect prompt quality, then open your preferred AI research tool. The complete brief stays under your control.</p><div class='pillrow'><span class='pill'>✦ Evidence-graded prompts</span><span class='pill'>◉ Multi-AI workflow</span><span class='pill'>⌁ Prompt quality radar</span><span class='pill'>⛨ No brokerage access</span></div></div>", unsafe_allow_html=True)

    snap = get_market_snapshot(tuple(symbols[:12]))
    c1, c2, c3, c4 = st.columns(4)
    with c1: metric("Prompt protocols", len(PROMPTS), "Question bank ready")
    with c2: metric("Available symbols", len(symbols), "Built-in + imported")
    with c3: metric("Saved briefs", len(st.session_state.research_history), "This browser session")
    with c4: metric("Data mode", "Optional", "Public snapshot only")

    left, right = st.columns([1.18, 1], gap="large")
    with left:
        st.markdown("<div class='section-title'>01 / Choose your research target</div><div class='section-sub'>Search your combined stock universe or type any valid ticker.</div>", unsafe_allow_html=True)
        stock_options = [f"{s} — {company_map.get(s, s)}" for s in symbols]
        chosen_label = st.selectbox("Stock universe", stock_options, index=stock_options.index("NVDA — NVIDIA") if "NVDA — NVIDIA" in stock_options else 0, key="chosen_stock")
        chosen_symbol = chosen_label.split(" — ", 1)[0] if chosen_label else "NVDA"
        custom_ticker = st.text_input("Or enter a ticker directly", placeholder="e.g. ASML, TSM, SHOP", key="direct_ticker").strip().upper()
        if custom_ticker:
            chosen_symbol = normalize_symbols([custom_ticker])[0] if normalize_symbols([custom_ticker]) else chosen_symbol
        company_name = st.text_input("Company / issuer name (optional)", value=company_map.get(chosen_symbol, chosen_symbol), key="company_name")
        extra_thesis = st.text_area("Your research question / thesis (optional)", placeholder="What do you want to test? What would change your mind?", height=78, key="thesis")
        c_h, c_r = st.columns(2)
        with c_h: local_horizon = st.selectbox("Time horizon", ["1 month", "3 to 12 months", "1 to 3 years"], index=["1 month", "3 to 12 months", "1 to 3 years"].index(horizon), key="task_horizon")
        with c_r: local_risk = st.selectbox("Risk level", ["Low", "Medium", "High"], index=["Low", "Medium", "High"].index(risk), key="task_risk")

    with right:
        st.markdown("<div class='section-title'>02 / Research protocol library</div><div class='section-sub'>Pick one of the existing question-bank tasks. Each task supplies its own method and output contract.</div>", unsafe_allow_html=True)
        search = st.text_input("Search research protocols", placeholder="Search: valuation, earnings, risk…", key="prompt_search")
        cats = sorted({p["cat"] for p in PROMPTS})
        chosen_cat = st.selectbox("Category", ["All categories"] + cats, key="prompt_category")
        filtered = [p for p in PROMPTS if (chosen_cat == "All categories" or p["cat"] == chosen_cat) and search.lower() in (p["name"] + " " + p["purpose"] + " " + p["cat"]).lower()]
        prompt_labels = {f"{p['icon']}  {p['name']}  ·  {p['level']}": p for p in filtered}
        if not prompt_labels:
            st.warning("No prompts match this search. Try another phrase or category.")
            chosen_prompt = PROMPTS[0]
        else:
            default_idx = next((i for i, p in enumerate(filtered) if p["id"] == "full"), 0)
            label = st.selectbox("Select a research task", list(prompt_labels.keys()), index=default_idx, key="selected_prompt_label")
            chosen_prompt = prompt_labels[label]
        st.markdown(f"<div class='prompt-card'><span class='tag'>{html.escape(chosen_prompt['cat'])}</span><div class='name'>{html.escape(chosen_prompt['icon']+' '+chosen_prompt['name'])}</div><div class='desc'>{html.escape(chosen_prompt['purpose'])}</div><div class='desc' style='margin-top:8px'><b>Output:</b> {html.escape(chosen_prompt['gets'])}</div></div>", unsafe_allow_html=True)
        with st.expander("What this prompt checks"):
            st.write(chosen_prompt.get("objective", ""))
            st.write("**Watch out:**", chosen_prompt.get("watch", ""))
            st.write("**Audience:**", chosen_prompt.get("audience", ""))

    st.markdown("<div class='section-title'>03 / Generate your research brief</div><div class='section-sub'>The app builds the complete brief locally. External AI sites will not receive it until you paste and submit it there.</div>", unsafe_allow_html=True)
    if st.button("✦  GENERATE FULL RESEARCH BRIEF", type="primary", use_container_width=True):
        extras = {"thesis": extra_thesis.strip() or None}
        generated = build_prompt(chosen_prompt, chosen_symbol, company_name.strip() or chosen_symbol, local_horizon, local_risk, extras)
        st.session_state.generated_prompt = generated
        st.session_state.generated_meta = {"ticker": chosen_symbol, "company": company_name.strip() or chosen_symbol, "task": chosen_prompt["name"], "created": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "horizon": local_horizon, "risk": local_risk}
        st.session_state.research_history.insert(0, {**st.session_state.generated_meta, "prompt": generated})
        st.session_state.research_history = st.session_state.research_history[:30]

    if st.session_state.generated_prompt:
        generated = st.session_state.generated_prompt
        meta = st.session_state.get("generated_meta", {})
        st.markdown(f"<div class='panel'><div class='kicker'>Generated research artifact</div><div style='font-size:20px;font-weight:800;color:#f5f8ff'>{html.escape(meta.get('ticker',''))} · {html.escape(meta.get('task','Research brief'))}</div><div class='small-muted'>Created {html.escape(meta.get('created',''))} · {html.escape(meta.get('horizon',''))} · Risk: {html.escape(meta.get('risk',''))}</div></div>", unsafe_allow_html=True)
        tests = radar_report(generated)
        good = sum(1 for _, ok in tests if ok)
        r1, r2, r3 = st.columns([1, 1, 2])
        with r1: metric("Prompt quality", f"{round(good/len(tests)*100)}%", f"{good} of {len(tests)} checks")
        with r2: metric("Brief length", f"{len(generated):,}", "Characters")
        with r3:
            st.markdown("<div class='panel'><b>Prompt Radar</b><div class='small-muted'>Quality checks are heuristics, not a guarantee that the research answer will be correct.</div>", unsafe_allow_html=True)
            radar_cols = st.columns(3)
            for idx, (name, ok) in enumerate(tests):
                with radar_cols[idx % 3]: st.markdown(("🟢 " if ok else "🟡 ") + name)
            st.markdown("</div>", unsafe_allow_html=True)
        with st.expander("Preview / edit the full prompt", expanded=True):
            edited = st.text_area("Full research prompt", value=generated, height=370, key="prompt_edit_area")
            if edited != generated:
                st.session_state.generated_prompt = edited
                generated = edited
        st.download_button("⬇ Download research brief (.txt)", data=generated, file_name=f"{meta.get('ticker','research')}_{meta.get('task','brief').lower().replace(' ','_')}.txt", mime="text/plain")
        st.markdown("<div class='section-title'>04 / Continue in your AI tool</div><div class='section-sub'>Open a tool, paste the full brief from above, and press Send. Browser security does not allow this app to silently submit it.</div>", unsafe_allow_html=True)
        ai_cols = st.columns(4)
        short_text = build_link(chosen_prompt, chosen_symbol, company_name.strip() or chosen_symbol)
        for i, (engine, base) in enumerate(ENGINES.items()):
            url = base + quote(short_text, safe="") if engine != "Gemini (paste brief)" else base
            with ai_cols[i % 4]:
                st.link_button(engine, url, use_container_width=True)
        st.caption("Tip: Use the download or copy control for the complete brief. URL-prefill is intentionally short; the full research protocol is the controlling instruction.")
        st.code(generated[:1600] + ("\n… [preview truncated; full brief above]" if len(generated) > 1600 else ""), language=None)

    st.markdown("<div class='section-title'>Live snapshot (optional)</div><div class='section-sub'>A short public-data snapshot is helpful for orientation only. If yfinance or the network is unavailable, the prompt builder still works.</div>", unsafe_allow_html=True)
    if snap.empty:
        st.info("No live snapshot loaded. Install yfinance and check your internet connection to enable this optional panel. Prompt generation does not depend on it.")
    else:
        st.dataframe(snap, use_container_width=True, hide_index=True, column_config={"Price": st.column_config.NumberColumn(format="$%.2f"), "Change %": st.column_config.NumberColumn(format="%.2f%%")})

elif page == "Classic Research Studio":
    st.markdown("<div class='hero'><div class='kicker'>◈ Compatibility workspace</div><h1>Classic Research Studio</h1><p>Your preserved original research workflow, including its stock-selection flow, source links, prompt comparison, and decision journal. The premium dashboard is available in the Research Studio page.</p></div>", unsafe_allow_html=True)
    legacy_prompts.render(default_ticker="")

elif page == "Stock Universe":
    st.markdown("<div class='hero'><div class='kicker'>◈ Asset universe</div><h1>One universe. Your stocks + global tickers.</h1><p>Built-in starter symbols are combined with your imported and manually added symbols. Import CSV, Excel, JSON or TXT files using the sidebar. This is a research universe, not a brokerage position list.</p></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric'><div class='label'>Combined symbols</div><div class='value'>{len(symbols):,}</div><div class='hint'>Built-in + session-added</div></div>", unsafe_allow_html=True)
    frame = pd.DataFrame([{"Symbol": s, "Company / label": company_map.get(s, s), "Yahoo Finance": f"https://finance.yahoo.com/quote/{quote(s)}/"} for s in symbols])
    st.dataframe(frame, use_container_width=True, hide_index=True, column_config={"Yahoo Finance": st.column_config.LinkColumn("Yahoo Finance", display_text="Open quote ↗")})
    st.download_button("Download current universe CSV", frame.to_csv(index=False).encode("utf-8"), "equity_universe.csv", "text/csv")
    if st.button("Clear session-added symbols"):
        st.session_state.custom_symbols = []
        st.rerun()

elif page == "Research History":
    st.markdown("<div class='hero'><div class='kicker'>◈ Your workspace</div><h1>Recent research briefs</h1><p>Generated prompts are kept in Streamlit session state while this session is active. Download important briefs to retain them.</p></div>", unsafe_allow_html=True)
    history = st.session_state.research_history
    if not history:
        st.info("No research briefs generated yet. Open Research Studio and generate a brief.")
    else:
        for i, item in enumerate(history):
            with st.expander(f"{item['created']} · {item['ticker']} · {item['task']}"):
                st.caption(f"Horizon: {item['horizon']} · Risk: {item['risk']}")
                st.text_area("Brief", value=item["prompt"], height=220, key=f"history_prompt_{i}")
                st.download_button("Download this brief", item["prompt"], file_name=f"{item['ticker']}_{i}_brief.txt", key=f"history_dl_{i}")

else:
    st.markdown("<div class='hero'><div class='kicker'>◈ Product notes</div><h1>Built for structured research.</h1><p>This dashboard improves the interface and gives you a local prompt-building workflow. It does not claim to be an autonomous web-search agent; research is performed by the AI site you open after pasting the brief.</p></div>", unsafe_allow_html=True)
    st.markdown("### Included")
    st.markdown("- Existing question-bank protocols and full prompt builder are preserved in `modules/question_bank.py`.\n- Original Research Studio module is retained in `modules/prompts.py` for integration into your existing app.\n- Import stock symbols from CSV, Excel, JSON or TXT.\n- Build and download a full research brief, inspect Prompt Radar checks, and open AI editors.\n- Optional cached Yahoo Finance snapshot if `yfinance` and network access are available.\n- No broker credentials or private account data are requested.")
    st.markdown("### Important implementation notes")
    st.warning("The original `modules/prompts.py` is retained and available through the Classic Research Studio page. Your separate existing app modules such as datahub, theme, membership and earnings_viz are not included in this package; if your main app uses them, keep them in place when integrating this dashboard into that app.")
    st.markdown("### Run locally")
    st.code("pip install -r requirements.txt\nstreamlit run app.py", language="powershell")

st.markdown("<div style='margin-top:28px;padding:15px 0;border-top:1px solid rgba(148,163,184,.13);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:#71819f;font-size:10px;letter-spacing:.05em'><span>◈ EQUITY INTELLIGENCE · RESEARCH OS</span><span>Public information only · Educational use · Not financial advice</span></div>", unsafe_allow_html=True)

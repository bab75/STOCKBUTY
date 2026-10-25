# modules/watchlist.py · My Watchlist.
# Sources: Data Hub stock list (automatic), Stock Lab adds, manual entry, pasted symbols, CSV/Excel/JSON import.
# Prices and P&L come from the daily file in Data Hub. Self-contained: uses no helpers from prompts.py.
# Research and education only. Not financial advice.
import datetime as dt
import html
import io
import json
import math
import re
from urllib.parse import quote

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modules import datahub, theme, membership
from modules import earnings_viz

KEY = "wl_items"
DISMISS = "wl_dismissed"
MAX_CARDS = 150
SOURCE = {"manual": "Manual", "list": "Stock list", "added": "Stock Lab", "import": "Imported", "global": "Global market"}
VIEWS = {"all": "📋 All", "profit": "🟢 In profit", "loss": "🔴 In loss",
         "positions": "💼 Positions", "list": "📥 From stock list"}
SORTS = ["Biggest gain", "Biggest loss", "Symbol"]
ENGINES = {
    "Google AI Mode": "https://www.google.com/search?udm=50&q={q}",
    "ChatGPT": "https://chatgpt.com/?q={q}",
    "Claude": "https://claude.ai/new?q={q}",
    "Microsoft Copilot": "https://copilot.microsoft.com/?q={q}",
    "Google Search": "https://www.google.com/search?q={q}",
    "Gemini (paste)": "https://gemini.google.com/app",
}

HERO_CSS = """
<style>
.wl-hero{padding:18px 22px;border-radius:20px;margin-bottom:12px;
 background:linear-gradient(120deg,rgba(250,204,21,.16),rgba(14,165,233,.18),rgba(168,85,247,.22));
 border:1px solid rgba(253,230,138,.35)}
.wl-t{font-size:22px;font-weight:900;color:#fff}
.wl-s{font-size:13px;color:#cbd5e1;margin-top:4px}
</style>
"""

CARD_CSS = """
html,body{margin:0;background:transparent;font-family:Inter,system-ui,sans-serif;color:#e2e8f0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px;padding:6px;perspective:1100px}
.card{position:relative;border-radius:20px;padding:16px;overflow:hidden;
 background:linear-gradient(160deg,rgba(30,41,80,.88),rgba(8,14,30,.96));
 border:1px solid rgba(148,163,184,.22);box-shadow:0 18px 40px rgba(0,0,0,.45);
 transform-style:preserve-3d;transition:transform .18s ease,box-shadow .3s;animation:float 6s ease-in-out infinite}
.card.up,.card.strong{border-color:rgba(74,222,128,.55)}
.card.down,.card.deep{border-color:rgba(255,107,129,.55)}
.card:hover{box-shadow:0 26px 60px rgba(56,189,248,.25)}
.glow{position:absolute;inset:-40%;pointer-events:none;
 background:conic-gradient(from 0deg,transparent,rgba(56,189,248,.16),transparent 30%);animation:spin 9s linear infinite}
@keyframes float{0%,100%{translate:0 0}50%{translate:0 -5px}}
@keyframes spin{to{transform:rotate(360deg)}}
.top{display:flex;justify-content:space-between;align-items:center;position:relative}
.sym{font-size:20px;font-weight:900;color:#fff}
.badge{font-size:11px;font-weight:800;padding:4px 9px;border-radius:999px;background:rgba(148,163,184,.15)}
.badge.up,.badge.strong{color:#4ade80}
.badge.down,.badge.deep{color:#ff6b81}
.co{font-size:12px;color:#94a3b8;margin:6px 0 10px;position:relative;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.px{font-size:26px;font-weight:900;color:#fff;position:relative}
.chg{font-size:14px;font-weight:800;position:relative}
.chg.up{color:#4ade80;text-shadow:0 0 14px rgba(74,222,128,.5)}
.chg.down{color:#ff6b81}
.pl{margin-top:8px;font-size:12px;font-weight:700;color:#cbd5e1;position:relative}
.meta{font-size:11px;color:#64748b;margin-top:4px;position:relative}
.links{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;position:relative}
.links a{font-size:11px;font-weight:800;padding:5px 9px;border-radius:999px;text-decoration:none;color:#06101f;
 background:linear-gradient(135deg,#fde68a,#f59e0b);box-shadow:0 4px 10px rgba(245,158,11,.25)}
.links a:nth-child(2n){background:linear-gradient(135deg,#67e8f9,#a78bfa)}
.links a:hover{filter:brightness(1.1);transform:translateY(-1px)}
</style>
"""

CARD_JS = """
<script>
document.querySelectorAll('.card').forEach(function(c){
  c.addEventListener('mousemove',function(e){
    var r=c.getBoundingClientRect();
    var x=(e.clientX-r.left)/r.width-.5, y=(e.clientY-r.top)/r.height-.5;
    c.style.transform='rotateY('+(x*18)+'deg) rotateX('+(-y*18)+'deg) translateZ(18px)';
  });
  c.addEventListener('mouseleave',function(){c.style.transform='';});
});
</script>
"""


# ------------------------------------------------------------------ helpers
def _num(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(re.sub(r"[$,%\s+]", "", str(v)))
    except ValueError:
        return None


def _txt(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    return str(v).strip()


def _usd(x, signed=False):
    if x is None:
        return "—"
    sign = "+" if signed and x > 0 else ("-" if x < 0 else "")
    return f"{sign}${abs(x):,.2f}"


def _pct(x):
    return "—" if x is None else f"{x:+.2f}%"


def _msg(text):
    st.session_state["wl_msg"] = text


def _items():
    return st.session_state.setdefault(KEY, {})


def _unlist(sym):
    st.session_state[DISMISS] = [x for x in st.session_state.get(DISMISS, []) if x != sym]


def _new(sym, source, company="", qty=None, buy=None, note=""):
    return {"symbol": sym, "company": _txt(company), "source": source,
            "qty": _num(qty), "buy": _num(buy), "note": _txt(note),
            "added": dt.date.today().isoformat()}


def _snap():
    d = datahub.daily()
    return {} if d is None else {
        _txt(r.get("Symbol")).upper(): r
        for r in d.to_dict("records")
        if _txt(r.get("Symbol"))
    }


def _sync():
    """Brings in the Data Hub stock list and Stock Lab adds. Removed stocks stay removed."""
    items = _items()
    gone = set(st.session_state.setdefault(DISMISS, []))
    for s in st.session_state.get("watchlist", []):
        s = str(s).upper()
        if s and s not in items and s not in gone:
            items[s] = _new(s, "added")
    sl = datahub.stock_list()
    if sl is not None:
        for r in sl.to_dict("records"):
            s = str(r.get("Symbol", "")).upper()
            if s and s not in items and s not in gone:
                items[s] = _new(s, "list", r.get("Name", ""))


def _tier(plp, pct):
    if plp is not None:
        if plp >= 20:
            return "🚀", "Strong profit", "strong"
        if plp > 0:
            return "🟢", "Profit", "up"
        if plp == 0:
            return "⚪", "Break-even", "flat"
        if plp <= -15:
            return "🛑", "Deep loss", "deep"
        return "🔴", "Loss", "down"
    if pct is None:
        return "⚪", "No price", "flat"
    if pct > 0:
        return "📈", "Up today", "up"
    if pct < 0:
        return "📉", "Down today", "down"
    return "⚪", "Flat today", "flat"


def _row(sym, it, sr):
    last = _num(sr.get("Last Sale")) if sr else None
    pct = _num(sr.get("% Change")) if sr else None
    qty, buy = it.get("qty"), it.get("buy")
    cost = qty * buy if qty and buy else None
    value = qty * last if cost is not None and last is not None else None
    pl = value - cost if value is not None else None
    plp = pl / cost * 100 if pl is not None and cost else None
    icon, label, tone = _tier(plp, pct)
    return {**it, "symbol": sym,
            "company": it.get("company") or (_txt(sr.get("Name")) if sr else ""),
            "sector": _txt(sr.get("Sector")) if sr else "",
            "last": last, "pct": pct, "cost": cost, "value": value, "pl": pl, "plp": plp,
            "icon": icon, "label": label, "tone": tone, "in_file": sr is not None}


def _filter(rows, view):
    if view == "profit":
        return [r for r in rows if r["plp"] is not None and r["plp"] > 0]
    if view == "loss":
        return [r for r in rows if r["plp"] is not None and r["plp"] < 0]
    if view == "positions":
        return [r for r in rows if r["cost"] is not None]
    if view == "list":
        return [r for r in rows if r["source"] == "list"]
    return rows


def _sort(rows, how):
    if how == "Symbol":
        return sorted(rows, key=lambda r: r["symbol"])
    key = lambda r: (r["plp"] if r["plp"] is not None else (r["pct"] if r["pct"] is not None else -1e9))
    return sorted(rows, key=key, reverse=(how == "Biggest gain"))


def _links(sym):
    q = quote(f"{sym} stock news earnings")
    return [
        ("🔍 Google AI", f"https://www.google.com/search?udm=50&q={q}"),
        ("🔎 Google", f"https://www.google.com/search?q={q}"),
        ("📊 StockAnalysis", f"https://stockanalysis.com/stocks/{sym.lower()}/"),
        ("🎯 tickers.info", f"https://tickers.info/ticker?Ticker={quote(sym)}"),
        ("📈 Yahoo", f"https://finance.yahoo.com/quote/{quote(sym)}"),
        ("🏛️ SEC", f"https://www.sec.gov/edgar/search/#/q={quote(sym)}"),
    ]


def _question_list():
    """Research questions from prompts.py, read safely whatever version is installed."""
    out = []
    for p in getattr(__import__("modules.prompts", fromlist=["PROMPTS"]), "PROMPTS", []):
        body = p.get("body") or p.get("text") or ""
        out.append((p.get("id", p.get("name", "")), p.get("name", "Question"), body))
    return out


def _copy_button(text, label):
    payload = json.dumps(text).replace("</", "<\\/")
    components.html(f"""
<button id="cp" style="width:100%;padding:12px;border:0;border-radius:14px;font-weight:800;color:#06101f;
background:linear-gradient(135deg,#38bdf8,#8b5cf6);cursor:pointer;font-size:14px;font-family:Inter,system-ui">{html.escape(label)}</button>
<script>const tx={payload};const b=document.getElementById('cp');
b.onclick=async()=>{{try{{await navigator.clipboard.writeText(tx);b.textContent='Copied ✓';}}catch(e){{b.textContent='Copy blocked';}}
setTimeout(()=>{{b.textContent='{html.escape(label)}';}},1500);}};</script>""", height=60)


# ------------------------------------------------------------------ 3D cards
def _card(r, i, mmap):
    e = html.escape
    chg_cls = "up" if (r["pct"] or 0) > 0 else ("down" if (r["pct"] or 0) < 0 else "")
    pl_line = f"{_usd(r['pl'], True)} · {_pct(r['plp'])}" if r["pl"] is not None else "Add shares and buy price"
    links = "".join(f"<a href='{e(u, quote=True)}' target='_blank' rel='noopener'>{e(t)}</a>"
                    for t, u in _links(r["symbol"]))
    src = SOURCE.get(r["source"], r["source"]) + (" · in daily file" if r["in_file"] else " · not in daily file")
    note = f" · {e(r['note'])}" if r["note"] else ""
    return (f"<div class='card {r['tone']}' style='animation-delay:{(i % 6) * 0.5:.1f}s'>"
            "<div class='glow'></div>"
            f"<div class='top'><span class='sym'>{e(r['symbol'])}</span>"
            f"<span class='badge {r['tone']}'>{r['icon']} {e(r['label'])}</span></div>"
            f"<div class='co'>{e(r['company'] or 'company not set')}</div>"
            f"<div class='px'>{_usd(r['last'])}</div>"
            f"<div class='chg {chg_cls}'>{_pct(r['pct'])} today</div>"
            f"<div class='pl'>{e(pl_line)}</div>"
            f"<div class='meta'>{e(src)}{note}</div>"
            f"<div style='position:relative;margin-top:8px'>{membership.chips_html(r['symbol'], mmap)}</div>"
            f"<div class='links'>{links}</div></div>")


def _cards_doc(rows, mmap):
    body = "".join(_card(r, i, mmap) for i, r in enumerate(rows[:MAX_CARDS]))
    return ("<!doctype html><html><head><meta charset='utf-8'><style>" + CARD_CSS + "</style></head><body>"
            "<div class='grid'>" + body + "</div>" + CARD_JS + "</body></html>")
# ------------------------------------------------------------------ summary
def _summary(rows):
    priced = [r for r in rows if r["pl"] is not None]
    cost = sum(r["cost"] for r in priced)
    value = sum(r["value"] for r in priced)
    pl = value - cost
    plp = pl / cost * 100 if cost else None
    best = max(priced, key=lambda r: r["plp"]) if priced else None
    worst = min(priced, key=lambda r: r["plp"]) if priced else None
    in_file = sum(1 for r in rows if r["in_file"])
    tone = "up" if pl > 0 else ("down" if pl < 0 else "")
    k = st.columns(6)
    k[0].markdown(theme.card("Watching", f"{len(rows):,}", f"{in_file:,} in daily file"), unsafe_allow_html=True)
    k[1].markdown(theme.card("Positions", f"{len(priced):,}", "shares × buy price"), unsafe_allow_html=True)
    k[2].markdown(theme.card("Cost basis", _usd(cost) if priced else "—"), unsafe_allow_html=True)
    k[3].markdown(theme.card("Market value", _usd(value) if priced else "—", "daily file prices"),
                  unsafe_allow_html=True)
    k[4].markdown(theme.card("Total P&L", _usd(pl, True) if priced else "—", _pct(plp), tone),
                  unsafe_allow_html=True)
    k[5].markdown(theme.card("Best / worst",
                             f"{best['symbol']} {_pct(best['plp'])}" if best else "—",
                             f"{worst['symbol']} {_pct(worst['plp'])}" if worst else "",
                             "up" if best else ""), unsafe_allow_html=True)


# ------------------------------------------------------------------ callbacks
def _cb_add():
    sym = str(st.session_state.get("wl_new_sym", "")).strip().upper()
    if not sym:
        return _msg("Enter a ticker first.")
    items = _items()
    if sym in items:
        return _msg(f"{sym} is already on your watchlist.")
    items[sym] = _new(sym, "manual", st.session_state.get("wl_new_co", ""), st.session_state.get("wl_new_qty"),
                      st.session_state.get("wl_new_buy"), st.session_state.get("wl_new_note", ""))
    _unlist(sym)
    for k in ("wl_new_sym", "wl_new_co", "wl_new_qty", "wl_new_buy", "wl_new_note"):
        st.session_state[k] = ""
    _msg(f"{sym} added.")


def _cb_paste():
    raw = st.session_state.get("wl_paste", "")
    syms = [s.upper() for s in re.split(r"[,;\s]+", raw) if re.fullmatch(r"[A-Za-z.\-]{1,10}", s)]
    items, n = _items(), 0
    for s in dict.fromkeys(syms):
        if s not in items:
            items[s] = _new(s, "manual")
            _unlist(s)
            n += 1
    st.session_state["wl_paste"] = ""
    _msg(f"Added {n} new stock{'s' if n != 1 else ''}.")


def _read_file(upload):
    name, raw = upload.name.lower(), upload.getvalue()
    if name.endswith(".json"):
        data = json.loads(raw.decode("utf-8"))
        if isinstance(data, dict):
            data = data.get("items", data.get("watchlist", []))
        df = pd.DataFrame(data)
    elif name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(raw))
    else:
        df = pd.read_excel(io.BytesIO(raw))
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _col(df, *names):
    for n in names:
        if n in df.columns:
            return n
    return None


def _cb_import():
    up = st.session_state.get("wl_upload")
    if up is None:
        return _msg("Choose a file first.")
    try:
        df = _read_file(up)
    except Exception as exc:
        return _msg(f"Could not read that file: {exc}")
    c_sym = _col(df, "symbol", "ticker", "sym")
    if c_sym is None:
        return _msg("The file needs a Symbol or Ticker column.")
    c_co = _col(df, "company", "name")
    c_qty = _col(df, "shares", "qty", "quantity", "units", "number of shares")
    c_buy = _col(df, "buy price", "buy", "cost", "avg cost", "entry price", "price paid")
    c_note = _col(df, "note", "notes", "comment")
    items, added, updated = _items(), 0, 0
    for r in df.to_dict("records"):
        s = _txt(r.get(c_sym)).upper()
        if s in ("", "NAN"):
            continue
        qty = _num(r.get(c_qty)) if c_qty else None
        buy = _num(r.get(c_buy)) if c_buy else None
        note = _txt(r.get(c_note)) if c_note else ""
        if s in items:
            if qty is not None:
                items[s]["qty"] = qty
            if buy is not None:
                items[s]["buy"] = buy
            if note:
                items[s]["note"] = note
            updated += 1
        else:
            items[s] = _new(s, "import", r.get(c_co) if c_co else "", qty, buy, note)
            added += 1
        _unlist(s)
    _msg(f"Imported {added} new and updated {updated} existing stocks.")


def _cb_save(sym):
    it = _items().get(sym)
    if it is None:
        return
    it["qty"] = _num(st.session_state.get(f"wl_ed_qty_{sym}")) or None
    it["buy"] = _num(st.session_state.get(f"wl_ed_buy_{sym}")) or None
    it["note"] = _txt(st.session_state.get(f"wl_ed_note_{sym}"))
    _msg(f"{sym} saved.")


def _cb_remove(sym):
    _items().pop(sym, None)
    st.session_state[DISMISS] = list(set(st.session_state.get(DISMISS, [])) | {sym})
    st.session_state["watchlist"] = [x for x in st.session_state.get("watchlist", []) if x != sym]
    _msg(f"{sym} removed.")


def _cb_clear():
    if not st.session_state.get("wl_confirm_clear"):
        return _msg("Tick the confirmation box first.")
    items = _items()
    sl = datahub.stock_list()
    listed = set(sl["Symbol"]) if sl is not None else set()
    st.session_state[DISMISS] = list(set(items) | listed | set(st.session_state.get(DISMISS, [])))
    items.clear()
    st.session_state["watchlist"] = []
    _msg("Watchlist cleared. Stocks stay hidden until you add them again.")


def _export_df(rows):
    return pd.DataFrame([{
        "Symbol": r["symbol"], "Company": r["company"], "Source": SOURCE.get(r["source"], r["source"]),
        "Shares": r["qty"], "Buy price": r["buy"], "Last price": r["last"], "Cost": r["cost"],
        "Value": r["value"], "P&L $": r["pl"], "P&L %": r["plp"], "Today %": r["pct"],
        "Signal": r["label"], "Note": r["note"], "Added": r["added"]} for r in rows])


# ------------------------------------------------------------------ earnings for watchlist
def _earnings_block(symbols):
    e = datahub.earnings()
    if e is None:
        st.caption("Load your earnings file in 📥 Data Hub to see earnings for these stocks.")
        return
    v = e[e["Symbol"].isin(symbols)]
    if v.empty:
        st.caption("None of your watchlist stocks are in the earnings file.")
        return
    earnings_viz.styled_table(v, height=min(560, 90 + 40 * len(v)))


# ------------------------------------------------------------------ page
def render():
    st.markdown(HERO_CSS, unsafe_allow_html=True)
    _sync()
    snap = _snap()
    items = _items()

    st.markdown(
        "<div class='wl-hero'><div class='wl-t'>⭐ My Watchlist</div>"
        "<div class='wl-s'>One place for your Data Hub stock list, your saved watchlist, and every global stock "
        "available in your program's daily market file. Prices and P&amp;L use that file's date. Research and education only.</div>"
        "</div>", unsafe_allow_html=True
    )

    msg = st.session_state.pop("wl_msg", "")
    if msg:
        st.info(msg)

    # Rows saved in the user's watchlist (editable, importable and exportable).
    my_rows = [_row(sym, it, snap.get(sym)) for sym, it in items.items()]

    # Discover the symbols in the Data Hub stock list and the global daily market file.
    sl = datahub.stock_list()
    list_symbols = set()
    if sl is not None and not sl.empty and "Symbol" in sl.columns:
        list_symbols = {
            _txt(sym).upper() for sym in sl["Symbol"].tolist()
            if _txt(sym)
        }

    # The global universe includes every symbol present in the daily file, including
    # symbols that also happen to be in the stock list or the saved watchlist.
    global_symbols = {str(sym).strip().upper() for sym in snap if str(sym).strip()}
    all_by_symbol = {r["symbol"]: r for r in my_rows}

    # Keep the complete Data Hub stock list available in the universe filter,
    # even when a symbol was previously dismissed from the personal watchlist.
    list_names = {}
    if sl is not None and not sl.empty and "Symbol" in sl.columns:
        for rec in sl.to_dict("records"):
            sym = _txt(rec.get("Symbol")).upper()
            if sym:
                list_names[sym] = _txt(rec.get("Name"))
                if sym not in all_by_symbol:
                    all_by_symbol[sym] = _row(
                        sym,
                        _new(sym, "list", list_names[sym]),
                        snap.get(sym)
                    )

    for sym in sorted(global_symbols):
        if sym not in all_by_symbol:
            sr = snap.get(sym)
            all_by_symbol[sym] = _row(
                sym,
                _new(sym, "global", _txt(sr.get("Name")) if sr else ""),
                sr
            )
    all_rows = list(all_by_symbol.values())

    # Single universe selector: all program stocks, Data Hub stock list, global market,
    # or the user's own saved watchlist. This is independent of performance filters.
    universe_labels = [
        "All stocks in program",
        "Stock list",
        "Global stocks",
        "My watchlist",
    ]
    universe_choice = st.selectbox(
        "STOCK UNIVERSE",
        universe_labels,
        index=0,
        key="wl_universe_choice",
        help="All stocks combines your saved watchlist with every symbol in the Data Hub daily market file.",
    )

    if universe_choice == "Stock list":
        base_rows = [r for r in all_rows if r["symbol"] in list_symbols]
    elif universe_choice == "Global stocks":
        base_rows = [r for r in all_rows if r["symbol"] in global_symbols]
    elif universe_choice == "My watchlist":
        base_rows = list(my_rows)
    else:
        base_rows = list(all_rows)

    mem, etfs, mmap, _ = membership.etf_context("")
    spec = membership.etf_filter_bar(mem, etfs)
    allowed = membership.allowed_symbols(mem, spec)
    if allowed is not None:
        base_rows = [r for r in base_rows if r["symbol"] in allowed]

    # Summary tiles now describe the currently selected universe.
    if base_rows:
        _summary(base_rows)
    else:
        if universe_choice == "Stock list":
            st.info("No stocks found in the Data Hub stock list. Load or refresh it in Data Hub.")
        elif universe_choice == "Global stocks":
            st.info("No global stocks found. Load the daily market file in Data Hub.")
        else:
            st.info("No stocks found in this universe. Load a stock list, add stocks, or import a file.")

    with st.expander("➕ Add, paste or import", expanded=not my_rows):
        a = st.columns([1.2, 1.8, 1, 1, 1.8])
        a[0].text_input("Ticker", key="wl_new_sym", placeholder="NVDA")
        a[1].text_input("Company (optional)", key="wl_new_co")
        a[2].text_input("Shares", key="wl_new_qty", placeholder="10")
        a[3].text_input("Buy price $", key="wl_new_buy", placeholder="125.50")
        a[4].text_input("Note", key="wl_new_note", placeholder="Why I watch it")
        st.button("➕ Add stock", type="primary", key="wl_add", on_click=_cb_add)
        p = st.columns([3, 1])
        p[0].text_area("Paste many symbols (commas, spaces or new lines)", key="wl_paste", height=80)
        p[1].write("")
        p[1].button("Add pasted symbols", key="wl_paste_btn", on_click=_cb_paste)
        i = st.columns([3, 1])
        i[0].file_uploader(
            "Import CSV, Excel or JSON (Symbol, Shares, Buy price and Note are optional)",
            type=["csv", "xlsx", "xls", "json"], key="wl_upload"
        )
        i[1].write("")
        i[1].button("⬆ Import", key="wl_import_btn", on_click=_cb_import)

    if not base_rows:
        # The management/export sections below still remain available for saved items.
        display_rows = []
    else:
        c = st.columns([2.2, 1.4, 1.2])
        view = c[0].radio(
            "PERFORMANCE FILTER",
            list(VIEWS),
            format_func=lambda k: VIEWS[k],
            horizontal=True,
            key="wl_view",
        )
        sort = c[1].selectbox("SORT BY", SORTS, key="wl_sort")
        page_size = c[2].selectbox("Cards per page", [30, 60, 100], index=0, key="wl_page_size")

        # The performance filter is applied after the universe selector.
        filtered = _sort(_filter(base_rows, view), sort)
        if not filtered:
            st.info("No stocks match this performance filter. Choose another filter or stock universe.")
            display_rows = []
        else:
            pages = max(1, math.ceil(len(filtered) / int(page_size)))
            page_key = "wl_universe_page"
            old_sig = (universe_choice, view, sort, int(page_size), len(filtered), tuple(r["symbol"] for r in filtered[:10]))
            if st.session_state.get("wl_universe_page_sig") != old_sig:
                st.session_state["wl_universe_page_sig"] = old_sig
                st.session_state[page_key] = 1
            page = min(max(1, int(st.session_state.get(page_key, 1))), pages)
            st.session_state[page_key] = page
            if pages > 1:
                pcols = st.columns([1, 2, 1])
                if pcols[0].button("← Previous", disabled=page <= 1, key="wl_univ_prev", use_container_width=True):
                    st.session_state[page_key] = page - 1
                    st.rerun()
                pcols[1].markdown(
                    f"<div style='text-align:center;padding:.45rem;color:#94a3b8'>"
                    f"Page <b>{page}</b> of <b>{pages}</b> · {len(filtered):,} matching stocks</div>",
                    unsafe_allow_html=True
                )
                if pcols[2].button("Next →", disabled=page >= pages, key="wl_univ_next", use_container_width=True):
                    st.session_state[page_key] = page + 1
                    st.rerun()
            lo = (page - 1) * int(page_size)
            display_rows = filtered[lo:lo + int(page_size)]
            components.html(
                _cards_doc(display_rows, mmap),
                height=min(1600, 300 * math.ceil(len(display_rows) / 3) + 40),
                scrolling=True
            )
            st.caption(
                f"Showing {lo + 1:,}–{min(lo + len(display_rows), len(filtered)):,} of {len(filtered):,} stocks. "
                "Hover a card to tilt it. Research links open in a new tab."
            )

    with st.expander("📅 Earnings for the selected universe"):
        _earnings_block([r["symbol"] for r in base_rows])

    if display_rows:
        st.markdown("#### 🤖 Ask AI about a stock")
        questions = _question_list()
        a = st.columns([2, 3, 2])
        pick = a[0].selectbox("Stock", [r["symbol"] for r in display_rows], key="wl_ai_sym")
        qidx = a[1].selectbox(
            "Research question",
            list(range(len(questions))) if questions else [0],
            format_func=lambda i: questions[i][1] if questions else "No questions found",
            key="wl_ai_q",
        )
        eng = a[2].selectbox("Open with", list(ENGINES), key="wl_ai_eng")
        r = next(x for x in display_rows if x["symbol"] == pick)
        body = questions[qidx][2].replace("[TICKER]", pick) if questions else ""
        text = (
            f"Research {pick} ({r['company'] or 'company not set'}). {body}\n\n"
            f"FILE SNAPSHOT (daily Nasdaq file): last {_usd(r['last'])}, change {_pct(r['pct'])}. "
            "Dated reference only; verify the live price. Do not invent numbers. "
            "Mark anything unverified as UNVERIFIED. Research only, not a recommendation."
        )
        url = ENGINES[eng].replace("{q}", quote(text[:1400]))
        b = st.columns([1, 1])
        b[0].markdown(
            f"<a class='abtn' href='{html.escape(url, quote=True)}' target='_blank' "
            f"rel='noopener'>Open {html.escape(eng)} →</a>",
            unsafe_allow_html=True
        )
        with b[1]:
            _copy_button(text, "📋 Copy question")

    # Editing and removal apply only to the user's saved watchlist, never to the
    # ephemeral global-market rows.
    if my_rows:
        with st.expander("✏️ Edit shares, buy price or note"):
            editable_symbols = [r["symbol"] for r in my_rows]
            sel = st.selectbox("Stock", editable_symbols, key="wl_edit_sym")
            it = items[sel]
            e = st.columns([1, 1, 2, 1, 1])
            e[0].number_input(
                "Shares", min_value=0.0, value=float(it.get("qty") or 0.0),
                step=1.0, key=f"wl_ed_qty_{sel}"
            )
            e[1].number_input(
                "Buy price $", min_value=0.0, value=float(it.get("buy") or 0.0),
                step=0.01, key=f"wl_ed_buy_{sel}"
            )
            e[2].text_input("Note", value=it.get("note", ""), key=f"wl_ed_note_{sel}")
            e[3].button("💾 Save", key=f"wl_save_{sel}", on_click=_cb_save, args=(sel,))
            e[4].button("🗑 Remove", key=f"wl_rm_{sel}", on_click=_cb_remove, args=(sel,))

    st.markdown("#### 📦 Export, backup and clear")
    export_rows = my_rows if universe_choice == "My watchlist" else base_rows
    xbuf = io.BytesIO()
    with pd.ExcelWriter(xbuf, engine="openpyxl") as w:
        _export_df(export_rows).to_excel(w, index=False, sheet_name="Watchlist")
    d = st.columns(3)
    d[0].download_button(
        "⬇ Excel (.xlsx)", xbuf.getvalue(), file_name="watchlist_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="wl_dl_x"
    )
    d[1].download_button(
        "⬇ CSV", _export_df(export_rows).to_csv(index=False).encode("utf-8"),
        file_name="watchlist_export.csv", mime="text/csv", key="wl_dl_c"
    )
    d[2].download_button(
        "⬇ JSON (saved watchlist)", json.dumps(list(items.values()), indent=2).encode("utf-8"),
        file_name="my_watchlist.json", mime="application/json", key="wl_dl_j"
    )
    cc = st.columns([2, 1])
    cc[0].checkbox("Yes, clear the whole watchlist", key="wl_confirm_clear")
    cc[1].button("🗑 Clear all", key="wl_clear", on_click=_cb_clear)
    st.caption(
        "Stock list and global market rows are read from Data Hub. Global stocks are not copied into "
        "your saved watchlist unless you add them. Download JSON to back up your saved watchlist."
    )

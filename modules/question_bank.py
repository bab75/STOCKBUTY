# modules/question_bank.py · Research questions built from shared protocols.
# Each question = mission + protocol (method) + evidence grades + quality gate + its own rules + layout.
# Research and education only. Not financial advice.

ICON_LEGEND = ("ICONS (write the word too): 🟢 UP/positive  🟡 MIXED  🔴 DOWN/negative  ⚪ NOT FOUND  "
               "⚠️ UNVERIFIED  🏛️ filing  📰 news  🎯 analyst  📱 social  📅 dated event  🔗 link")

RULES = (
    "RULES\n"
    "- Research and education only. Not financial advice. No buy, sell or hold instruction.\n"
    "- Use live web search. Date every price, number and item. Say if a price is delayed.\n"
    "- Give a source, date and link for every number. If you cannot verify it, write NOT FOUND. Never guess.\n"
    "- Plain words for a beginner. Explain each finance term in brackets, once.\n"
    "- Social media is opinion: mark it UNVERIFIED. Do not quote private accounts.\n"
    "- Finish with: Research only. Not financial advice."
)

EVIDENCE = (
    "EVIDENCE GRADES: A = SEC filing or company release; B = reputable outlet or data provider; "
    "C = named analyst or expert; D = social media or unnamed source (always ⚠️ UNVERIFIED). "
    "Grade every claim A, B, C or D."
)

QUALITY_GATE = (
    "QUALITY GATE (check before you answer):\n"
    "1) Every number has a date and a link.\n"
    "2) At least two dated facts argue against your view.\n"
    "3) Give a confidence word, HIGH, MEDIUM or LOW, and the one fact that would change it.\n"
    "4) Base rate: how often has a similar event moved this stock or its sector? Use dated examples."
)

PROTOCOLS = {
    "scan": ("Evidence scan", [
        "Confirm the live price and its time stamp. Compare it with the file snapshot.",
        "List news and filings from the last 30 days, each dated and graded.",
        "Merge duplicates. Rank by likely price impact.",
        "For the top item, state what would have to be true for it to matter.",
    ]),
    "fundamentals": ("Business health", [
        "Use the latest 10-K or 10-Q. State the period for every number.",
        "Measure revenue growth over 1 and 3 years, and whether profit turns into cash.",
        "List debt, cash and any debt due inside 12 months, with the filing section.",
        "Compare valuation with the industry median and say what the price assumes.",
    ]),
    "technical": ("Price behaviour", [
        "Use dated price data only. Name the source and its time stamp.",
        "Read the 50-day and 200-day averages, RSI and MACD in one plain sentence each.",
        "Check whether volume confirms the move.",
        "Describe what the chart would have to show to invalidate the read.",
    ]),
    "catalyst": ("Catalysts and results", [
        "List dated events in the next 90 days. Mark each CONFIRMED or ESTIMATED.",
        "Find the last result against expectations, and the stock's reaction.",
        "Rank catalysts by how many analysts expect them.",
        "Name the outcome the market is already pricing in.",
    ]),
    "risk": ("Downside search", [
        "Search filings for dilution, debt, legal and going-concern wording.",
        "Grade each risk LOW, MEDIUM or HIGH, with its filing section.",
        "Estimate how bad the downside could be. Label it ESTIMATE and give its basis.",
        "Mark any category with no evidence NOT FOUND.",
    ]),
    "thesis": ("Hypothesis test", [
        "Restate the view as one sentence that could be proven false.",
        "Gather the strongest evidence for and against, each graded.",
        "Name three facts that would prove the view wrong, and where to check each.",
        "Name the single price or event that should trigger a re-think.",
    ]),
    "sector": ("Sector analysis", [
        "Name the sector's drivers, each with a dated source.",
        "Rank the leading companies by a measure you state.",
        "Describe how the sector behaved in its last downturn.",
        "Say what the fund-versus-stock trade-off depends on.",
    ]),
    "sentiment": ("Crowd signal", [
        "Find public posts and videos from the last 30 days.",
        "Tag each claim as fact, opinion or unverified.",
        "Count the tone, and state that tone is not evidence.",
        "Note any poster who discloses owning the stock.",
    ]),
    "moat": ("Durability test", [
        "Name the moat type and rate it wide, narrow or weak.",
        "Test durability over ten years against two named peers.",
        "Name the threat that would end the moat and its earliest warning sign.",
    ]),
    "full": ("Full research and pre-mortem", [
        "Run the scan, fundamentals, technical, catalyst, risk and sentiment protocols in order.",
        "Score each area UP, MIXED, DOWN or NOT FOUND.",
        "Give the bull and bear case, each with graded sources.",
        "Pre-mortem: assume the view failed in 12 months. List the three likeliest reasons.",
    ]),
}

LAYOUTS = {
    "full360": ("ANSWER LAYOUT: 1) Verdict card: Area | Icon | Signal | Reason | Date and link. "
                "2) Five plain sentences. 3) Bull case, three graded bullets. 4) Bear case, three graded bullets. "
                "5) Dated events, next 90 days, CONFIRMED or ESTIMATED. 6) Confidence and three data gaps. "
                "7) Pre-mortem reasons. 8) Numbered sources with grade, date and link."),
    "standard": ("ANSWER LAYOUT: 1) One-line summary with one icon. 2) Facts table: Factor | Shows | Icon and word | "
                 "Grade | Date and link. 3) Reasons it could rise, three bullets. 4) Reasons it could fall, three bullets. "
                 "5) Dated items to watch. 6) One question for me. 7) Numbered sources."),
    "table": "ANSWER LAYOUT: one table first, then at most three short bullets. Each row has a grade, a date and a link. "
             "End with a numbered sources list.",
    "short": "ANSWER LAYOUT: under 250 words, short icon bullets, graded items with dates and links.",
    "custom": "ANSWER LAYOUT: one heading per requested section, a plain-English summary first, every claim graded, "
              "dated and linked, then a numbered sources list.",
}


def _q(qid, icon, name, level, cat, fmt, protocol, purpose, gets, watch, context, objective,
       audience, style, rules, src="Original", needs=None):
    return {"id": qid, "icon": icon, "name": name, "level": level, "cat": cat, "fmt": fmt,
            "protocol": protocol, "purpose": purpose, "gets": gets, "watch": watch,
            "context": context, "objective": objective, "audience": audience, "style": style,
            "rules": rules, "src": src, "needs": needs or []}


PROMPTS = [
    _q("quick", "⚡", "Quick Check", "Beginner", "Start here", "short", "scan",
       "A one-minute snapshot to decide whether a stock deserves more of your time.",
       "Price with time stamp, 1-week, 1-month and 1-year moves, consensus, next event, top three risks.",
       "A snapshot is not a decision.",
       "I am a beginner looking at [COMPANY] ([TICKER]).",
       "Give the price with its time stamp, the 1-week, 1-month and 1-year moves, the analyst consensus with the firms named, "
       "the next company event, and the top three risks.",
       "A beginner with no finance background.", "Plain and friendly.",
       ["Say whether the price is delayed.", "Name each firm behind a consensus, or write NOT FOUND."]),

    _q("news", "📰", "News & Catalyst Digest", "Beginner", "Market & trend", "table", "scan",
       "The most material news and filings from 30 days, in one reviewable list.",
       "Up to 10 dated items with grade, impact icon and direct link.",
       "Headlines repeat. Count one story once and open the original link.",
       "I want the most important recent news about [COMPANY] ([TICKER]).",
       "Find up to 10 of the most material news items and filings from the last 30 days. For each give the date, headline, "
       "outlet or filing, type icon, impact icon, one sentence on why it matters, and the link. Rank by likely impact.",
       "A beginner who reads news critically.", "A table first. One plain sentence per row.",
       ["Merge duplicate stories and keep the original outlet's link.", "Mark opinion pieces OPINION."]),

    _q("why_moved", "⚡", "Why Did These Stocks Move?", "Intermediate", "Market & trend", "table", "catalyst",
       "Explains each mover in your file with dated news.",
       "For each stock: the most likely cause, its date, a link and HIGH, MEDIUM or LOW confidence.",
       "The file shows one day. Confirm the move happened that day.",
       "I want to understand the biggest moves in my file. The list is:\n[MOVERS]",
       "For each stock in the list, explain the most likely cause of its move on the file date, checking news, filings, "
       "analyst actions and scheduled events from that day and the day before.",
       "A learner who wants to know why prices move.", "A table, then one lesson sentence per stock.",
       ["HIGH needs a filing or major outlet. MEDIUM needs one reliable source. LOW means social media only.",
        "If no cause can be verified, write NOT FOUND and say the move may be market-wide noise."], needs=["movers"]),

    _q("analysts", "🎯", "Analyst & Expert Views", "Beginner", "Analysts & investors", "table", "sentiment",
       "What credible professionals think, with dates, so you see who agrees.",
       "Named firms with positive, neutral or negative views and an agreement count.",
       "Price targets are opinions. Check when each was published.",
       "I want to know what credible professionals said about [COMPANY] ([TICKER]) recently.",
       "List brokerage research and respected financial journalists who published a view in the last 90 days: firm, date, "
       "rating, any price target, and link. End with how many agree.",
       "A beginner.", "Table first, then a two-sentence summary.",
       ["Only views dated within 90 days, each with a named firm or author.", "Price targets are opinions. Say so in each row."],
       src="Original"),

    _q("earnings", "📅", "Earnings & Upcoming Events", "Beginner", "Company", "custom", "catalyst",
       "When the next test happens and what the market expects from it.",
       "Next report date marked CONFIRMED or ESTIMATED, expectations, last reaction, 90-day events.",
       "Data-site dates are often estimates. Check the company's own announcement.",
       "I want to understand the next earnings report for [COMPANY] ([TICKER]).",
       "Give the next report date, the revenue and earnings per share analysts expect, what the company said about the coming "
       "quarter, how the stock reacted to the last report, and other dated events in 90 days.",
       "A beginner.", "Calendar-style list, dates first.",
       ["Mark the date CONFIRMED if the company announced it, otherwise ESTIMATED.",
        "Give consensus figures with the publisher named."]),

    _q("health", "🏥", "Company Health (Financials)", "Beginner", "Company", "custom", "fundamentals",
       "Does the business make money, turn profit into cash, and carry manageable debt?",
       "Status for growth, profit, cash and debt, each with an everyday analogy.",
       "Profit and cash can differ. The question asks for both on purpose.",
       "I want to judge whether [COMPANY] ([TICKER]) is financially healthy.",
       "Explain what it sells and to whom, whether revenue grows over 1 and 3 years, whether profit turns into cash, how much "
       "debt it carries against cash, and how its valuation compares with its industry.",
       "A beginner who has never read a balance sheet.", "One everyday analogy per concept.",
       ["State the reporting period for every number.", "Name any debt due inside 12 months with its filing section."]),

    _q("trend", "📈", "Price Trend (Chart Check)", "Intermediate", "Market & trend", "table", "technical",
       "The direction and strength of the price, without predicting levels.",
       "A table of indicators with readings and what each means in plain words.",
       "Indicators describe the past. They do not prove what comes next.",
       "I want to read the price trend of [COMPANY] ([TICKER]) without predicting exact prices.",
       "Describe the trend over 1, 3 and 12 months, the position against the 50-day and 200-day averages, RSI and MACD, "
       "volume against price, and the comparison with the market index.",
       "A beginner who has seen charts.", "Explain each term in one line.",
       ["Use dated price data only, and say if it is delayed.", "Give no price targets."]),

    _q("direction", "🧭", "Will It Rise? Direction Report", "Beginner", "Start here", "standard", "thesis",
       "A lean with the reasons for and against, so you learn to weigh evidence.",
       "A summary, facts table, reasons for and against, and one question for you.",
       "A lean is not a promise. Check the date of every fact.",
       "I am deciding whether [COMPANY] ([TICKER]) deserves more attention over a [HORIZON] horizon. My risk comfort is [RISK].",
       "Answer one question: over this horizon, is the stock more likely to rise or fall, and how sure are you? Weigh news, "
       "the latest result, analyst views, financial health and the price trend.",
       "A smart beginner who wants to judge evidence.", "Balanced. Teach the reasoning.",
       ["Give the lean as UP, MIXED or DOWN, a confidence word, and the one fact that would change it.",
        "List at least two dated facts against the lean."]),

    _q("risks", "🧨", "Risk & Dilution Check", "Intermediate", "Risk", "custom", "risk",
       "The downside traps: new shares, debt due soon, legal cases, expectations already high.",
       "A risk table with severity and the dated filing behind each risk.",
       "No risk list is complete. Missing evidence appears as NOT FOUND.",
       "I want the honest downside of [COMPANY] ([TICKER]).",
       "List the biggest current red flags: new share issuance, debt due soon, legal or regulatory cases, customer concentration, "
       "falling margins, insider selling, going-concern warnings, and a valuation that assumes great results.",
       "A beginner who wants to avoid obvious traps.", "Direct and sober.",
       ["Give each risk LOW, MEDIUM or HIGH, with its reason and filing.", "Mark an unchecked category NOT FOUND."]),

    _q("redflag", "🚩", "Financial Red-Flag Scanner", "Intermediate", "Risk", "custom", "fundamentals",
       "Reads an annual report like an auditor looking for problems.",
       "Flags, each with severity, filing section and a follow-up question.",
       "A flag is a question to investigate, not proof of wrongdoing.",
       "I want to check [COMPANY] ([TICKER]) for accounting and balance-sheet warning signs in its latest annual report.",
       "Find warning signs a careful analyst should investigate: revenue quality, margin compression, receivables or inventory "
       "growing faster than revenue, debt and covenants, accounting policy changes, defensive language, auditor opinion or changes.",
       "A learner who reads filings sceptically.", "Direct and neutral. No accusations.",
       ["Name the filing section and year for every flag.", "Write NOT FOUND for any area with no filing section."],
       src="Adapted from AI Investing Lab (2026)"),

    _q("steelman", "⚖️", "Bull vs Bear Steel-Man", "Intermediate", "Risk", "custom", "thesis",
       "The strongest honest case for both sides, so your own view is tested.",
       "A bull case and a bear case, each as strong as its believers would make it.",
       "Strong does not mean true. Check each claim against its source.",
       "I am considering [COMPANY] ([TICKER]). My current view: [THESIS]",
       "Write the strongest bull case a believer would make, then the strongest bear case a sceptic would make. Finish with "
       "3 to 5 dated events to monitor over 12 months.",
       "A learner testing their own idea.", "Persuasive within each case, honest about evidence.",
       ["Write the two cases separately. Do not blend them.", "Each case needs at least two graded sources."],
       src="Adapted from AI Investing Lab (2026)", needs=["thesis"]),

    _q("challenge", "🥊", "Challenge My Idea", "Advanced", "Risk", "custom", "thesis",
       "Tries to prove your view wrong, to reduce confirmation bias.",
       "The strongest case against you, three facts that would prove you wrong, and a trigger to reconsider.",
       "Do not let the counter-case replace your judgement. Weigh it.",
       "I believe [COMPANY] ([TICKER]) will do well because: [THESIS]",
       "Try hard to prove me wrong using verified, dated facts. Give the strongest case against my view, three facts that would "
       "show I am wrong, and the price move or event that should make me reconsider.",
       "A learner who wants to avoid confirmation bias.", "Respectful, direct and specific.",
       ["Use only verified, dated facts against my view.", "Name a trigger price or event with its source."], needs=["thesis"]),

    _q("insiders", "🕵️", "Insider & Big-Investor Filings", "Intermediate", "Analysts & investors", "table", "scan",
       "What insiders and large funds have filed, with the built-in delay.",
       "Filings with person or fund, action, size, trade date, filing date and link.",
       "A 13F is a snapshot up to 45 days old. It is not a live trade feed.",
       "I want to know what insiders and large investors have done with [COMPANY] ([TICKER]).",
       "List insider buys and sells (SEC Form 4) and changes in large fund holdings (SEC 13F), with the person or fund, action, "
       "size, trade date, filing date and link.",
       "A beginner.", "Table, then a plain note on what the filings can and cannot show.",
       ["Give both trade date and filing date.", "A filing does not prove a future move."]),

    _q("social", "📱", "Social & Video Pulse", "Beginner", "Analysts & investors", "table", "sentiment",
       "What creators and investors say, as links to review, with how much to trust each.",
       "Videos and posts with date, creator, tone, main claim, disclosure and link.",
       "Popular is not correct. Check whether the poster owns the stock.",
       "I want to see what investors and creators say about [COMPANY] ([TICKER]), and how much to trust it.",
       "Find up to 6 recent videos and up to 6 public discussions about [COMPANY] ([TICKER]) from the last 30 days. For each give "
       "date, creator, tone, main claim, whether the poster discloses owning the stock, and the link.",
       "A beginner who wants the crowd's mood without being led by it.", "Two tables and a short tone count.",
       ["Every claim is UNVERIFIED unless a reliable source confirms it.", "Name public posts only. No private accounts."]),

    _q("moat", "🏰", "Competitive Moat Test", "Intermediate", "Company", "custom", "moat",
       "Whether the advantage lasts long enough to matter over ten years.",
       "Moat type, a wide, narrow or weak rating, and the threats to it.",
       "Famous companies can lose their moats.",
       "I want to know whether [COMPANY] ([TICKER]) has a durable competitive advantage.",
       "Name the moat type, rate its strength, assess its durability over ten years, and compare it with two named peers.",
       "A learner building a long-term view.", "A table first, then the reasoning.",
       ["Give the evidence for the rating.", "Name each threat with its source."],
       src="Adapted from AI Academy by Techpresso (2026)"),

    _q("sector", "🗺️", "Sector Thesis", "Intermediate", "Market & trend", "custom", "sector",
       "Whether the sector wind is in your favour, and whether a fund may suit you better.",
       "Growth drivers, headwinds, a valuation check, and fund versus single-stock trade-offs.",
       "Sector cycles reverse. Check how the sector behaved in its last downturn.",
       "I want to know whether the [SECTOR] sector is a good place to look for investments.",
       "Cover the growth drivers over five years, the headwinds, the three to five leading companies and why, valuation against "
       "history, past cycles, and a sector fund versus single stocks.",
       "A learner choosing where to look first.", "Sectioned, with a dated source per section.",
       ["Name each industry report and its date.", "Give no stock picks unless asked."],
       src="Adapted from AI Academy by Techpresso (2026)", needs=["sector"]),

    _q("disrupt", "🛰️", "Industry Disruption Scan", "Advanced", "Market & trend", "custom", "sector",
       "Technologies and models that could reshape an industry over 5 to 10 years.",
       "Each risk with its mechanism, named companies, a time estimate and vulnerable or resilient labels.",
       "Timelines are estimates. Ask for the source behind each one.",
       "I am researching the [SECTOR] industry to see which incumbents may be exposed to change.",
       "Identify credible disruption risks over 5 to 10 years. For each give the mechanism, the companies or technologies driving "
       "it, the time to impact, and which incumbents are vulnerable or resilient.",
       "An intermediate learner who thinks like a strategist.", "Concrete, with examples.",
       ["Label every timeline ESTIMATE with its basis.", "Avoid generic claims such as digital transformation."],
       src="Adapted from AI Investing Lab (2026)", needs=["sector"]),

    _q("compare", "⚔️", "Compare Two Stocks", "Beginner", "Company", "table", "scan",
       "Trade-offs side by side, so you see which company is stronger on which measure.",
       "A table with a winner on each measure, and where each is stronger.",
       "Compare companies in the same sector. Different industries are hard to compare fairly.",
       "I am comparing [TICKER] and [TICKER2] to understand the trade-offs.",
       "Build a side-by-side table of business, recent growth, profitability, debt, valuation, analyst consensus and one-year "
       "price change. Say which is stronger on the facts and which carries more risk.",
       "A beginner.", "Table first, then trade-offs in plain words.",
       ["Use the same measure and the same date for both.", "Say which is stronger on the facts, not which to buy."],
       needs=["ticker2"]),

    _q("options", "🎲", "Options Market Explained", "Advanced", "Advanced", "custom", "technical",
       "What the options market says about expected moves, in plain English.",
       "The implied move, whether options look cheap or expensive, and the main risk of each option type.",
       "Option prices change every minute. Every number needs a timestamp.",
       "I want to understand what the options market says about [COMPANY] ([TICKER]), for learning only.",
       "Explain the move priced into options for the next event, whether options look expensive or cheap against their own "
       "history, and the main risk of each option type.",
       "An advanced learner who knows what an option is.", "Precise. Define each term once.",
       ["Timestamp every option price and say if it is delayed.", "Do not recommend a contract, strike or trade."]),

    _q("research360", "🌐", "360° Complete Research", "Advanced", "Start here", "full360", "full",
       "One long answer that checks everything that can move a stock.",
       "A verdict card where every area shows UP, MIXED, DOWN or NOT FOUND, with a date and link.",
       "The largest answer is the easiest to over-trust. Verify its top three claims yourself.",
       "I want a complete, honest picture of [COMPANY] ([TICKER]) before deciding anything. My horizon is [HORIZON] and my risk "
       "comfort is [RISK].",
       "Cover fundamentals, technicals, 30-day news, catalysts, the last result and guidance, lawsuits and regulation, macro and "
       "tariff exposure, peers and sector, analyst ratings, and social tone.",
       "A learner who understands each part and wants the whole picture.",
       "Clear and organised. The verdict card must read at a glance.",
       ["Give every area a status icon and word, a date and a link.", "Name your top three claims and which to verify first."]),
]

for _i, _p in enumerate(PROMPTS, start=1):
    _p["rank"] = _i


def get_prompt(pid):
    return next(p for p in PROMPTS if p["id"] == pid)


def build_prompt(p, ticker, company, horizon, risk, extra):
    """Full research brief: role, mission, data contract, protocol, grades, quality gate,
    output contract, rules and layout. Paste the whole text into the AI."""
    extra = extra or {}
    subs = {
        "[TICKER]": ticker or "[TICKER]",
        "[COMPANY]": company or ticker or "[COMPANY]",
        "[HORIZON]": horizon,
        "[RISK]": risk,
        "[THESIS]": extra.get("thesis") or "[WRITE YOUR IDEA IN ONE SENTENCE]",
        "[TICKER2]": extra.get("ticker2") or "[SECOND TICKER]",
        "[SECTOR]": extra.get("sector") or "[ENTER SECTOR OR INDUSTRY]",
        "[MOVERS]": extra.get("movers") or "[PASTE THE MOVERS LIST]",
    }

    def fill(text):
        for k, v in subs.items():
            text = text.replace(k, str(v))
        return text

    proto_name, steps = PROTOCOLS[p["protocol"]]
    protocol = "PROTOCOL: " + proto_name + "\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    own = "QUESTION RULES\n" + "\n".join("- " + r for r in p["rules"])

    role = ("ROLE: You are a careful equity research analyst with a scientist's habits. "
            "Your goal is to be correct and honest, not confident. Say 'I could not verify this' when that is true.")
    data = ("DATA CONTRACT: Use only facts you can open and date. Use the file snapshot as a dated reference, "
            "and verify the live price before using it. Anything older than the time frame, or any claim you "
            "cannot open, is grade D or NOT FOUND.")
    contract = ("OUTPUT CONTRACT: Before the answer, write one line titled CHECKS RUN that lists the quality-gate "
                "checks you completed and any you could not. Then give the answer in the layout below. "
                "End with a numbered sources list: grade, publisher, date, link.")

    parts = [
        role,
        "MISSION: " + fill(p["context"]) + " " + fill(p["objective"]),
        data,
        protocol,
        "AUDIENCE: " + p["audience"] + " STYLE: " + p["style"],
        own,
        RULES,
        EVIDENCE,
        QUALITY_GATE,
        contract,
        ICON_LEGEND,
        LAYOUTS[p["fmt"]],
    ]
    return "\n\n".join(parts)


def build_link(p, ticker, company=""):
    """Build a short, question-specific instruction for the AI editor URL.

    The complete prompt is too long for many URL prefill fields. The UI copies
    that complete prompt separately; the user must paste it into the external AI
    chat and press Send. This helper deliberately does not claim to submit it.
    """
    ticker = (ticker or "").strip().upper()
    company = (company or ticker or "the selected company").strip()
    task = p.get("name", "Research task")
    objective = p.get("objective", "").strip()

    # Replace common placeholders so the prefilled instruction is specific too.
    replacements = {
        "[TICKER]": ticker or "the selected ticker",
        "[COMPANY]": company,
        "[HORIZON]": "the selected time horizon",
        "[RISK]": "the selected risk comfort",
        "[THESIS]": "the thesis supplied in the full brief",
        "[TICKER2]": "the second ticker supplied in the full brief",
        "[SECTOR]": "the sector supplied in the full brief",
        "[MOVERS]": "the mover list supplied in the full brief",
    }
    for token, value in replacements.items():
        objective = objective.replace(token, value)

    subject = f"{ticker} ({company})" if ticker else "the selected stock list"
    return (
        f"Task: {task}. Subject: {subject}. "
        f"Goal: {objective} "
        "I am now pasting the complete research brief, which contains the controlling "
        "protocol, question-specific rules, evidence grades, quality checks and output format. "
        "Follow that full brief exactly. Do not substitute a generic stock summary. "
        "Use dated sources and links; write NOT FOUND when evidence cannot be verified. "
        "Research and education only; not financial advice."
    )

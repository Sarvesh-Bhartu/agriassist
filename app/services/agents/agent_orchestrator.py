"""
LangChain-powered Agent Orchestrator.

Architecture:
  1. Each of the 5 analysis agents is registered as a LangChain @tool.
  2. A LangChain agent (using Gemini via google-generativeai + ChatGoogleGenerativeAI-compatible
     wrapper) receives the admin query, decides which tools to call, and calls them.
  3. Every step — tool selection, tool execution, result summary — is streamed as SSE events
     so the chat front-end can show Perplexity-style live progress.

NOTE: langchain_google_genai is NOT installed.  We use the google-generativeai SDK directly
      to do the tool-routing decision, then delegate execution to LangChain tool wrappers.
      This gives us full LangChain Tool introspection (name / description / args_schema)
      while keeping Gemini as the decision engine.
"""
from __future__ import annotations

import json
import asyncio
from typing import AsyncGenerator, Any

# ── LangChain imports ─────────────────────────────────────────────────────
from langchain_core.tools import tool as lc_tool
from langchain_core.tools import BaseTool
import langchain_core.globals as lc_globals

# Fix for "module 'langchain' has no attribute 'debug'"
# This happens because some internal langchain-core logic checks for the global debug flag
# in the 'langchain' package, which may be missing or mismatched in the environment.
try:
    import langchain
    if not hasattr(langchain, "debug"):
        langchain.debug = False
except ImportError:
    import sys
    from types import ModuleType
    m = ModuleType("langchain")
    m.debug = False
    sys.modules["langchain"] = m

# Explicitly disable debug in langchain-core globals
lc_globals.set_debug(False)


# ── Gemini direct SDK ─────────────────────────────────────────────────────
import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
_gemini = genai.GenerativeModel("gemini-2.5-flash")

# We store the DB session in a thread-local so the stateless LangChain tools
# can access it without passing it as an argument (LangChain tool signatures
# must match JSON schema exactly and cannot accept SQLAlchemy sessions).
import threading
_local = threading.local()


def _get_db():
    return getattr(_local, "db", None)


# ══════════════════════════════════════════════════════════════════════════
#  LangChain Tool Definitions  (one per agent)
# ══════════════════════════════════════════════════════════════════════════

@lc_tool
def portfolio_analysis_tool(dummy: str = "") -> str:
    """
    Analyzes the complete farmer and farm portfolio.
    Use this tool when the query is about platform overview, total land area,
    carbon credits, soil type distribution, top farmers, or general business
    intelligence / KPI reporting.
    Returns: JSON string with BI report (executive_summary, insights, health_score).
    """
    db = _get_db()
    if db is None:
        return json.dumps({"error": "No DB session available"})
    from app.services.agents.agent_portfolio import run_portfolio_analysis_agent
    result = run_portfolio_analysis_agent(db)
    a = result.get("analysis", {})
    r = result.get("raw_data", {})
    return json.dumps({
        "agent": "portfolio",
        "health_score": a.get("portfolio_health_score"),
        "executive_summary": a.get("executive_summary"),
        "top_insights": a.get("top_insights", [])[:4],
        "recommendations": a.get("recommendations", [])[:3],
        "risks": a.get("risks", [])[:3],
        "raw": {
            "total_farmers": r.get("total_farmers"),
            "total_farms": r.get("total_farms"),
            "total_area_hectares": r.get("total_area_hectares"),
            "total_carbon_credits": r.get("total_carbon_credits"),
            "verification": r.get("verification"),
        }
    }, ensure_ascii=False)


@lc_tool
def personalized_campaigns_tool(dummy: str = "") -> str:
    """
    Identifies cross-sell and upsell opportunities for individual farmers.
    Use this tool when the query is about campaigns, marketing, targeted messages,
    farmer engagement scoring, cross-sell, upsell, or personalized outreach.
    Returns: JSON string with farmer campaign suggestions and platform campaign ideas.
    """
    db = _get_db()
    if db is None:
        return json.dumps({"error": "No DB session available"})
    from app.services.agents.agent_personalized import run_personalized_agent
    result = run_personalized_agent(db, top_n=8)
    c = result.get("campaigns", {})
    return json.dumps({
        "agent": "personalized",
        "summary": c.get("summary"),
        "farmer_campaigns": c.get("farmer_campaigns", [])[:6],
        "platform_campaigns": c.get("platform_campaigns", []),
    }, ensure_ascii=False)


@lc_tool
def retention_analysis_tool(dummy: str = "") -> str:
    """
    Identifies at-risk farmers who may churn or become inactive.
    Use this tool when the query is about farmer retention, at-risk farmers,
    inactive users, churn, breakthrough areas, or regional concentration of problems.
    Returns: JSON string with risk summary, breakthrough areas, and individual actions.
    """
    db = _get_db()
    if db is None:
        return json.dumps({"error": "No DB session available"})
    from app.services.agents.agent_retention import run_retention_agent
    result = run_retention_agent(db)
    r = result.get("retention_plan", {})
    s = result.get("risk_summary", {})
    return json.dumps({
        "agent": "retention",
        "risk_summary": s,
        "overall_health": r.get("overall_retention_health"),
        "summary": r.get("summary"),
        "churn_patterns": r.get("churn_patterns", []),
        "breakthrough_areas": r.get("breakthrough_areas", [])[:5],
        "individual_actions": r.get("individual_actions", [])[:5],
    }, ensure_ascii=False)


@lc_tool
def crop_advisor_audit_tool(dummy: str = "") -> str:
    """
    Audits the quality of crop recommendations given to farmers.
    Use this tool when the query is about crop advice quality, which crops are
    performing well or poorly, market alignment of suggestions, or advisory improvements.
    Returns: JSON string with advisory quality score, top/under-performing crops, improvements.
    """
    db = _get_db()
    if db is None:
        return json.dumps({"error": "No DB session available"})
    from app.services.agents.agent_crop_advisor import run_crop_advisor_audit_agent
    result = run_crop_advisor_audit_agent(db)
    a = result.get("audit_report", {})
    r = result.get("raw_data", {})
    return json.dumps({
        "agent": "crop_advisor",
        "advisory_quality_score": a.get("advisory_quality_score"),
        "summary": a.get("summary"),
        "top_performing_crops": a.get("top_performing_crops", [])[:4],
        "underperforming_crops": a.get("underperforming_crops", [])[:4],
        "advisory_improvements": a.get("advisory_improvements", [])[:4],
        "raw": {
            "total_crop_records": r.get("total_crop_records"),
            "profitable_count": r.get("profitable_count"),
            "loss_count": r.get("loss_count"),
        }
    }, ensure_ascii=False)


@lc_tool
def data_visualization_tool(chart_query: str = "all") -> str:
    """
    Generates charts and heatmaps from the live database.
    Use this tool when the query asks for charts, graphs, heatmaps, visual data,
    soil distribution plots, carbon credit graphs, farmer activity maps, or land size visuals.
    The chart_query parameter should be the user's original question or 'all' for all charts.
    Returns: JSON string with chart images (base64) and AI narrative.
    """
    db = _get_db()
    if db is None:
        return json.dumps({"error": "No DB session available"})
    from app.services.agents.agent_visualization import run_visualization_agent
    result = run_visualization_agent(db, query=chart_query or "all")
    charts_meta = [
        {"label": c["label"], "has_image": bool(c.get("image")), "image": c.get("image")}
        for c in result.get("charts", [])
    ]
    return json.dumps({
        "agent": "visualization",
        "ai_narrative": result.get("ai_narrative"),
        "charts": charts_meta,
    }, ensure_ascii=False)


# ── Tool registry (for display metadata) ──────────────────────────────────
ALL_TOOLS: list[BaseTool] = [
    portfolio_analysis_tool,
    personalized_campaigns_tool,
    retention_analysis_tool,
    crop_advisor_audit_tool,
    data_visualization_tool,
]

TOOL_META = {
    "portfolio_analysis_tool":    {"icon": "📊", "label": "Portfolio Analysis"},
    "personalized_campaigns_tool": {"icon": "🎯", "label": "Personalized Campaigns"},
    "retention_analysis_tool":    {"icon": "🔄", "label": "Retention Analysis"},
    "crop_advisor_audit_tool":    {"icon": "🌾", "label": "Crop Advisor Audit"},
    "data_visualization_tool":   {"icon": "📈", "label": "Data Visualization"},
}


# ══════════════════════════════════════════════════════════════════════════
#  Gemini-powered Tool Router  (replaces LangGraph / ReAct agent)
#  Uses LangChain tool schemas for structured selection
# ══════════════════════════════════════════════════════════════════════════

def _build_tool_catalogue() -> str:
    """Build a human-readable tool catalogue from LangChain tool metadata."""
    lines = []
    for t in ALL_TOOLS:
        lines.append(f'  - tool_name: "{t.name}"\n    description: {t.description.strip()[:200]}')
    return "\n".join(lines)


def _gemini_select_tools(query: str) -> list[dict]:
    """
    Ask Gemini to select which LangChain tools to call and with what arguments.
    Returns a list of {"tool_name": str, "args": dict} dicts.
    """
    catalogue = _build_tool_catalogue()
    prompt = f"""You are an intelligent tool router for an agricultural admin platform.

Available LangChain tools:
{catalogue}

Admin query: "{query}"

Select 1-3 tools to call to best answer this query. For data_visualization_tool, set
chart_query to the user's question about visuals. For all other tools use an empty string
for the dummy parameter.

Return ONLY a valid JSON array. Example:
[
  {{"tool_name": "portfolio_analysis_tool", "args": {{"dummy": ""}}}},
  {{"tool_name": "retention_analysis_tool", "args": {{"dummy": ""}}}}
]

Raw JSON only, no markdown fences.
"""
    try:
        resp = _gemini.generate_content(prompt)
        text = resp.text.strip().replace("```json", "").replace("```", "").strip()
        selected = json.loads(text)
        # Validate tool names
        valid_names = {t.name for t in ALL_TOOLS}
        return [s for s in selected if s.get("tool_name") in valid_names][:3]
    except Exception as e:
        return [{"tool_name": "portfolio_analysis_tool", "args": {"dummy": ""}}]


def _execute_tool(tool_name: str, args: dict) -> Any:
    """Find and invoke a LangChain tool by name."""
    for t in ALL_TOOLS:
        if t.name == tool_name:
            return t.invoke(args)
    return json.dumps({"error": f"Tool {tool_name} not found"})


def _execute_tool_with_db(tool_name: str, args: dict, db) -> Any:
    """Wrapper to ensure DB session is set in the executor thread's local storage."""
    _local.db = db
    return _execute_tool(tool_name, args)


def _synthesize_with_langchain_results(query: str, tool_results: list[dict]) -> str:
    """Gemini synthesizes a final answer from all tool outputs."""
    combined = "\n\n".join(
        f"[{r['label']} tool result]\n{r['raw_output'][:600]}"
        for r in tool_results
    )
    prompt = f"""You are an expert agricultural admin assistant for 'AgriAssist' in India.

Admin asked: "{query}"

LangChain tool outputs:
{combined}

Write a clear, concise, actionable response (150-250 words). Use numbers from the data.
Be conversational but professional. Use bullet points where helpful.
Plain text only, no markdown headers.
"""
    try:
        resp = _gemini.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        return f"Analysis complete. (Synthesis error: {e})"


# ══════════════════════════════════════════════════════════════════════════
#  SSE Streaming Orchestrator
# ══════════════════════════════════════════════════════════════════════════

def emit(data: dict) -> str:
    """Helper to format a dictionary as an SSE data block."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

async def stream_orchestrator(query: str, db) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE data lines.
    SSE event types:
      thinking   — step description text
      tool_list  — all available LangChain tools (for display)
      tool_pick  — which tools were selected (with args)
      tool_start — a specific tool is now running
      tool_done  — tool finished (with summary)
      chart      — base64 chart image from visualization tool
      answer     — final synthesized answer text
      done       — stream complete
    """

    # Store DB in thread-local for tools to access
    _local.db = db

    # ── Step 1: Announce available tools ─────────────────────────────────
    yield emit({"type": "thinking", "text": f'Received query: "{query}"'})
    await asyncio.sleep(0.05)

    tools_info = [
        {
            "name": t.name,
            "label": TOOL_META.get(t.name, {}).get("label", t.name),
            "icon": TOOL_META.get(t.name, {}).get("icon", "🔧"),
            "description": (t.description or "")[:120].strip()
        }
        for t in ALL_TOOLS
    ]
    yield emit({"type": "tool_list", "tools": tools_info})
    yield emit({"type": "thinking", "text": f"Loaded {len(ALL_TOOLS)} LangChain tools — asking Gemini to select the best ones..."})
    await asyncio.sleep(0.05)

    # ── Step 2: Tool Selection via Gemini + LangChain schemas ─────────────
    loop = asyncio.get_event_loop()
    selected_calls = await loop.run_in_executor(None, _gemini_select_tools, query)

    if not selected_calls:
        yield emit({"type": "thinking", "text": "No suitable tools found, falling back to portfolio overview."})
        selected_calls = [{"tool_name": "portfolio_analysis_tool", "args": {"dummy": ""}}]

    # Emit which tools were picked (with labels and args)
    picked_display = []
    for sc in selected_calls:
        tn = sc["tool_name"]
        meta = TOOL_META.get(tn, {"icon": "🔧", "label": tn})
        args_clean = {k: v for k, v in sc.get("args", {}).items() if v and k != "dummy"}
        picked_display.append({
            "tool_name": tn,
            "label": meta["label"],
            "icon": meta["icon"],
            "args": args_clean
        })

    yield emit({"type": "tool_pick", "selected": picked_display})
    names_str = ", ".join(f"{p['icon']} {p['label']}" for p in picked_display)
    yield emit({"type": "thinking", "text": f"LangChain selected {len(selected_calls)} tool(s): {names_str}"})
    await asyncio.sleep(0.05)

    # ── Step 3: Execute Selected Tools ───────────────────────────────────
    all_results = []
    for sc in selected_calls:
        tn = sc["tool_name"]
        args = sc.get("args", {})
        meta = TOOL_META.get(tn, {"icon": "🔧", "label": tn})
        label = meta["label"]
        icon = meta["icon"]

        yield emit({"type": "tool_start", "tool_name": tn, "label": label, "icon": icon,
                    "args": {k: v for k, v in args.items() if v and k != "dummy"}})
        yield emit({"type": "thinking", "text": f"Executing {icon} {label} — querying database..."})
        await asyncio.sleep(0.05)

        try:
            raw_output = await loop.run_in_executor(None, _execute_tool_with_db, tn, args, db)
            result_data = json.loads(raw_output) if isinstance(raw_output, str) else raw_output

            # Extract a one-line summary
            summary = _tool_summary(tn, result_data)

            yield emit({"type": "tool_done", "tool_name": tn, "label": label, "icon": icon,
                        "summary": summary, "error": False})

            all_results.append({"tool_name": tn, "label": label, "icon": icon,
                                 "raw_output": raw_output, "data": result_data})

            # Stream charts if visualization tool
            if tn == "data_visualization_tool":
                for chart in result_data.get("charts", []):
                    if chart.get("image"):
                        yield emit({"type": "chart", "label": chart["label"], "image": chart["image"]})
                    await asyncio.sleep(0.02)

        except Exception as e:
            yield emit({"type": "tool_done", "tool_name": tn, "label": label, "icon": icon,
                        "summary": f"Error: {str(e)[:80]}", "error": True})

        await asyncio.sleep(0.05)

    # ── Step 4: Synthesize Final Answer ──────────────────────────────────
    yield emit({"type": "thinking", "text": "Synthesizing final answer from all tool results..."})
    await asyncio.sleep(0.05)

    final_answer = await loop.run_in_executor(None, _synthesize_with_langchain_results, query, all_results)
    yield emit({"type": "answer", "text": final_answer})
    yield emit({"type": "done"})

    # Cleanup
    _local.db = None


def _tool_summary(tool_name: str, data: dict) -> str:
    if tool_name == "portfolio_analysis_tool":
        score = data.get("health_score", "?")
        n = len(data.get("top_insights", []))
        return f"Health score {score}/100 · {n} insights found"
    elif tool_name == "personalized_campaigns_tool":
        n = len(data.get("farmer_campaigns", []))
        return f"{n} farmer campaigns identified"
    elif tool_name == "retention_analysis_tool":
        s = data.get("risk_summary", {})
        return f"{s.get('critical_high', 0)} critical/high risk farmers · Health: {data.get('overall_health', '?')}"
    elif tool_name == "crop_advisor_audit_tool":
        score = data.get("advisory_quality_score", "?")
        return f"Advisory quality: {score}/100"
    elif tool_name == "data_visualization_tool":
        n = sum(1 for c in data.get("charts", []) if c.get("has_image"))
        return f"{n} chart(s) generated successfully"
    return "Completed"

"""
Agent 5: Data Visualization Agent
Converts natural language queries into heatmap charts and analysis images
using matplotlib/numpy. Returns base64-encoded PNG images.
"""
import json
import io
import base64
from datetime import datetime
from collections import Counter, defaultdict
from sqlalchemy.orm import Session
from app.models.user import Farmer
from app.models.farm import Farm
from app.models.crop import Crop, MarketPrice
from app.models.gamification import GamificationEvent
import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.5-flash")

# ── Matplotlib imports (already available via numpy/pillow stack) ─
try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend for server use
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def _encode_fig(fig) -> str:
    """Encode a matplotlib figure to base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110, facecolor=fig.get_facecolor())
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"


def _chart_soil_distribution(db: Session) -> str:
    farms = db.query(Farm).all()
    soil_counts = Counter(f.soil_type for f in farms if f.soil_type)
    if not soil_counts or not MATPLOTLIB_AVAILABLE:
        return None
    labels = list(soil_counts.keys())
    values = list(soil_counts.values())
    colors = ["#4ade80", "#22d3ee", "#f59e0b", "#f87171", "#a78bfa", "#fb923c"][:len(labels)]
    fig, ax = plt.subplots(figsize=(7, 4), facecolor="#f0fdf4")
    ax.set_facecolor("#f0fdf4")
    bars = ax.barh(labels, values, color=colors, edgecolor="white", linewidth=1.5)
    ax.bar_label(bars, padding=4, fontsize=10, color="#166534", fontweight="bold")
    ax.set_title("Soil Type Distribution Across Farms", fontsize=13, color="#166534", fontweight="bold", pad=10)
    ax.set_xlabel("Number of Farms", color="#4b5563")
    ax.tick_params(colors="#4b5563")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return _encode_fig(fig)


def _chart_carbon_by_soil(db: Session) -> str:
    farms = db.query(Farm).all()
    by_soil: dict = defaultdict(list)
    for f in farms:
        if f.soil_type and f.carbon_credits_annual:
            by_soil[f.soil_type].append(float(f.carbon_credits_annual))
    if not by_soil or not MATPLOTLIB_AVAILABLE:
        return None
    labels = list(by_soil.keys())
    means = [sum(v) / len(v) for v in by_soil.values()]
    colors = ["#16a34a", "#0891b2", "#b45309", "#dc2626", "#7c3aed"][:len(labels)]
    fig, ax = plt.subplots(figsize=(7, 4), facecolor="#f0fdf4")
    ax.set_facecolor("#f0fdf4")
    bars = ax.bar(labels, means, color=colors, edgecolor="white", linewidth=1.5, width=0.6)
    ax.bar_label(bars, fmt="%.1f", padding=4, fontsize=9, color="#166534", fontweight="bold")
    ax.set_title("Avg Carbon Credits by Soil Type", fontsize=13, color="#166534", fontweight="bold", pad=10)
    ax.set_ylabel("Credits / Year", color="#4b5563")
    ax.tick_params(colors="#4b5563")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return _encode_fig(fig)


def _chart_verification_status(db: Session) -> str:
    farms = db.query(Farm).all()
    status_counts = Counter((f.verification_status or "no_doc") for f in farms)
    labels = {"pending": "Pending", "approved": "Approved", "rejected": "Rejected", "no_doc": "No Doc"}
    color_map = {"pending": "#f59e0b", "approved": "#22c55e", "rejected": "#ef4444", "no_doc": "#9ca3af"}
    data = [(labels.get(k, k), v, color_map.get(k, "#8b5cf6")) for k, v in status_counts.items()]
    if not data or not MATPLOTLIB_AVAILABLE:
        return None
    fig, ax = plt.subplots(figsize=(5, 5), facecolor="#f0fdf4")
    ax.set_facecolor("#f0fdf4")
    lbs = [d[0] for d in data]
    vals = [d[1] for d in data]
    cols = [d[2] for d in data]
    wedges, texts, autotexts = ax.pie(vals, labels=lbs, colors=cols, autopct="%1.0f%%",
                                       startangle=140, pctdistance=0.82, wedgeprops={"linewidth": 2, "edgecolor": "white"})
    for t in texts:
        t.set_fontsize(11)
        t.set_color("#374151")
    for at in autotexts:
        at.set_fontsize(10)
        at.set_color("white")
        at.set_fontweight("bold")
    ax.set_title("Farm Verification Status", fontsize=13, color="#166534", fontweight="bold", pad=15)
    fig.tight_layout()
    return _encode_fig(fig)


def _chart_farmer_activity_heatmap(db: Session) -> str:
    """Shows farmer engagement by day of week (from gamification events)."""
    events = db.query(GamificationEvent).all()
    if not events or not MATPLOTLIB_AVAILABLE:
        return None
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hours = list(range(0, 24, 3))  # 0,3,6,...,21
    heatmap = np.zeros((7, len(hours)))
    for e in events:
        if e.created_at:
            dow = e.created_at.weekday()
            hour_bin = e.created_at.hour // 3
            heatmap[dow][hour_bin] += 1
    fig, ax = plt.subplots(figsize=(10, 4), facecolor="#f0fdf4")
    ax.set_facecolor("#f0fdf4")
    im = ax.imshow(heatmap, cmap="YlGn", aspect="auto")
    ax.set_xticks(range(len(hours)))
    ax.set_xticklabels([f"{h:02d}:00" for h in hours], fontsize=9)
    ax.set_yticks(range(7))
    ax.set_yticklabels(days, fontsize=10)
    ax.set_title("Farmer Activity Heatmap (Day vs Time)", fontsize=13, color="#166534", fontweight="bold", pad=10)
    plt.colorbar(im, ax=ax, label="Events")
    fig.tight_layout()
    return _encode_fig(fig)


def _chart_top_farmers_bar(db: Session) -> str:
    farmers = db.query(Farmer).order_by(Farmer.total_points.desc()).limit(8).all()
    if not farmers or not MATPLOTLIB_AVAILABLE:
        return None
    names = [f.name[:12] for f in farmers]
    points = [f.total_points for f in farmers]
    colors = [f"#{hex(int(200 - i*20))[2:]:0>2}c55e" if i < 3 else "#4ade80" for i in range(len(names))]
    fig, ax = plt.subplots(figsize=(8, 4), facecolor="#f0fdf4")
    ax.set_facecolor("#f0fdf4")
    bars = ax.bar(names, points, color=["#15803d", "#16a34a", "#22c55e"] + ["#86efac"] * (len(names) - 3),
                   edgecolor="white", linewidth=1.5)
    ax.bar_label(bars, padding=3, fontsize=9, color="#166534", fontweight="bold")
    ax.set_title("Top Farmers by Engagement Points", fontsize=13, color="#166534", fontweight="bold", pad=10)
    ax.set_ylabel("Points", color="#4b5563")
    ax.tick_params(axis="x", rotation=20, colors="#4b5563")
    ax.tick_params(axis="y", colors="#4b5563")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return _encode_fig(fig)


def _chart_land_distribution(db: Session) -> str:
    """Pie chart of land size distribution buckets."""
    farms = db.query(Farm).all()
    area_data = [float(f.area_hectares or 0) for f in farms if f.area_hectares]
    if not area_data or not MATPLOTLIB_AVAILABLE:
        return None
    buckets = {"<1 Ha": 0, "1-5 Ha": 0, "5-10 Ha": 0, ">10 Ha": 0}
    for a in area_data:
        if a < 1:
            buckets["<1 Ha"] += 1
        elif a < 5:
            buckets["1-5 Ha"] += 1
        elif a < 10:
            buckets["5-10 Ha"] += 1
        else:
            buckets[">10 Ha"] += 1
    labels = list(buckets.keys())
    vals = list(buckets.values())
    colors = ["#f59e0b", "#22c55e", "#0891b2", "#8b5cf6"]
    fig, ax = plt.subplots(figsize=(5, 5), facecolor="#f0fdf4")
    wedges, texts, autotexts = ax.pie(vals, labels=labels, colors=colors, autopct="%1.0f%%",
                                       startangle=90, wedgeprops={"linewidth": 2, "edgecolor": "white"})
    for at in autotexts:
        at.set_fontsize(10)
        at.set_color("white")
        at.set_fontweight("bold")
    ax.set_title("Farm Land Size Distribution", fontsize=13, color="#166534", fontweight="bold", pad=15)
    fig.tight_layout()
    return _encode_fig(fig)


# ── Catalogue of available charts ──────────────────────────────────────────
CHART_CATALOGUE = {
    "soil_distribution": {
        "label": "Soil Type Distribution",
        "description": "Bar chart of soil types across all farms",
        "fn": _chart_soil_distribution,
    },
    "carbon_by_soil": {
        "label": "Carbon Credits by Soil Type",
        "description": "Average carbon credits grouped by soil type",
        "fn": _chart_carbon_by_soil,
    },
    "verification_status": {
        "label": "Verification Status Pie",
        "description": "Pie chart of farm document verification statuses",
        "fn": _chart_verification_status,
    },
    "activity_heatmap": {
        "label": "Farmer Activity Heatmap",
        "description": "Heatmap showing when farmers are most active (day vs hour)",
        "fn": _chart_farmer_activity_heatmap,
    },
    "top_farmers": {
        "label": "Top Farmers by Points",
        "description": "Bar chart of top 8 farmers ranked by engagement points",
        "fn": _chart_top_farmers_bar,
    },
    "land_distribution": {
        "label": "Land Size Distribution",
        "description": "Pie chart of farm size buckets",
        "fn": _chart_land_distribution,
    },
}


def run_visualization_agent(db: Session, query: str = "all") -> dict:
    """
    Data Visualization Agent.
    - query='all': returns all charts
    - query='<natural language>': Gemini picks the best chart(s) to answer, plus gives AI narrative
    """
    if query.strip().lower() == "all":
        chart_ids = list(CHART_CATALOGUE.keys())
    else:
        # Ask Gemini which charts best answer the query
        catalogue_desc = json.dumps(
            {k: v["description"] for k, v in CHART_CATALOGUE.items()}, indent=2
        )
        pick_prompt = f"""
You are a data visualization assistant. A user asked:
"{query}"

Here are the available charts:
{catalogue_desc}

Return ONLY a JSON array of the chart IDs (from the keys above) that best answer the user's query.
Example: ["soil_distribution", "carbon_by_soil"]
Return at most 3 charts. Return as raw JSON array, no markdown.
"""
        try:
            pick_resp = _model.generate_content(pick_prompt)
            pick_text = pick_resp.text.strip().replace("```json", "").replace("```", "")
            chart_ids = json.loads(pick_text)
        except Exception:
            chart_ids = list(CHART_CATALOGUE.keys())[:2]

    # Generate the selected charts
    charts_output = []
    for cid in chart_ids:
        if cid not in CHART_CATALOGUE:
            continue
        meta = CHART_CATALOGUE[cid]
        try:
            image_b64 = meta["fn"](db)
        except Exception as e:
            image_b64 = None
        charts_output.append({
            "id": cid,
            "label": meta["label"],
            "description": meta["description"],
            "image": image_b64,
            "error": None if image_b64 else "Chart generation failed or no data available"
        })

    # Ask Gemini for a narrative analysis based on which charts were shown
    chart_labels = [c["label"] for c in charts_output]
    narrative_prompt = f"""
You are an agricultural data analyst. Based on these charts that were generated for the admin dashboard:
Charts shown: {chart_labels}
User's question was: "{query}"

Provide a short, insightful 3-4 sentence narrative explaining what the admin should take away from these visualizations,
in the context of managing an agricultural platform in India.
Be specific and actionable. Return plain text only, no JSON, no markdown.
"""
    try:
        narr_resp = _model.generate_content(narrative_prompt)
        narrative = narr_resp.text.strip()
    except Exception as e:
        narrative = f"Charts generated successfully. AI narrative unavailable: {str(e)}"

    return {
        "query": query,
        "charts": charts_output,
        "ai_narrative": narrative,
        "matplotlib_available": MATPLOTLIB_AVAILABLE,
        "catalogue": {k: {"label": v["label"], "description": v["description"]} for k, v in CHART_CATALOGUE.items()}
    }

"""
Urban Farmer Space Analysis Service
Uses Gemini Vision to analyze balcony/terrace photos and polygon markings 
to estimate:
  - Cultivable area (m²)
  - Sunlight level
  - Recommended crops (matched to season, space type)
  - Estimated carbon credit potential
  - Monthly yield estimate
"""

import json
import io
import os
from PIL import Image, ImageDraw
import google.generativeai as genai
from app.core.config import settings

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.5-flash")


def _draw_polygon_on_image(img: Image.Image, points: list[dict], width: int, height: int) -> Image.Image:
    """Draw the user's polygon on the image so Gemini can see EXACTLY the marked area."""
    overlay = img.copy().convert("RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")

    if len(points) >= 3:
        # Convert relative (0-1) coords to absolute pixel coords
        pixel_pts = [(int(p["x"] * width), int(p["y"] * height)) for p in points]
        draw.polygon(pixel_pts, fill=(204, 255, 0, 80), outline=(204, 255, 0, 255))
        for pt in pixel_pts:
            r = 6
            draw.ellipse([pt[0]-r, pt[1]-r, pt[0]+r, pt[1]+r], fill=(204, 255, 0, 255))

    # Composite back to RGB
    background = Image.new("RGB", overlay.size, (0, 0, 0))
    background.paste(overlay, mask=overlay.split()[3])
    return background


def _build_prompt(space_name: str, space_type: str, image_count: int) -> str:
    return f"""
You are an expert urban agriculture consultant analysing an Indian city rooftop/balcony photo for the 'Urban AgriAssist' platform.

**Space details:**
- Name: {space_name}
- Type: {space_type}  (balcony | terrace | window_sill | indoor)
- Images analysed: {image_count}

The image shows the user's space with a **neon-yellow polygon** overlay marking the exact planting area they want to use.

Please analyse the highlighted area and return ONLY a raw JSON object (no markdown, no backticks) with this exact structure:

{{
  "estimated_area_sqm": 6.5,
  "sunlight_level": "Full Sun | Partial Sun | Shade",
  "sunlight_hours_per_day": 5,
  "recommended_crops": [
    {{
      "name": "Cherry Tomatoes",
      "variety": "Roma VF",
      "monthly_yield_kg": 3.2,
      "difficulty": "Easy",
      "container_size_liters": 15,
      "days_to_harvest": 75
    }}
  ],
  "estimated_carbon_credits_per_year": 0.42,
  "estimated_monthly_income_inr": 640,
  "soil_recommendation": "Use a mix of cocopeat + vermicompost + perlite (50:40:10)",
  "key_tips": ["Tip 1 specific to this space type", "Tip 2"],
  "overall_suitability": "Excellent | Good | Fair | Poor",
  "suitability_reason": "A short sentence explaining why."
}}

Limits for realistic recommendations:
- Balcony: 3–20 m², max 3 crops
- Terrace: 10–100 m², max 5 crops
- Window sill: 0.5–2 m², max 2 crops
- Indoor: 1–10 m², max 3 crops
Recommend only crops feasible in containers on an Indian city rooftop (no paddy, no trees).
Carbon credits: assume 0.06 credits per m² per year (conservative).
Income: use current Mumbai/Pune market rates for vegetables/herbs.
"""


async def analyse_space(
    space_name: str,
    space_type: str,
    image_paths: list[str],
    polygons_json: str
) -> dict:
    """
    Send space images (with polygon overlay) to Gemini Vision and return structured analysis.
    
    Args:
        space_name: User-given nickname for the space
        space_type: balcony | terrace | window_sill | indoor
        image_paths: List of saved image file paths on disk
        polygons_json: JSON string of polygon points per image
    
    Returns:
        dict with analysis results or an error key
    """
    try:
        polygons = json.loads(polygons_json)
    except Exception:
        polygons = [[] for _ in image_paths]

    gemini_parts = []

    for i, img_path in enumerate(image_paths):
        if not os.path.exists(img_path):
            continue

        points = polygons[i] if i < len(polygons) else []

        with Image.open(img_path) as img:
            img = img.convert("RGB")
            w, h = img.size

            # Draw the polygon so Gemini sees the highlighted area
            if points:
                img = _draw_polygon_on_image(img, points, w, h)

            # Convert to bytes for Gemini
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            buf.seek(0)

        gemini_parts.append({
            "mime_type": "image/jpeg",
            "data": buf.read()
        })

    if not gemini_parts:
        return {"error": "No valid images found for analysis"}

    # Build the prompt
    prompt_text = _build_prompt(space_name, space_type, len(gemini_parts))

    # Assemble Gemini content parts
    content = [prompt_text] + [
        {"mime_type": p["mime_type"], "data": p["data"]}
        for p in gemini_parts
    ]

    try:
        response = _model.generate_content(content)
        result_text = response.text.strip()

        # Strip markdown wrappers if present
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]

        return json.loads(result_text.strip())

    except json.JSONDecodeError as e:
        return {"error": f"Gemini returned invalid JSON: {e}", "raw": result_text}
    except Exception as e:
        return {"error": str(e)}


def _build_plan_prompt(space_name: str, space_type: str, analysis: dict) -> str:
    return f"""
You are an expert urban garden designer. Create a detailed, step-by-step Planting Plan for this space.

**Space Context:**
- Name: {space_name}
- Type: {space_type}
- Area: {analysis.get('estimated_area_sqm')} m²
- Sunlight: {analysis.get('sunlight_level')} ({analysis.get('sunlight_hours_per_day')} hrs/day)
- Recommended Crops: {", ".join([c['name'] for c in analysis.get('recommended_crops', [])])}

**Deliverables:**
Return ONLY a raw JSON object (no markdown, no backticks) with this structure:

{{
  "name": "E.g. Monsoon Balcony Bounty",
  "total_budget_est": 1200.0,
  "expected_monthly_harvest_kg": 2.5,
  "steps": [
    {{
      "crop_name": "Tomato",
      "action": "Sow seeds",
      "week": 1,
      "description": "Plant 3 seeds in 15L container at 0.5 inch depth."
    }}
  ],
  "budget_breakdown": [
    {{
      "item": "Potting Mix (20kg)",
      "estimated_cost_inr": 450.0,
      "category": "Soil/Media"
    }}
  ],
  "layout_diagram_svg": "A string containing a simple horizontal SVG diagram showing the spatial arrangement of containers.",
  "maintenance_tips": ["Water only in the early morning", "Prune lower leaves after 4 weeks"]
}}

Specific constraints:
- Use Indian Rupee (INR) for costs.
- The SVG should be roughly 600x200 pixels, using rectangles/circles to represent pots. Label them with text.
- Ensure the steps cover at least 4 weeks of the initial setup and growth.
"""


async def generate_planting_plan(
    space_name: str,
    space_type: str,
    analysis_result: dict
) -> dict:
    """
    Generate a detailed planting plan using Gemini based on previous analysis.
    """
    prompt_text = _build_plan_prompt(space_name, space_type, analysis_result)
    
    try:
        # We can pass the analysis_result as text to give Gemini context
        response = _model.generate_content(prompt_text)
        result_text = response.text.strip()

        # Clean JSON
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]

        return json.loads(result_text.strip())

    except Exception as e:
        return {"error": str(e)}

async def chat_with_urban_ai(
    user_message: str,
    context_data: dict,
    chat_history: list = None
) -> str:
    """
    Personalized gardening chat that knows about the user's specific balcony and plans.
    """
    history = chat_history or []
    
    system_prompt = f"""
    You are 'Urban AgriAssist AI', a friendly and expert assistant for balcony and terrace gardening in Indian cities.
    
    USER'S GARDEN CONTEXT:
    - Spaces: {json.dumps(context_data.get('spaces', []))}
    - Active Plans: {json.dumps(context_data.get('plans', []))}
    
    Your goal is to provide specific, actionable advice based on THEIR context. 
    If they ask about watering, refer to their sunlight levels. 
    If they ask about pests, refer to the crops they are currently growing.
    
    Keep responses concise (max 3-4 sentences), encouraging, and expert.
    Use Hindi or English based on the user's tone. If they speak Hindi, respond in Hindi.
    """
    
    chat = _model.start_chat(history=[
        {"role": "user", "parts": [system_prompt]},
        {"role": "model", "parts": ["Understood. I am now your specialized Urban AgriAssist AI. How can I help with your balcony garden today?"]}
    ] + history)
    
    try:
        response = chat.send_message(user_message)
        return response.text
    except Exception as e:
        return f"I'm sorry, I'm having trouble connecting right now. Error: {str(e)}"

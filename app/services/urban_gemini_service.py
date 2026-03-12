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

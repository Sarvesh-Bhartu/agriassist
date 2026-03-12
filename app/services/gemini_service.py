import google.generativeai as genai
from app.core.config import settings

class GeminiService:
    """Base Gemini API service (Vision and Text)"""
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.vision_model = genai.GenerativeModel('gemini-1.5-flash')
        self.pro_model = genai.GenerativeModel('gemini-1.5-flash')
    
    def get_vision_model(self):
        """Get Gemini Vision model"""
        return self.vision_model
    
    def get_pro_model(self):
        """Get Gemini Pro model"""
        return self.pro_model

    async def identify_plant(self, image_data: bytes) -> dict:
        """Identify plant species and details using Gemini Vision."""
        try:
            import json
            import io
            from PIL import Image

            img = Image.open(io.BytesIO(image_data))
            
            prompt = """
            Analyze this image of a plant/crop. Return ONLY a valid JSON object with the following structure:
            {
                "species": "Exact Latin or common species name",
                "common_name": "Common english name",
                "local_name": "Common local/Indian name if applicable, else empty",
                "is_invasive": true/false (true if it's an invasive weed, or a severe disease/blight),
                "threat_level": "High" or "Medium" or "Low",
                "confidence": 0.95,
                "removal_method": "Detailed paragraph on how to treat or remove it (if diseased/invasive) or care instructions (if healthy)"
            }
            Ensure the response is raw JSON with no markdown formatting or backticks.
            """
            
            response = self.vision_model.generate_content([prompt, img])
            result_text = response.text.strip()
            
            # Clean possible markdown JSON wrappers
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
                
            return json.loads(result_text.strip())
            
        except Exception as e:
            print(f"Gemini Vision Error: {e}")
            return None

    async def generate_crop_recommendation(self, farm_data: dict, local_trends: dict, user_preferences: dict) -> dict:
        """Generate AI crop recommendations using Gemini with Farm data and Neo4j context."""
        try:
            import json
            
            prompt = f"""
            You are an expert Agronomist AI for the 'AgriAssist' platform in India. 
            Analyze the following data to recommend the most profitable and suitable crop for this farmer.
            
            FARMER'S FARM DATA:
            - Area: {farm_data.get('area_hectares', 'Unknown')} Hectares
            - Soil Type: {farm_data.get('soil_type', 'Unknown')}
            - Water Source: {farm_data.get('water_source', 'Unknown')}
            - Irrigation Type: {farm_data.get('irrigation_type', 'Unknown')}

            FARMER'S PREFERENCES:
            - Desired Season: {user_preferences.get('season')}
            - Investment Budget (INR): {user_preferences.get('budget')}

            ENVIRONMENTAL CONTEXT (From nearby Neo4j farms within 10km):
            - Number of nearby reporting farms: {local_trends.get('neighbor_count', 0)}
            - Regional Soil Distribution: {local_trends.get('soil_distribution', {})}
            - Average nearby farm size: {local_trends.get('average_neighbor_farm_size_hectares', 'Unknown')} ha

            Based heavily on their soil type, available water source, the season they chose, and their exact budget, recommend ONE high-yield crop and variety.
            
            IMPORTANT: Return ONLY a raw JSON object string with no markdown formatting. The JSON must EXACTLY match this structure:
            {{
                "crop": "Name of the crop (e.g., Wheat)",
                "variety": "Specific high-yield variety (e.g., HD-2967)",
                "expected_profit_min": 50000.0,
                "expected_profit_max": 75000.0,
                "investment_breakdown": {{
                    "Seeds": 5000,
                    "Fertilizer": 15000,
                    "Labor": 10000,
                    "Irrigation/Misc": 5000
                }},
                "risk_factors": ["List 2-3 risks like specific pests or weather"],
                "timeline": "e.g. 120-130 days",
                "advice": "A short, encouraging paragraph on why this is the best decision based on their local graph trends and soil."
            }}
            """
            
            response = self.pro_model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Clean possible markdown JSON wrappers
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
                
            return json.loads(result_text.strip())
            
        except Exception as e:
            import traceback
            print(f"Gemini Recommendation Error: {e}")
            try:
                print(f"RAW TEXT WAS: {result_text}")
            except:
                pass
            traceback.print_exc()
            return None

    async def generate_text_response(self, prompt: str) -> str:
        """Generate a raw text response for Voice/IVR using Gemini."""
        try:
            response = self.pro_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini Voice Response Error: {e}")
            return "माफ़ करें, अभी कोई तकनीकी समस्या है। कृपया बाद में प्रयास करें।"

# Create singleton instance
gemini_service = GeminiService()

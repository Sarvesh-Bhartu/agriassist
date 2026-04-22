import google.generativeai as genai
from app.core.config import settings
import os
import json
import httpx
import traceback
import io
from PIL import Image

class GeminiService:
    """Robust AI service with Gemini Key Rotation and Groq Fallback."""
    
    def __init__(self):
        # 1. Parse Gemini Pool from Pydantic settings
        pool_str = getattr(settings, "GEMINI_API_KEY_POOL", "")
        if pool_str is None:
            pool_str = ""
        self.keys = [k.strip() for k in pool_str.split(",") if k.strip()]
        
        if not self.keys:
            # Fallback for earlier setups without pool
            single_key = getattr(settings, "GEMINI_API_KEY", None)
            if single_key:
                self.keys = [single_key]
                
        self.current_key_idx = 0
        if self.keys:
            genai.configure(api_key=self.keys[self.current_key_idx])
            
        self.vision_model = genai.GenerativeModel('gemini-1.5-flash')
        self.pro_model = genai.GenerativeModel('gemini-1.5-flash')
        self.use_groq_exclusively = False

    def get_vision_model(self):
        """Get Gemini Vision model (Legacy getter)"""
        return self.vision_model
    
    def get_pro_model(self):
        """Get Gemini Pro model (Legacy getter)"""
        return self.pro_model

    def rotate_key(self) -> bool:
        """Rotates to the next Gemini key. Returns False if all keys exhausted."""
        if not self.keys or self.current_key_idx >= len(self.keys) - 1:
            return False # no more keys
        self.current_key_idx += 1
        print(f"QUOTA EXCEEDED! Rotating to Gemini Key #{self.current_key_idx + 1}")
        genai.configure(api_key=self.keys[self.current_key_idx])
        # Re-initialize models with new config context
        self.vision_model = genai.GenerativeModel('gemini-1.5-flash')
        self.pro_model = genai.GenerativeModel('gemini-1.5-flash')
        return True

    def reset_key_cycle(self):
        """Reset sequence after total failures to ensure next request starts fresh"""
        if self.keys:
            self.current_key_idx = 0
            genai.configure(api_key=self.keys[self.current_key_idx])
            self.vision_model = genai.GenerativeModel('models/gemini-1.5-flash')
            self.pro_model = genai.GenerativeModel('models/gemini-1.5-flash')

    async def generate_smart_text(self, prompt: str) -> str:
        """Centralized text generation with Key Rotation & Groq Fallback."""
        return await self._generate_text_with_retry(prompt)

    async def generate_smart_vision(self, prompt: str, image_data: list[bytes]) -> str:
        """Vision generation with Key Rotation. (Groq does not support vision yet)"""
        # Note: image_data is list of bytes
        parts = [prompt]
        for data in image_data:
            parts.append(Image.open(io.BytesIO(data)))
            
        while True:
            try:
                response = self.vision_model.generate_content(parts)
                return response.text.strip()
            except Exception as e:
                error_msg = str(e).lower()
                if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
                    if self.rotate_key():
                        continue
                print(f"Gemini Vision completely failed: {e}")
                raise e


    async def _call_groq_text(self, prompt: str) -> str:
        """Fallback to Groq Llama-3 API if Gemini pool is exhausted."""
        print("Switching to Groq Llama-3 API Fallback...")
        groq_api_key = getattr(settings, "GROQ_API_KEY", "")
        if groq_api_key is None:
            groq_api_key = ""
        groq_api_key = groq_api_key.strip()
        
        if not groq_api_key:
            raise Exception("No Groq API Key available for fallback.")
            
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content'].strip()

    async def _generate_text_with_retry(self, prompt: str) -> str:
        """Helper to try Gemini keys, and fallback to Groq on Exhaustion"""
        if self.use_groq_exclusively:
            return await self._call_groq_text(prompt)
            
        while True:
            try:
                response = self.pro_model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                error_msg = str(e).lower()
                # Check for quota or 429
                if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
                    if self.rotate_key():
                        continue # try the prompt again with new key
                
                # If we're here, it's either not a quota error OR all keys are exhausted
                print(f"Gemini wrapper completely failed: {e}")
                self.use_groq_exclusively = True
                
                try:
                    return await self._call_groq_text(prompt)
                except Exception as groq_err:
                    print(f"Groq Fallback also failed: {groq_err}")
                    raise groq_err

    async def identify_plant(self, image_data: bytes) -> dict:
        """Identify plant species and details using Gemini Vision."""
        try:
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
            
            result_text = None
            while True:
                try:
                    response = self.vision_model.generate_content([prompt, img])
                    result_text = response.text.strip()
                    break
                except Exception as e:
                    error_msg = str(e).lower()
                    if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
                        if self.rotate_key():
                            continue
                    raise e
            
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
                
            return json.loads(result_text.strip())
            
        except Exception as e:
            print(f"Gemini Vision Error: {e}")
            self.reset_key_cycle()
            return None

    async def generate_crop_recommendation(self, farm_data: dict, local_trends: dict, user_preferences: dict) -> dict:
        """Generate AI crop recommendations using Gemini with Farm data and Neo4j context."""
        try:
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
            CRITICAL INSTRUCTION: Your cost breakdown MUST sum up perfectly to their Investment Budget. Your expected profit MUST be mathematically realistic based on Indian agricultural standards for that investment size (typically 30% to 150% ROI). DO NOT inflate profits ridiculously high.

            IMPORTANT: Return ONLY a raw JSON object string with no markdown formatting. The JSON must EXACTLY match this structure:
            {{
                "crop": "Name of the crop (e.g., Wheat)",
                "variety": "Specific high-yield variety (e.g., HD-2967)",
                "expected_profit_min": <FLOAT: realistic low-end net profit strictly based on budget>,
                "expected_profit_max": <FLOAT: realistic high-end net profit strictly based on budget>,
                "investment_breakdown": {{
                    "Seeds": <INT: proportional cost>,
                    "Fertilizer": <INT: proportional cost>,
                    "Labor": <INT: proportional cost>,
                    "Irrigation/Misc": <INT: proportional cost>
                }},
                "risk_factors": ["List 2-3 risks like specific pests or weather"],
                "timeline": "e.g. 120-130 days",
                "advice": "A short, encouraging paragraph on why this is the best decision based on their local graph trends and soil."
            }}
            """
            
            result_text = await self._generate_text_with_retry(prompt)
            
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
                
            return json.loads(result_text.strip())
            
        except Exception as e:
            traceback.print_exc()
            print(f"Gemini Recommendation Error: {e}")
            return None

    async def generate_text_response(self, prompt: str) -> str:
        """Generate a raw text response for Voice/IVR using exclusively Groq Llama 3."""
        try:
            return await self._call_groq_text(prompt)
        except Exception as e:
            import traceback
            import tempfile
            with open("error_log.txt", "a") as f:
                f.write("\\n\\n--- IVR ERROR ---\\n")
                f.write(traceback.format_exc())
            try:
                print(f"Gemini/Groq Voice Response Error: {e}")
            except Exception:
                pass
            return "माफ़ करें, अभी कोई तकनीकी समस्या है। कृपया बाद में प्रयास करें।"

# Create singleton instance
gemini_service = GeminiService()

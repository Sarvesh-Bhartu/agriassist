from PIL import Image
import io
import json
from typing import Dict
from app.services.gemini_service import gemini_service


class VisionService:
    """Plant identification using Gemini Vision"""
    
    def __init__(self):
        self.model = gemini_service.get_vision_model()
    
    async def identify_plant(self, image_bytes: bytes) -> Dict:
        """Identify plant from image using Gemini Vision"""
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Create prompt for plant identification
            prompt = """
            Analyze this plant image and provide detailed information.
            
            Respond in JSON format with these exact fields:
            {
                "species": "scientific name of the plant",
                "common_name": "common English name",
                "local_name": "Hindi/regional name if applicable",
                "is_invasive": true or false (whether invasive to Indian agriculture),
                "threat_level": "High" or "Medium" or "Low",
                "confidence": 0.85 (your confidence level as decimal 0.0-1.0),
                "removal_method": "detailed removal steps if invasive, otherwise general care tips"
            }
            
            If you cannot identify the plant clearly, set confidence below 0.5 and provide your best guess.
            """
            
            # Generate response
            response = self.model.generate_content([prompt, image])
            
            # Parse JSON from response
            result_text = response.text.strip()
            
            # Handle markdown code blocks
            if result_text.startswith("```json"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            elif result_text.startswith("```"):
                result_text = result_text.replace("```", "").strip()
            
            result = json.loads(result_text)
            
            # Validate and set defaults
            result.setdefault("species", "Unknown")
            result.setdefault("common_name", "Unknown Plant")
            result.setdefault("local_name", "")
            result.setdefault("is_invasive", False)
            result.setdefault("threat_level", "Low")
            result.setdefault("confidence", 0.5)
            result.setdefault("removal_method", "")
            
            return result
            
        except json.JSONDecodeError as e:
            # Fallback if JSON parsing fails
            return {
                "species": "Unknown",
                "common_name": "Plant identification failed",
                "local_name": "",
                "is_invasive": False,
                "threat_level": "Low",
                "confidence": 0.0,
                "removal_method": "Unable to analyze image properly. Please try with a clearer photo."
            }
        except Exception as e:
            raise Exception(f"Plant identification failed: {str(e)}")


# Create singleton instance
vision_service = VisionService()

import google.generativeai as genai
from app.core.config import settings


class GeminiService:
    """Base Gemini API service"""
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.vision_model = genai.GenerativeModel('gemini-1.5-flash')
        self.pro_model = genai.GenerativeModel('gemini-1.5-pro')
    
    def get_vision_model(self):
        """Get Gemini Vision model"""
        return self.vision_model
    
    def get_pro_model(self):
        """Get Gemini Pro model"""
        return self.pro_model


# Create singleton instance
gemini_service = GeminiService()

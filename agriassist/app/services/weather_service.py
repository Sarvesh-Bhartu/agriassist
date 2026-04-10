import httpx
import logging

logger = logging.getLogger(__name__)

class WeatherService:
    """Service to fetch real-time weather data from Open-Meteo (Free, No Key Required)"""
    
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    
    async def get_weather(self, lat: float, lon: float) -> dict:
        """Fetch current weather for given coordinates."""
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "timezone": "auto"
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                if "current_weather" in data:
                    cw = data["current_weather"]
                    return {
                        "temp": cw.get("temperature"),
                        "windspeed": cw.get("windspeed"),
                        "condition_code": cw.get("weathercode"),
                        "is_day": cw.get("is_day")
                    }
                return None
        except Exception as e:
            logger.error(f"Error fetching weather from Open-Meteo: {e}")
            return None

    def get_condition_string(self, code: int) -> str:
        """Map WMO code to a simple descriptive string (in English, to be translated by LLM)."""
        # Mapping from https://open-meteo.com/en/docs
        mapping = {
            0: "Clear sky",
            1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        return mapping.get(code, "Cloudy")

weather_service = WeatherService()

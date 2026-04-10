from fastapi import APIRouter, Request, Response, Depends, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import Farmer
from app.models.farm import Farm
from app.models.crop import MarketPrice
from app.services.graph_service import graph_service
from app.services.gemini_service import gemini_service
from app.services.weather_service import weather_service
from app.services.market_service import market_service
from app.core.security import get_current_user
from sqlalchemy import func
import urllib.parse
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

from twilio.twiml.voice_response import VoiceResponse, Gather

from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from app.core.config import settings

router = APIRouter(prefix="/api/voice", tags=["Voice Assistant"])

@router.get("/token")
async def get_voice_token(
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user)
):
    """Generate a Twilio Client token for making web calls"""
    if not settings.TWILIO_API_KEY or not settings.TWILIO_API_SECRET or not settings.TWILIO_TWIML_APP_SID:
        return {"error": "Missing Twilio API credentials for Voice Token."}
        
    # Create access token with credentials
    token = AccessToken(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_API_KEY,
        settings.TWILIO_API_SECRET,
        identity=f"farmer_web_{current_user.phone}"
    )

    # Create a Voice grant and add to token
    voice_grant = VoiceGrant(
        outgoing_application_sid=settings.TWILIO_TWIML_APP_SID,
        incoming_allow=False # Not receiving calls
    )
    token.add_grant(voice_grant)

    # Return token info as JSON
    return {"token": token.to_jwt()}

@router.post("/webhook")
async def handle_incoming_call(request: Request, db: Session = Depends(get_db)):
    """Handle incoming Twilio voice calls"""
    form_data = await request.form()
    caller_phone = form_data.get('From', '')
    
    # Clean phone number (e.g. +91...)
    clean_phone = caller_phone.replace(' ', '')
    
    # Identify farmer from phone number in SQLite
    if clean_phone.startswith('client:farmer_web_'):
        actual_phone = clean_phone.replace('client:farmer_web_', '')
        farmer = db.query(Farmer).filter(Farmer.phone == actual_phone).first()
    else:
        farmer = db.query(Farmer).filter(Farmer.phone == clean_phone).first()

    response = VoiceResponse()
    
    if not farmer:
        # Unknown caller - simple fallback greeting
        response.say(
            "नमस्ते! कृषि सहायता में आपका स्वागत है। आप हमारे सिस्टम में पंजीकृत नहीं हैं। कृपया ऐप डाउनलोड करके रजिस्टर करें।",
            language='hi-IN',
            voice='Polly.Aditi'
        )
        return Response(content=str(response), media_type='text/xml')
        
    # Existing user - main menu
    gather = Gather(
        num_digits=1,
        action='/api/voice/menu',
        timeout=10
    )
    
    greeting = f"नमस्ते {farmer.name.split()[0]}! कृषि सहायता में आपका स्वागत है। "
    menu = (
        "फसल सलाह के लिए 1 दबाएं, "
        "बाजार भाव के लिए 2 दबाएं, "
        "मौसम अपडेट के लिए 3 दबाएं, "
        "या AI सहायक से बात करने के लिए 4 दबाएं।"
    )
    
    gather.say(greeting + menu, language='hi-IN', voice='Polly.Aditi')
    response.append(gather)
    
    return Response(content=str(response), media_type='text/xml')

@router.post("/menu")
async def handle_menu_selection(request: Request, db: Session = Depends(get_db)):
    """Handle user menu selection"""
    form_data = await request.form()
    digit_pressed = form_data.get('Digits')
    caller_phone = form_data.get('From', '')
    
    response = VoiceResponse()
    
    logger.info(f"☎️ Voice Menu Choice: {digit_pressed} from {caller_phone}")

    if digit_pressed == '4':
        # AI assistant
        gather = Gather(
            input='speech',
            action='/api/voice/ai-response',
            language='hi-IN', # Hindi ASR is not supported by Default Basic engine
            timeout=5,
            speechTimeout='auto'
        )
        gather.say("अपना सवाल बोलें।", language='hi-IN', voice='Polly.Aditi')
        response.append(gather)
        
    elif digit_pressed == '2':
        # REAL Market Prices from Database. Auto-refresh if stale.
        logger.info("Fetching market prices...")
        
        # 1. Fetch farmer context to get state
        clean_phone = caller_phone.replace(' ', '')
        if clean_phone.startswith('client:farmer_web_'):
            actual_phone = clean_phone.replace('client:farmer_web_', '')
            farmer = db.query(Farmer).filter(Farmer.phone == actual_phone).first()
        else:
            farmer = db.query(Farmer).filter(Farmer.phone == clean_phone).first()
        
        state = farmer.state if farmer and farmer.state else "Maharashtra"
        
        # 2. Trigger background update for fresh data
        await market_service.update_market_db(db, state)
        
        # 3. Read back latest 5 prices
        prices = db.query(MarketPrice).order_by(MarketPrice.price_date.desc()).limit(5).all()
        
        if not prices:
            price_text = "माफ़ कीजिये, अभी हमारे पास बाज़ार भाव की ताज़ा जानकारी उपलब्ध नहीं है।"
        else:
            price_text = "आज के बाज़ार भाव इस प्रकार हैं: "
            for p in prices:
                # Assuming Indian quintal (100kg) for better context
                quintal_price = float(p.price_per_kg) * 100
                trend_emoji = "📈" if p.trend == 'rising' else ("📉" if p.trend == 'falling' else "➡️")
                trend_text = "बढ़ रहा है" if p.trend == 'rising' else ("गिर रहा है" if p.trend == 'falling' else "स्थिर है")
                price_text += f"{p.crop_name} {int(quintal_price)} रुपये प्रति क्विंटल, भाव {trend_text}। "
        
        logger.info(f"Responding with Market Price Text: {price_text}")
        response.say(price_text, language='hi-IN', voice='Polly.Aditi')
        response.redirect('/api/voice/webhook')
        
    elif digit_pressed == '3':
        # AI-Powered REAL weather updates (Integrated Open-Meteo)
        logger.info(f"Fetching weather for {caller_phone}...")
        clean_phone = caller_phone.replace(' ', '')
        if clean_phone.startswith('client:farmer_web_'):
            actual_phone = clean_phone.replace('client:farmer_web_', '')
            farmer = db.query(Farmer).filter(Farmer.phone == actual_phone).first()
        else:
            farmer = db.query(Farmer).filter(Farmer.phone == clean_phone).first()

        location_name = f"{farmer.district}, {farmer.state}" if farmer and farmer.district else "उत्तर भारत"
        
        # Default fallback context
        weather_data_str = "No real-time data available, provide a general seasonal update."
        
        if farmer and farmer.latitude and farmer.longitude:
            logger.info(f"Using GPS coordinates for weather: {farmer.latitude}, {farmer.longitude}")
            data = await weather_service.get_weather(float(farmer.latitude), float(farmer.longitude))
            if data:
                cond_str = weather_service.get_condition_string(data["condition_code"])
                weather_data_str = f"Temperature: {data['temp']}C, Conditions: {cond_str}, Location: {location_name}"
        
        weather_context = f"""
        REAL-TIME WEATHER DATA: {weather_data_str}
        
        Generate a concise agricultural weather report for TODAY in Hindi.
        Include temperature and sky conditions.
        Keep it to exactly 2 short sentences.
        Strictly Hindi script. No English. No markdown.
        """
        
        try:
            weather_report = await gemini_service.generate_text_response(weather_context)
            logger.info(f"Gemini Weather Response: {weather_report}")
            response.say(weather_report, language='hi-IN', voice='Polly.Aditi')
        except Exception as e:
            logger.error(f"Gemini Weather Error: {e}")
            response.say("मौसम की जानकारी प्राप्त करने में समस्या आ रही है।", language='hi-IN', voice='Polly.Aditi')
            
        response.redirect('/api/voice/webhook')
        
    elif digit_pressed == '1':
        # AI Crop Guidance using SQLite + Neo4j Context
        logger.info(f"Generating crop guidance for {caller_phone}...")
        clean_phone = caller_phone.replace(' ', '')
        if clean_phone.startswith('client:farmer_web_'):
            actual_phone = clean_phone.replace('client:farmer_web_', '')
            farmer = db.query(Farmer).filter(Farmer.phone == actual_phone).first()
        else:
            farmer = db.query(Farmer).filter(Farmer.phone == clean_phone).first()
            
        farm = db.query(Farm).filter(Farm.farmer_id == farmer.id).first() if farmer else None
        
        # Optional: Fetch neighbor trends from Neo4j
        neighbor_crops = []
        try:
            trends = graph_service.get_local_trends(farmer.id) if farmer else {}
            neighbor_crops = trends.get("popular_crops", [])
        except:
            pass
            
        context = f"""
        FARMER CONTEXT:
        - Location: {farmer.district if farmer else 'India'}, {farmer.state if farmer else ''}
        - Soil Type: {farm.soil_type if farm else 'Unknown'}
        - Neighboring Trends: {', '.join(neighbor_crops) if neighbor_crops else 'None'}
        - Current Date: {datetime.now().strftime('%B %Y')}
        
        Provide high-level seasonal crop guidance in exactly 2 short Hindi sentences.
        Recommend 1 or 2 crops to plant based on their soil and neighbors.
        Strictly Hindi script. No English characters. No markdown.
        """
        
        try:
            guidance = await gemini_service.generate_text_response(context)
            response.say(guidance, language='hi-IN', voice='Polly.Aditi')
        except Exception as e:
            logger.error(f"Guidance Error: {e}")
            response.say("सलाह प्राप्त करने में समस्या आ रही है।", language='hi-IN', voice='Polly.Aditi')
            
        response.redirect('/api/voice/webhook')
    else:
        response.say("गलत विकल्प।", language='hi-IN', voice='Polly.Aditi')
        response.redirect('/api/voice/webhook')

    return Response(content=str(response), media_type='text/xml')


@router.post("/ai-response")
async def generate_ai_response(request: Request, db: Session = Depends(get_db)):
    """Process farmer question via speech-to-text and generate LLM audio response"""
    form_data = await request.form()
    # Twilio's Gather with input="speech" sends SpeechResult
    transcription = form_data.get('SpeechResult', '')
    caller_phone = form_data.get('From', '')
    
    response = VoiceResponse()
    
    if not transcription:
        response.say("मुझे समझ नहीं आया।", language='hi-IN', voice='Polly.Aditi')
        response.redirect('/api/voice/menu?Digits=4')
        return Response(content=str(response), media_type='text/xml')

    # Get farmer context
    if caller_phone.startswith('client:farmer_web_'):
        actual_phone = caller_phone.replace('client:farmer_web_', '')
        farmer = db.query(Farmer).filter(Farmer.phone == actual_phone).first()
    else:
        farmer = db.query(Farmer).filter(Farmer.phone == caller_phone).first()
        
    if not farmer:
        response.say("खाता नहीं मिला।", language='hi-IN', voice='Polly.Aditi')
        return Response(content=str(response), media_type='text/xml')
        
    farm = db.query(Farm).filter(Farm.farmer_id == farmer.id).first()
    
    # Build Context
    context = f"""
    Farmer Profile:
    - Name: {farmer.name}
    - Farm Size: {float(farm.area_hectares) if farm and farm.area_hectares else 'Unknown'} hectares
    - Soil Type: {farm.soil_type if farm else 'Unknown'}
    
    The farmer asked this question via a Hindi voice phone call: "{transcription}"
    
    Based on their farm profile, provide a concise, helpful answer.
    IMPORTANT RULES:
    1. Respond entirely in spoken Hindi script.
    2. Write it exactly as it should be spoken aloud by a Text-to-Speech engine.
    3. Keep it VERY concise (maximum 2 or 3 short sentences, under 40 words total).
    4. Do not use markdown like asterisks (*). Do not use English words unless necessary (like 'hectare').
    """
    
    # Get answer from Gemini
    ai_answer = await gemini_service.generate_text_response(context)
    
    response.say(ai_answer, language='hi-IN', voice='Polly.Aditi')
    response.say("मुख्य मेनू के लिए कोई भी नंबर दबाएं।", language='hi-IN', voice='Polly.Aditi')
    
    gather = Gather(action='/api/voice/webhook', num_digits=1, timeout=5)
    response.append(gather)
    
    return Response(content=str(response), media_type='text/xml')

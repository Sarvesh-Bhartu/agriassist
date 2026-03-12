from app.core.database import SessionLocal
from app.models.crop import MarketPrice
from datetime import date, timedelta
import uuid

def seed_market_prices():
    db = SessionLocal()
    # Check if we have any prices
    count = db.query(MarketPrice).count()
    if count > 0:
        print(f"Found {count} existing market prices. Updating dates to today...")
        # Update existing records to today so the -7 days filter catches them
        prices = db.query(MarketPrice).all()
        for p in prices:
            p.price_date = date.today()
        db.commit()
    else:
        print("No market prices found. Seeding dummy data...")
        prices = [
            MarketPrice(
                id=str(uuid.uuid4()),
                market_name="Azadpur Mandi",
                market_location="Delhi",
                crop_name="Wheat (Gehun)",
                price_per_kg=24.50,
                price_date=date.today(),
                trend="rising"
            ),
            MarketPrice(
                id=str(uuid.uuid4()),
                market_name="Indore Mandi",
                market_location="Indore",
                crop_name="Soybean",
                price_per_kg=48.00,
                price_date=date.today(),
                trend="stable"
            ),
            MarketPrice(
                id=str(uuid.uuid4()),
                market_name="Vashi Mandi",
                market_location="Mumbai",
                crop_name="Rice (Chawal)",
                price_per_kg=32.00,
                price_date=date.today(),
                trend="falling"
            )
        ]
        db.add_all(prices)
        db.commit()
    db.close()
    print("Market price seeding complete!")

if __name__ == "__main__":
    seed_market_prices()

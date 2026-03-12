from sqlalchemy.orm import Session
from app.models.gamification import GamificationEvent
from app.models.user import Farmer
from typing import Dict, List


class GamificationService:
    """Points and badges management"""
    
    # Badge definitions
    BADGES = {
        'early_adopter': {
            'name': 'Early Adopter',
            'description': 'Registered in first month',
            'points_required': 0,
            'icon': '🌟'
        },
        'plant_guardian': {
            'name': 'Plant Guardian',
            'description': 'Detected 10 invasive plants',
            'points_required': 500,
            'icon': '🌿'
        },
        'carbon_champion': {
            'name': 'Carbon Champion',
            'description': 'Mapped farm and calculated carbon credits',
            'points_required': 100,
            'icon': '🍃'
        },
        'top_farmer': {
            'name': 'Top Farmer',
            'description': 'Reached #1 on leaderboard',
            'points_required': 1000,
            'icon': '🏆'
        },
        'knowledge_seeker': {
            'name': 'Knowledge Seeker',
            'description': 'Used crop recommendations 5 times',
            'points_required': 250,
            'icon': '📚'
        }
    }
    
    # Level Progression Tiers
    LEVEL_TIERS = [
        {'name': 'Novice Planter', 'icon': '🌱', 'min_points': 0, 'max_points': 999},
        {'name': 'Growing Cultivator', 'icon': '🌿', 'min_points': 1000, 'max_points': 2499},
        {'name': 'Skilled Agronomist', 'icon': '🪴', 'min_points': 2500, 'max_points': 4999},
        {'name': 'Master Harvester', 'icon': '🌳', 'min_points': 5000, 'max_points': float('inf')}
    ]
    
    def get_user_level(self, current_points: int) -> Dict:
        """Calculate the user's current gamification level and progress to the next"""
        current_tier = None
        next_tier = None
        
        for i, tier in enumerate(self.LEVEL_TIERS):
            if tier['min_points'] <= current_points <= tier['max_points']:
                current_tier = tier
                if i + 1 < len(self.LEVEL_TIERS):
                    next_tier = self.LEVEL_TIERS[i + 1]
                break
                
        if not current_tier:
            return {}
            
        progress_percentage = 100
        points_needed = 0
        
        if next_tier:
            tier_range = next_tier['min_points'] - current_tier['min_points']
            points_into_tier = current_points - current_tier['min_points']
            progress_percentage = min(100, max(0, int((points_into_tier / tier_range) * 100)))
            points_needed = next_tier['min_points'] - current_points
            
        return {
            'current_level': current_tier['name'],
            'current_icon': current_tier['icon'],
            'next_level': next_tier['name'] if next_tier else None,
            'next_icon': next_tier['icon'] if next_tier else None,
            'progress_percentage': progress_percentage,
            'points_to_next': points_needed,
            'current_points': current_points,
            'next_tier_points': next_tier['min_points'] if next_tier else current_tier['min_points']
        }
    
    async def add_points(
        self,
        db: Session,
        farmer_id: str,
        points: int,
        reason: str,
        event_type: str
    ) -> Dict:
        """Award points and check for new badges"""
        
        # Get farmer
        farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
        
        if not farmer:
            raise ValueError("Farmer not found")
        
        # Add points
        farmer.total_points += points
        
        # Record event
        event = GamificationEvent(
            farmer_id=farmer_id,
            event_type=event_type,
            points_awarded=points,
            reason=reason
        )
        db.add(event)
        
        # Check for new badges
        new_badges = []
        current_badges = farmer.badges or []
        
        for badge_id, badge_info in self.BADGES.items():
            if badge_id not in current_badges:
                if farmer.total_points >= badge_info['points_required']:
                    current_badges.append(badge_id)
                    new_badges.append(badge_info['name'])
                    event.badge_awarded = badge_id
        
        # Update farmer badges
        farmer.badges = current_badges
        
        db.commit()
        db.refresh(farmer)
        
        return {
            'points_added': points,
            'total_points': farmer.total_points,
            'new_badges': new_badges,
            'all_badges': [self.BADGES[b]['name'] for b in current_badges if b in self.BADGES]
        }
    
    async def get_leaderboard(self, db: Session, limit: int = 50) -> List[Dict]:
        """Get top farmers by points"""
        
        farmers = db.query(Farmer).filter(
            Farmer.is_active == True
        ).order_by(
            Farmer.total_points.desc()
        ).limit(limit).all()
        
        leaderboard = []
        for rank, farmer in enumerate(farmers, 1):
            badges_info = [
                self.BADGES[b] for b in (farmer.badges or []) 
                if b in self.BADGES
            ]
            
            leaderboard.append({
                'rank': rank,
                'name': farmer.name,
                'points': farmer.total_points,
                'badges': [b['name'] for b in badges_info],
                'badges_icons': [b['icon'] for b in badges_info],
                'district': farmer.district
            })
        
        return leaderboard
    
    def get_badge_info(self, badge_id: str) -> Dict:
        """Get information about a specific badge"""
        return self.BADGES.get(badge_id, {})
    
    def get_all_badges(self) -> Dict:
        """Get all available badges"""
        return self.BADGES


# Create singleton instance
gamification_service = GamificationService()

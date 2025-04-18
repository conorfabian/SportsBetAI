from app import create_app, db
from app.models.base import Player, Game, PlayerStats, PropLine, Prediction
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def init_db():
    """Initialize database with required tables"""
    app = create_app()
    with app.app_context():
        logger.info("Creating database tables...")
        db.create_all()
        logger.info("Database tables created successfully!")

def seed_sample_data():
    """Seed database with sample data for development"""
    app = create_app()
    with app.app_context():
        # Check if we already have data
        if Player.query.count() > 0:
            logger.info("Database already has data. Skipping seed.")
            return
        
        logger.info("Seeding database with sample data...")
        
        # Add sample players
        jokic = Player(nba_api_id=203999, full_name="Nikola Jokić")
        lebron = Player(nba_api_id=2544, full_name="LeBron James")
        curry = Player(nba_api_id=201939, full_name="Stephen Curry")
        
        db.session.add_all([jokic, lebron, curry])
        db.session.commit()
        
        logger.info("Sample data seeded successfully!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    seed_sample_data() 
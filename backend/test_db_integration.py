#!/usr/bin/env python
"""
Test database integration with a temporary SQLite database.
This tests the historical data fetcher with actual database operations
without needing to set up PostgreSQL.
"""
import os
import logging
import pandas as pd
import tempfile
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.models.base import Player, Game, PlayerStats
from app.utils.historical_data_fetcher import save_to_database, fetch_player_game_logs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_app():
    """Create a test Flask app with a SQLite database"""
    # Create a temporary file for SQLite
    db_fd, db_path = tempfile.mkstemp()
    
    # Configure the app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    
    # Initialize SQLAlchemy
    db = SQLAlchemy(app)
    
    return app, db, db_fd, db_path

def create_test_player(db):
    """Create a test player in the database"""
    player = Player(
        nba_api_id=2544,  # LeBron James
        full_name="LeBron James"
    )
    db.session.add(player)
    db.session.commit()
    return player

def create_test_game_logs():
    """Create test game logs DataFrame"""
    return pd.DataFrame({
        'GAME_DATE': ['2023-10-24', '2023-10-26'],
        'MATCHUP': ['LAL vs. PHX', 'LAL @ DEN'],
        'WL': ['W', 'L'],
        'MIN': ['32', '35'],
        'PTS': [30, 25],
        'REB': [10, 8],
        'AST': [8, 9],
        'STL': [1, 0],
        'BLK': [0, 1],
        'TOV': [3, 2],
        'FGM': [10, 8],
        'FGA': [16, 15],
        'FG_PCT': [0.625, 0.533],
        'FG3M': [2, 1],
        'FG3A': [5, 4],
        'FG3_PCT': [0.400, 0.250],
        'FTM': [8, 8],
        'FTA': [10, 9],
        'FT_PCT': [0.800, 0.889],
        'PLUS_MINUS': [10, -5]
    })

def test_save_to_database():
    """Test the save_to_database function"""
    app, db, db_fd, db_path = create_test_app()
    
    try:
        with app.app_context():
            # Create tables
            from app.models.base import db as app_db
            app_db.app = app
            app_db.init_app(app)
            app_db.create_all()
            
            # Create test player
            player = create_test_player(db)
            
            # Create test game logs
            game_logs = create_test_game_logs()
            
            # Call save_to_database
            saved_count = save_to_database(game_logs, player)
            
            # Verify results
            assert saved_count == 2, f"Expected to save 2 games, but saved {saved_count}"
            
            # Query the database to verify
            games = Game.query.all()
            stats = PlayerStats.query.all()
            
            assert len(games) == 2, f"Expected 2 games, but found {len(games)}"
            assert len(stats) == 2, f"Expected 2 player stats records, but found {len(stats)}"
            
            # Check stats values
            for stat in stats:
                assert stat.player_id == player.id
                assert stat.points in [30, 25]
                
            logger.info("Test passed: save_to_database works correctly")
            return True
    
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False
    
    finally:
        # Clean up
        os.close(db_fd)
        os.unlink(db_path)

def main():
    """Run all tests"""
    logger.info("Starting database integration tests")
    
    success = test_save_to_database()
    
    if success:
        logger.info("All tests passed!")
    else:
        logger.error("Some tests failed.")

if __name__ == '__main__':
    main() 
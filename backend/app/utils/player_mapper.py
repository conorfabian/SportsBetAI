import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from app import db
from app.models.prop_line import PropLine, PropLineRaw

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def map_players_to_ids():
    """
    Maps player names from raw prop lines to internal player IDs.
    
    This function looks for unprocessed raw prop lines, attempts to match them
    to player IDs in the players table, and creates entries in the prop_lines table.
    """
    try:
        logger.info("Starting player name to ID mapping process")
        
        # Get unprocessed raw prop lines
        raw_props = PropLineRaw.query.filter_by(processed=False).all()
        logger.info(f"Found {len(raw_props)} unprocessed raw prop lines")
        
        if not raw_props:
            logger.info("No unprocessed raw prop lines found. Exiting.")
            return
        
        # Get players from the database to map names
        # We'll use a simple query to get all players, but in a larger system
        # you might want to do this in batches or use a more sophisticated matching algorithm
        players_df = pd.read_sql_query(
            "SELECT id, full_name FROM players", 
            db.engine
        )
        
        if players_df.empty:
            logger.warning("No players found in database. Cannot map names to IDs.")
            return
        
        # Convert player names to lowercase for case-insensitive matching
        players_df['full_name_lower'] = players_df['full_name'].str.lower()
        
        # Create a name-to-id mapping
        name_to_id_map = dict(zip(players_df['full_name_lower'], players_df['id']))
        
        # Process each raw prop line
        for raw_prop in raw_props:
            player_name_lower = raw_prop.player_name.lower()
            
            # Look for an exact match first
            player_id = name_to_id_map.get(player_name_lower)
            
            # If no exact match, try a fuzzy match (simplified version)
            if player_id is None:
                # Find partial matches (simple implementation)
                # A more sophisticated approach could use fuzzywuzzy or similar libraries
                for db_name, db_id in name_to_id_map.items():
                    # Check if the player name contains the DB name or vice versa
                    if db_name in player_name_lower or player_name_lower in db_name:
                        player_id = db_id
                        logger.info(f"Fuzzy matched '{raw_prop.player_name}' to player ID {player_id}")
                        break
            
            if player_id:
                # Create a new PropLine entry
                new_prop = PropLine(
                    player_id=player_id,
                    game_date=raw_prop.game_date,
                    line=raw_prop.prop_line,
                    fetched_at=raw_prop.timestamp,
                    home_team=raw_prop.home_team,
                    away_team=raw_prop.away_team,
                    bookmaker=raw_prop.bookmaker
                )
                db.session.add(new_prop)
                
                # Mark the raw prop as processed
                raw_prop.processed = True
            else:
                logger.warning(f"Could not map player name '{raw_prop.player_name}' to an ID")
        
        # Commit all changes
        db.session.commit()
        logger.info("Player mapping process completed successfully")
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during player mapping: {str(e)}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during player mapping: {str(e)}")

def main():
    """
    Main function to run the player mapper independently.
    """
    try:
        map_players_to_ids()
    except Exception as e:
        logger.error(f"Failed to run player mapper: {str(e)}")

if __name__ == "__main__":
    main() 
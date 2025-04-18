import os
import logging
import requests
from datetime import datetime, date
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
API_KEY = os.environ.get('ODDS_API_KEY', 'd5fc1dff6519aedb48fee57ec75af13d')  # Default value is from the example, should be replaced with env var
SPORT = 'basketball_nba'
MARKET = 'player_points'
REGIONS = 'us'
ODDS_FORMAT = 'american'
BASE_URL = 'https://api.the-odds-api.com/v4/sports'

def fetch_live_prop_lines(db_connection_string=None):
    """
    Fetches live NBA player prop lines for points from The Odds API
    and stores them in the database if a connection string is provided.
    
    Args:
        db_connection_string (str, optional): Database connection string.
            If None, data is returned but not stored.
    
    Returns:
        list: Processed prop lines data
    """
    try:
        logger.info('Fetching NBA player points props...')
        
        url = f"{BASE_URL}/{SPORT}/odds"
        response = requests.get(url, params={
            'apiKey': API_KEY,
            'regions': REGIONS,
            'markets': MARKET,
            'oddsFormat': ODDS_FORMAT
        })
        
        response.raise_for_status()
        games = response.data if hasattr(response, 'data') else response.json()
        
        logger.info(f"Found {len(games)} NBA games with player points props")
        
        # Process the data into a standardized format
        processed_data = []
        current_timestamp = datetime.now()
        today = date.today()
        
        for game in games:
            game_date = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00')).date()
            
            for bookmaker in game['bookmakers']:
                if bookmaker['title'].lower() != 'fanduel':
                    continue
                    
                player_points_market = next((market for market in bookmaker['markets'] 
                                          if market['key'] == MARKET), None)
                
                if player_points_market:
                    for outcome in player_points_market['outcomes']:
                        player_name = outcome['name']
                        prop_line = outcome['point']
                        
                        processed_data.append({
                            'player_name': player_name,
                            'prop_line': prop_line,
                            'game_date': game_date,
                            'timestamp': current_timestamp,
                            'home_team': game['home_team'],
                            'away_team': game['away_team'],
                            'bookmaker': bookmaker['title']
                        })
        
        logger.info(f"Processed {len(processed_data)} player prop lines")
        
        # Store in database if connection string is provided
        if db_connection_string and processed_data:
            store_props_in_db(processed_data, db_connection_string)
        
        return processed_data
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching NBA player points props: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"API Response: {e.response.text}")
            logger.error(f"Status: {e.response.status_code}")
            
            # Handle 422 errors (often means no games or markets available)
            if e.response.status_code == 422:
                logger.warning("422 Error: This typically means no games are available or the market is not offered. If it's off-season or no games today, this is expected.")
                return []  # Return empty list instead of raising error
            
            # Implement retry logic here for HTTP 5xx errors
            if 500 <= e.response.status_code < 600:
                logger.info("Server error (5xx). Implementing retry...")
                # Here you would implement your retry logic
                # For simplicity, we're just logging it now
        
        # Only raise for non-422 errors
        if not (hasattr(e, 'response') and e.response and e.response.status_code == 422):
            raise e
        return []

def store_props_in_db(props_data, db_connection_string):
    """
    Store the fetched prop lines in the database.
    
    Args:
        props_data (list): List of dictionaries containing prop line data
        db_connection_string (str): Database connection string
    """
    try:
        engine = create_engine(db_connection_string)
        df = pd.DataFrame(props_data)
        
        # Here we would typically do player name to player_id mapping
        # This would require a lookup table that maps player names to your internal player IDs
        
        # For now, let's assume we're just storing the raw data
        df.to_sql('prop_lines_raw', engine, if_exists='append', index=False)
        
        logger.info(f"Successfully stored {len(props_data)} prop lines in the database")
    
    except SQLAlchemyError as e:
        logger.error(f"Database error while storing prop lines: {str(e)}")
        raise e

def main():
    """
    Main function to run the script independently for testing.
    """
    # Get connection string from environment variable or use None for testing
    db_connection_string = os.environ.get('DATABASE_URL')
    
    try:
        props = fetch_live_prop_lines(db_connection_string)
        
        # If just testing without DB, print some results
        if not db_connection_string:
            print(f"Fetched {len(props)} prop lines.")
            for prop in props[:5]:  # Print first 5 as example
                print(f"{prop['player_name']}: Over/Under {prop['prop_line']} points")
    
    except Exception as e:
        logger.error(f"Failed to fetch prop lines: {str(e)}")

if __name__ == "__main__":
    main() 
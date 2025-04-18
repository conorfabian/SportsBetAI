"""
Test script for directly testing the Odds API integration.
This can be run standalone to verify the API is working.
"""
import os
import requests
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
API_KEY = os.environ.get('ODDS_API_KEY', 'd5fc1dff6519aedb48fee57ec75af13d')  # Replace with your API key
SPORT = 'basketball_nba'
MARKET = 'player_points'
REGIONS = 'us'
ODDS_FORMAT = 'american'
BASE_URL = 'https://api.the-odds-api.com/v4/sports'

def test_odds_api():
    """Direct test of the Odds API without any database interaction."""
    logger.info('Testing Odds API direct access...')
    
    try:
        url = f"{BASE_URL}/{SPORT}/odds"
        response = requests.get(url, params={
            'apiKey': API_KEY,
            'regions': REGIONS,
            'markets': MARKET,
            'oddsFormat': ODDS_FORMAT
        })
        
        if response.status_code == 200:
            games = response.json()
            logger.info(f"API call successful! Found {len(games)} games with player points props")
            
            # Process the response
            process_response(games)
            
            # Return clean exit
            return True
        elif response.status_code == 422:
            logger.warning("422 Error: No games available or the market is not offered.")
            logger.warning("If it's off-season or no games today, this is expected.")
            return False
        else:
            logger.error(f"API Error: Status code {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Exception while testing API: {str(e)}")
        return False

def process_response(games):
    """Process the API response and print results."""
    if not games:
        logger.info("No games data received")
        return
    
    total_props = 0
    
    for game in games:
        print(f"\nGame: {game['away_team']} @ {game['home_team']}")
        print(f"Start Time: {game['commence_time']}")
        
        props_in_game = False
        
        for bookmaker in game['bookmakers']:
            if bookmaker['title'].lower() != 'fanduel':
                continue
            
            player_points_market = next((market for market in bookmaker['markets'] 
                                      if market['key'] == MARKET), None)
            
            if player_points_market:
                props_in_game = True
                print(f"\n  {bookmaker['title']} point props:")
                
                for outcome in sorted(player_points_market['outcomes'], 
                                    key=lambda x: float(x['point']), reverse=True):
                    player_name = outcome['name']
                    prop_line = outcome['point']
                    price = outcome['price']
                    price_display = f"+{price}" if price > 0 else price
                    
                    print(f"    {player_name}: Over/Under {prop_line} points ({price_display})")
                    total_props += 1
        
        if not props_in_game:
            print("  No FanDuel player points props available for this game")
    
    print(f"\nTotal player point props found: {total_props}")

if __name__ == "__main__":
    print("=" * 70)
    print("NBA PLAYER POINTS PROP LINES TEST")
    print("=" * 70)
    
    success = test_odds_api()
    
    if not success:
        # If the real API fails, show some sample data as fallback
        print("\nShowing sample data instead...")
        
        # Load sample data
        from mock_test import sample_response_data
        sample_games = json.loads(sample_response_data())
        
        # Process sample data
        process_response(sample_games)
        
        print("\nNote: This is SAMPLE DATA, not actual current odds!")
    
    print("\nTest complete.") 
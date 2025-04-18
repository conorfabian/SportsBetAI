import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_sample_data():
    """Process sample Odds API data directly to test the core logic."""
    logger.info("Processing sample data...")
    
    # Load sample data
    sample_data = json.loads(sample_response_data())
    
    # Process the data into a standardized format (similar to fetch_live_prop_lines)
    processed_data = []
    current_timestamp = datetime.now()
    
    for game in sample_data:
        game_date = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00')).date()
        
        for bookmaker in game['bookmakers']:
            if bookmaker['title'].lower() != 'fanduel':
                continue
                
            player_points_market = next((market for market in bookmaker['markets'] 
                                      if market['key'] == 'player_points'), None)
            
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
    
    # Display processed data
    for prop in processed_data:
        print(f"{prop['player_name']}: Over/Under {prop['prop_line']} points")
    
    return processed_data

def sample_response_data():
    """Return a sample JSON response from the Odds API."""
    return """
    [
      {
        "id": "1234",
        "sport_key": "basketball_nba",
        "commence_time": "2023-12-25T20:00:00Z",
        "home_team": "Los Angeles Lakers",
        "away_team": "Golden State Warriors",
        "bookmakers": [
          {
            "key": "fanduel",
            "title": "FanDuel",
            "last_update": "2023-12-25T19:30:00Z",
            "markets": [
              {
                "key": "player_points",
                "last_update": "2023-12-25T19:30:00Z",
                "outcomes": [
                  {
                    "name": "LeBron James",
                    "description": "Over",
                    "price": -110,
                    "point": 25.5
                  },
                  {
                    "name": "Stephen Curry",
                    "description": "Over",
                    "price": -115,
                    "point": 28.5
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "id": "5678",
        "sport_key": "basketball_nba",
        "commence_time": "2023-12-25T22:30:00Z",
        "home_team": "Boston Celtics",
        "away_team": "Milwaukee Bucks",
        "bookmakers": [
          {
            "key": "fanduel",
            "title": "FanDuel",
            "last_update": "2023-12-25T19:30:00Z",
            "markets": [
              {
                "key": "player_points",
                "last_update": "2023-12-25T19:30:00Z",
                "outcomes": [
                  {
                    "name": "Jayson Tatum",
                    "description": "Over",
                    "price": -110,
                    "point": 26.5
                  },
                  {
                    "name": "Giannis Antetokounmpo",
                    "description": "Over",
                    "price": -105,
                    "point": 30.5
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
    """

if __name__ == "__main__":
    process_sample_data() 
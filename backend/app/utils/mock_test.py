"""
Mock test for the odds fetcher functionality.
This script simulates the API response and directly tests the core logic.
"""
import sys
import json
import logging
from datetime import datetime
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_fetch_and_process():
    """Directly test the odds processing logic with sample data."""
    logger.info("Testing fetch and process logic with sample data")
    
    # Sample API response
    sample_data = json.loads(sample_response_data())
    
    # Process the data (similar to fetch_live_prop_lines)
    processed_data = process_games_data(sample_data)
    
    # Verify the results
    assert len(processed_data) == 4, f"Expected 4 prop lines, got {len(processed_data)}"
    
    # Check first prop
    first_prop = processed_data[0]
    assert first_prop['player_name'] == 'LeBron James', f"Expected LeBron James, got {first_prop['player_name']}"
    assert first_prop['prop_line'] == 25.5, f"Expected 25.5, got {first_prop['prop_line']}"
    assert first_prop['bookmaker'] == 'FanDuel', f"Expected FanDuel, got {first_prop['bookmaker']}"
    
    logger.info("All assertions passed!")
    
    # Print results
    for prop in processed_data:
        print(f"{prop['player_name']}: Over/Under {prop['prop_line']} points")
    
    return processed_data

def process_games_data(games):
    """Process games data into standardized format."""
    processed_data = []
    current_timestamp = datetime.now()
    
    for game in games:
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
    return processed_data

def test_store_in_db():
    """Test the database storage function."""
    logger.info("Testing database storage functionality")
    
    # First get some processed data
    props_data = test_fetch_and_process()
    
    # Create mock DataFrame and print what would be stored
    df = pd.DataFrame(props_data)
    print("\nData that would be stored in database:")
    print(df[['player_name', 'prop_line', 'bookmaker']])
    
    logger.info("Database storage simulation complete")

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
    # Run the fetch and process test
    test_fetch_and_process()
    print("\n" + "-" * 50 + "\n")
    
    # Run the database storage test
    try:
        test_store_in_db()
    except ImportError:
        logger.error("pandas not available, skipping DB storage test")
        print("Database test skipped (pandas required)") 
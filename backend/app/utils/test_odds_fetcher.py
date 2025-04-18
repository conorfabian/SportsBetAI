import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sys
import requests
from datetime import datetime

# Add the parent directory to the path so we can import our module
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import our module to test
import odds_fetcher

class TestOddsFetcher(unittest.TestCase):
    """Test cases for the odds_fetcher module."""

    @patch('odds_fetcher.requests.get')
    def test_fetch_live_prop_lines_success(self, mock_get):
        """Test successful fetching of prop lines."""
        # Load mock data from the test_data string
        mock_data = json.loads(self.sample_response_data())
        
        # Create a mock response object
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None  # This ensures raise_for_status doesn't raise an exception
        mock_response.json.return_value = mock_data
        
        # Set up the mock to return our mock response
        mock_get.return_value = mock_response
        
        # Call the function we're testing
        result = odds_fetcher.fetch_live_prop_lines()
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 4)  # We expect 4 prop lines based on our mock data
        
        # Check the first prop line
        first_prop = result[0]
        self.assertEqual(first_prop['player_name'], 'LeBron James')
        self.assertEqual(first_prop['prop_line'], 25.5)
        self.assertEqual(first_prop['bookmaker'], 'FanDuel')

    @patch('odds_fetcher.requests.get')
    def test_fetch_live_prop_lines_api_error(self, mock_get):
        """Test handling of API errors."""
        # Create a mock error response
        mock_error = requests.exceptions.HTTPError("422 Client Error")
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "No markets available"
        mock_error.response = mock_response
        
        # Make raise_for_status raise our mock error
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = mock_error
        mock_get.return_value = mock_resp
        
        # Call the function and check the result
        result = odds_fetcher.fetch_live_prop_lines()
        
        # Should return an empty list for a 422 error
        self.assertEqual(result, [])

    @patch('odds_fetcher.create_engine')
    @patch('odds_fetcher.pd.DataFrame')
    def test_store_props_in_db(self, mock_df, mock_create_engine):
        """Test storing prop lines in the database."""
        # Test data
        props_data = [
            {
                'player_name': 'LeBron James',
                'prop_line': 25.5,
                'game_date': datetime.now().date(),
                'timestamp': datetime.now(),
                'home_team': 'Los Angeles Lakers',
                'away_team': 'Golden State Warriors',
                'bookmaker': 'FanDuel'
            }
        ]
        
        # Mock DataFrame
        mock_df_instance = MagicMock()
        mock_df.return_value = mock_df_instance
        
        # Call the function
        odds_fetcher.store_props_in_db(props_data, 'mock_connection_string')
        
        # Verify DataFrame was created
        mock_df.assert_called_once_with(props_data)
        
        # Verify to_sql was called
        mock_df_instance.to_sql.assert_called_once()

    @staticmethod
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

if __name__ == '__main__':
    unittest.main() 
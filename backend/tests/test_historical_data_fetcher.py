#!/usr/bin/env python
"""
Test the historical data fetcher functionality.
This is a simple script to verify that the NBA API data fetching works correctly.
"""
import sys
import os
import pandas as pd
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path to allow importing app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.historical_data_fetcher import (
    get_active_players,
    fetch_player_game_logs,
    save_to_database
)

class TestHistoricalDataFetcher(unittest.TestCase):
    """Test cases for the historical data fetcher"""
    
    @patch('app.utils.historical_data_fetcher.commonallplayers.CommonAllPlayers')
    def test_get_active_players(self, mock_common_all_players):
        """Test that active players are retrieved correctly"""
        # Create a mock response
        mock_players_df = pd.DataFrame({
            'PERSON_ID': [1, 2, 3],
            'DISPLAY_FIRST_LAST': ['Player One', 'Player Two', 'Player Three'],
            'TO_YEAR': [2023, 2023, 2022]  # Only the first two are active
        })
        
        # Set up the mock to return our DataFrame
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [mock_players_df]
        mock_common_all_players.return_value = mock_instance
        
        # Call the function
        result = get_active_players()
        
        # Verify the result
        self.assertEqual(len(result), 2)  # Should only have the active players
        self.assertTrue('Player One' in result['DISPLAY_FIRST_LAST'].values)
        self.assertTrue('Player Two' in result['DISPLAY_FIRST_LAST'].values)
        self.assertFalse('Player Three' in result['DISPLAY_FIRST_LAST'].values)
    
    @patch('app.utils.historical_data_fetcher.playergamelog.PlayerGameLog')
    def test_fetch_player_game_logs(self, mock_player_game_log):
        """Test that game logs are fetched correctly"""
        # Create a mock game log DataFrame
        mock_game_log_df1 = pd.DataFrame({
            'GAME_DATE': ['2023-10-24', '2023-10-26'],
            'MATCHUP': ['LAL vs. PHX', 'LAL @ DEN'],
            'WL': ['W', 'L'],
            'PTS': [30, 25]
        })
        
        mock_game_log_df2 = pd.DataFrame({
            'GAME_DATE': ['2022-10-18', '2022-10-20'],
            'MATCHUP': ['LAL vs. GSW', 'LAL @ LAC'],
            'WL': ['L', 'W'],
            'PTS': [31, 20]
        })
        
        # Set up the mocks for two different season calls
        mock_instance1 = MagicMock()
        mock_instance1.get_data_frames.return_value = [mock_game_log_df1]
        
        mock_instance2 = MagicMock()
        mock_instance2.get_data_frames.return_value = [mock_game_log_df2]
        
        mock_player_game_log.side_effect = [mock_instance1, mock_instance2]
        
        # Call the function with two seasons
        result = fetch_player_game_logs(2544, 'LeBron James', ['2023-24', '2022-23'])
        
        # Verify the result
        self.assertEqual(len(result), 4)  # Should have 4 games total
        self.assertTrue('SEASON' in result.columns)  # Should have added the SEASON column
        
        # Check that both seasons are represented
        seasons = result['SEASON'].unique()
        self.assertEqual(len(seasons), 2)
        self.assertTrue('2023-24' in seasons)
        self.assertTrue('2022-23' in seasons)

if __name__ == '__main__':
    unittest.main() 
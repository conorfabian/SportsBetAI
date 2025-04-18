from nba_api.stats.endpoints import playergamelog
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def fetch_player_gamelog(player_id, season='2023-24'):
    """
    Fetch game log data for a specific player and season
    
    Args:
        player_id (int): NBA API player ID
        season (str): Season in format YYYY-YY (e.g., '2023-24')
        
    Returns:
        pandas.DataFrame: DataFrame containing player game log data
    """
    try:
        logger.info(f"Fetching game log for player ID {player_id} for season {season}")
        
        gamelog = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            season_type_all_star='Regular Season'
        )
        
        df = gamelog.get_data_frames()[0]
        logger.info(f"Successfully fetched {len(df)} games for player ID {player_id}")
        
        return df
    
    except Exception as e:
        logger.error(f"Error fetching game log for player ID {player_id}: {str(e)}")
        return pd.DataFrame() 
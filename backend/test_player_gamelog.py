#!/usr/bin/env python
"""
Standalone script to test fetching a player's game log from the NBA API.
This doesn't require setting up the database.
"""
import pandas as pd
import argparse
import logging
from nba_api.stats.endpoints import commonallplayers, playergamelog

def setup_logging(verbose=False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def find_player_by_name(player_name, logger):
    """Find a player by name"""
    logger.info(f"Searching for player: {player_name}")
    
    all_players = commonallplayers.CommonAllPlayers()
    players_df = all_players.get_data_frames()[0]
    
    # Case-insensitive search with partial matching
    matching_players = players_df[players_df['DISPLAY_FIRST_LAST'].str.lower().str.contains(player_name.lower())]
    
    if matching_players.empty:
        logger.error(f"No players found matching '{player_name}'")
        return None, None
    
    # Display all matches
    logger.info(f"Found {len(matching_players)} matching players:")
    for idx, player in matching_players.iterrows():
        logger.info(f"  {player['DISPLAY_FIRST_LAST']} (ID: {player['PERSON_ID']})")
    
    # Return the first match
    player_id = matching_players.iloc[0]['PERSON_ID']
    full_name = matching_players.iloc[0]['DISPLAY_FIRST_LAST']
    
    logger.info(f"Using player: {full_name} (ID: {player_id})")
    return player_id, full_name

def get_player_gamelog(player_id, player_name, season, logger):
    """Get a player's game log for a season"""
    logger.info(f"Fetching game log for {player_name} (ID: {player_id}) for season {season}")
    
    try:
        gamelog = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            season_type_all_star='Regular Season'
        )
        
        df = gamelog.get_data_frames()[0]
        
        if df.empty:
            logger.warning(f"No games found for {player_name} in season {season}")
        else:
            logger.info(f"Found {len(df)} games for {player_name} in season {season}")
        
        return df
    
    except Exception as e:
        logger.error(f"Error fetching game log: {str(e)}")
        return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser(description='Fetch a player\'s game log')
    parser.add_argument('player', help='Player name to search for')
    parser.add_argument('--season', default='2023-24', help='Season in format YYYY-YY')
    parser.add_argument('--save', action='store_true', help='Save game log to CSV')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    logger = setup_logging(args.verbose)
    
    # Find player
    player_id, player_name = find_player_by_name(args.player, logger)
    if not player_id:
        return
    
    # Get game log
    df = get_player_gamelog(player_id, player_name, args.season, logger)
    
    if df.empty:
        return
    
    # Display key stats
    display_cols = ['GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG_PCT', 'FG3_PCT', 'FT_PCT']
    print("\nGame Log:")
    print(df[display_cols].head().to_string())
    
    # Calculate averages
    print("\nSeason Averages:")
    for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV']:
        avg = df[col].mean()
        print(f"  {col}: {avg:.1f}")
    
    # Save to CSV if requested
    if args.save:
        filename = f"{player_name.replace(' ', '_')}_{args.season}_gamelog.csv"
        df.to_csv(filename, index=False)
        logger.info(f"Saved game log to {filename}")

if __name__ == '__main__':
    main() 
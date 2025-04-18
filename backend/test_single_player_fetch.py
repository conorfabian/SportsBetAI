#!/usr/bin/env python
"""
Test script to fetch and store data for a single NBA player.
Used for testing the data fetcher without processing all players.
"""
import logging
import argparse
import pandas as pd
from nba_api.stats.endpoints import commonallplayers, playergamelog
from app import create_app, db
from app.models.base import Player, Game, PlayerStats
from app.utils.historical_data_fetcher import save_to_database, fetch_player_game_logs

def setup_logging(verbose=False):
    """Configure logging for the script"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def find_player_by_name(player_name):
    """
    Find a player's ID by name
    
    Args:
        player_name (str): Player name to search for
        
    Returns:
        tuple: (player_id, full_name) or (None, None) if not found
    """
    try:
        all_players = commonallplayers.CommonAllPlayers()
        players_df = all_players.get_data_frames()[0]
        
        # Case-insensitive search
        matching_players = players_df[players_df['DISPLAY_FIRST_LAST'].str.lower().str.contains(player_name.lower())]
        
        if matching_players.empty:
            return None, None
        
        # Take the first match
        player_id = matching_players.iloc[0]['PERSON_ID']
        full_name = matching_players.iloc[0]['DISPLAY_FIRST_LAST']
        
        return player_id, full_name
    
    except Exception as e:
        logging.error(f"Error finding player: {str(e)}")
        return None, None

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Test fetch data for a single NBA player')
    parser.add_argument('player', help='Player name to search for')
    parser.add_argument('--seasons', nargs='+', default=['2023-24'], help='Seasons to fetch (format: YYYY-YY)')
    parser.add_argument('--save', action='store_true', help='Save data to database')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    logger = setup_logging(args.verbose)
    
    # Find player by name
    player_id, full_name = find_player_by_name(args.player)
    
    if not player_id:
        logger.error(f"Player '{args.player}' not found")
        return
    
    logger.info(f"Found player: {full_name} (ID: {player_id})")
    
    # Fetch game logs
    game_logs = fetch_player_game_logs(player_id, full_name, args.seasons)
    
    if game_logs.empty:
        logger.warning(f"No game logs found for {full_name} in seasons: {', '.join(args.seasons)}")
        return
    
    # Print summary of fetched data
    logger.info(f"Fetched {len(game_logs)} game logs for {full_name}")
    
    # Display first few games
    pd.set_option('display.max_columns', None)
    print("\nSample of game logs:")
    print(game_logs[['GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV']].head())
    
    if args.save:
        logger.info(f"Saving game logs to database...")
        
        app = create_app()
        with app.app_context():
            # Check if player exists, create if not
            player_obj = Player.query.filter_by(nba_api_id=player_id).first()
            if not player_obj:
                player_obj = Player(
                    nba_api_id=player_id,
                    full_name=full_name
                )
                db.session.add(player_obj)
                db.session.commit()
                logger.info(f"Added new player: {full_name}")
            
            # Save game logs
            saved_count = save_to_database(game_logs, player_obj)
            logger.info(f"Saved {saved_count} game logs to database")

if __name__ == '__main__':
    main() 
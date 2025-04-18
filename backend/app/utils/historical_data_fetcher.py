from nba_api.stats.endpoints import playergamelog, commonallplayers
import pandas as pd
from datetime import datetime, timedelta
import logging
import time
from app import db, create_app
from app.models.base import Player, Game, PlayerStats

logger = logging.getLogger(__name__)

def get_active_players():
    """
    Fetch all active NBA players
    
    Returns:
        DataFrame: DataFrame containing active players info
    """
    try:
        logger.info("Fetching active NBA players...")
        
        # Get all players, then filter for active players
        all_players = commonallplayers.CommonAllPlayers(is_only_current_season=1)
        players_df = all_players.get_data_frames()[0]
        
        # Filter for active players (where TO_YEAR is the current season)
        current_season = datetime.now().year if datetime.now().month > 9 else datetime.now().year - 1
        active_players = players_df[players_df['TO_YEAR'] == current_season]
        
        logger.info(f"Found {len(active_players)} active NBA players")
        return active_players
    
    except Exception as e:
        logger.error(f"Error fetching active players: {str(e)}")
        return pd.DataFrame()

def fetch_player_game_logs(player_id, player_name, seasons):
    """
    Fetch game logs for a player for multiple seasons
    
    Args:
        player_id (int): NBA API player ID
        player_name (str): Player's name for logging
        seasons (list): List of seasons in format 'YYYY-YY'
    
    Returns:
        DataFrame: Concatenated DataFrame of all seasons' game logs
    """
    all_seasons_df = pd.DataFrame()
    
    for season in seasons:
        try:
            logger.info(f"Fetching {season} game logs for {player_name} (ID: {player_id})")
            
            # Add delay to avoid rate limiting
            time.sleep(0.6)
            
            gamelog = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=season,
                season_type_all_star='Regular Season'
            )
            
            df = gamelog.get_data_frames()[0]
            
            if not df.empty:
                df['SEASON'] = season
                all_seasons_df = pd.concat([all_seasons_df, df])
                logger.info(f"Added {len(df)} games from {season} for {player_name}")
            else:
                logger.warning(f"No games found for {player_name} in season {season}")
                
        except Exception as e:
            logger.error(f"Error fetching {season} game logs for {player_name}: {str(e)}")
            # Continue with next season instead of failing completely
            continue
    
    return all_seasons_df

def save_to_database(game_logs_df, player_obj):
    """
    Save game log data to database
    
    Args:
        game_logs_df (DataFrame): Game logs data
        player_obj (Player): Player model object
    
    Returns:
        int: Number of records saved
    """
    if game_logs_df.empty:
        logger.warning(f"No game logs to save for player {player_obj.full_name}")
        return 0
    
    saved_count = 0
    
    for _, row in game_logs_df.iterrows():
        try:
            # Parse game date
            game_date = datetime.strptime(row['GAME_DATE'], '%Y-%m-%d').date()
            
            # Parse matchup to get teams
            matchup = row['MATCHUP']
            home_game = 'vs.' in matchup
            teams = matchup.split(' ')
            player_team = teams[0]
            opponent_team = teams[2]
            
            if home_game:
                home_team = player_team
                away_team = opponent_team
                home_away = 'HOME'
            else:
                home_team = opponent_team
                away_team = player_team
                home_away = 'AWAY'
            
            # Check if the game already exists
            game = Game.query.filter_by(
                game_date=game_date,
                home_team=home_team,
                away_team=away_team
            ).first()
            
            if not game:
                game = Game(
                    game_date=game_date,
                    home_team=home_team,
                    away_team=away_team
                )
                db.session.add(game)
                db.session.flush()  # Get the ID without committing
            
            # Check if stats already exist
            existing_stats = PlayerStats.query.filter_by(
                player_id=player_obj.id,
                game_id=game.id
            ).first()
            
            if not existing_stats:
                # Create new stats record with all the available fields
                stats = PlayerStats(
                    player_id=player_obj.id,
                    game_id=game.id,
                    
                    # Basic stats
                    points=row['PTS'],
                    rebounds=row['REB'],
                    assists=row['AST'],
                    steals=row['STL'],
                    blocks=row['BLK'],
                    turnovers=row['TOV'],
                    
                    # Minutes played
                    minutes=row['MIN'],
                    
                    # Shooting stats
                    field_goals_made=row['FGM'],
                    field_goals_attempted=row['FGA'],
                    field_goal_pct=row['FG_PCT'],
                    three_pointers_made=row['FG3M'],
                    three_pointers_attempted=row['FG3A'],
                    three_point_pct=row['FG3_PCT'],
                    free_throws_made=row['FTM'],
                    free_throws_attempted=row['FTA'],
                    free_throw_pct=row['FT_PCT'],
                    
                    # Game context
                    home_away=home_away,
                    win_loss=row['WL'],
                    
                    # Advanced metrics
                    plus_minus=row['PLUS_MINUS']
                )
                db.session.add(stats)
                saved_count += 1
        
        except Exception as e:
            logger.error(f"Error saving game log for {player_obj.full_name}: {str(e)}")
            db.session.rollback()
            continue
    
    # Commit all changes at once
    if saved_count > 0:
        try:
            db.session.commit()
            logger.info(f"Saved {saved_count} game logs for {player_obj.full_name}")
        except Exception as e:
            logger.error(f"Error committing game logs for {player_obj.full_name}: {str(e)}")
            db.session.rollback()
            saved_count = 0
    
    return saved_count

def fetch_and_store_historical_data(seasons=None):
    """
    Main function to fetch and store historical data for all active players
    
    Args:
        seasons (list): List of seasons to fetch data for, defaults to last 3 seasons
    
    Returns:
        dict: Summary of the operation
    """
    # Default to the last 3 seasons if not specified
    if not seasons:
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # If we're before October, we need to adjust the current season
        if current_month < 10:
            current_year -= 1
            
        seasons = [
            f"{current_year-2}-{str(current_year-1)[2:]}",
            f"{current_year-1}-{str(current_year)[2:]}",
            f"{current_year}-{str(current_year+1)[2:]}"
        ]
    
    logger.info(f"Starting historical data fetch for seasons: {', '.join(seasons)}")
    
    app = create_app()
    with app.app_context():
        active_players = get_active_players()
        
        if active_players.empty:
            return {"status": "error", "message": "Failed to fetch active players"}
        
        total_players = len(active_players)
        processed_players = 0
        successful_players = 0
        total_games_saved = 0
        
        for _, player in active_players.iterrows():
            player_id = player['PERSON_ID']
            player_name = f"{player['DISPLAY_FIRST_LAST']}"
            
            # Check if player exists in database, create if not
            player_obj = Player.query.filter_by(nba_api_id=player_id).first()
            if not player_obj:
                player_obj = Player(
                    nba_api_id=player_id,
                    full_name=player_name
                )
                db.session.add(player_obj)
                try:
                    db.session.commit()
                    logger.info(f"Added new player: {player_name}")
                except Exception as e:
                    logger.error(f"Error adding player {player_name}: {str(e)}")
                    db.session.rollback()
                    processed_players += 1
                    continue
            
            # Fetch game logs for the player
            game_logs = fetch_player_game_logs(player_id, player_name, seasons)
            
            # Save game logs to database
            if not game_logs.empty:
                games_saved = save_to_database(game_logs, player_obj)
                total_games_saved += games_saved
                
                if games_saved > 0:
                    successful_players += 1
            
            processed_players += 1
            logger.info(f"Processed {processed_players}/{total_players} players")
            
            # Add a short delay between players to avoid API rate limiting
            time.sleep(1)
        
        return {
            "status": "success",
            "total_players": total_players,
            "successful_players": successful_players,
            "total_games_saved": total_games_saved,
            "seasons": seasons
        }

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the data fetcher
    result = fetch_and_store_historical_data()
    print(f"Historical data fetch completed: {result}") 
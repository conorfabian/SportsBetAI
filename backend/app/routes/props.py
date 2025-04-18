import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from app.models.base import Player, PropLine, Prediction, Game, PlayerStats
from app import db, limiter
from sqlalchemy import desc
from app.utils.inference_service import get_inference_service
from app.utils.error_handlers import (
    PlayerNotFoundError, PropNotFoundError, 
    InvalidDateFormatError, DatabaseError
)

# Create a blueprint for props routes
bp = Blueprint('props', __name__, url_prefix='/api/props')
logger = logging.getLogger(__name__)

@bp.route('/', methods=['GET'])
@limiter.limit(requests=100, period=3600)  # 100 requests per hour
def get_props():
    """
    Get a list of all props for a specific date, sorted by probability.
    
    Query Parameters:
        date (str): Date in format YYYY-MM-DD (defaults to today)
    
    Returns:
        JSON response with props data sorted by prob_over DESC
    """
    # Add debug logging
    logger.info("get_props endpoint called")
    
    # Get date parameter (default to today)
    date_str = request.args.get('date', None)
    logger.info(f"Date parameter: {date_str}")
    
    try:
        # Parse the date if provided to use in the response
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                formatted_date = date_obj.strftime('%Y-%m-%d')
                logger.info(f"Parsed date: {formatted_date}")
            except ValueError:
                logger.error(f"Invalid date format: {date_str}")
                formatted_date = datetime.now().strftime('%Y-%m-%d')
        else:
            formatted_date = datetime.now().strftime('%Y-%m-%d')
            logger.info(f"Using default date: {formatted_date}")
        
        # Return enhanced mock data for testing
        logger.info("Preparing mock data")
        mock_data = [
            # Game 1: Lakers vs Warriors
            {
                'player_id': 1,
                'full_name': 'LeBron James',
                'line': 25.5,
                'prob_over': 0.72,
                'confidence_interval': 7.5,
                'home_team': 'LAL',
                'away_team': 'GSW',
                'game_time': '19:30',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 2,
                'full_name': 'Stephen Curry',
                'line': 28.5,
                'prob_over': 0.65,
                'confidence_interval': 6.8,
                'home_team': 'LAL',
                'away_team': 'GSW',
                'game_time': '19:30',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 3,
                'full_name': 'Anthony Davis',
                'line': 24.5,
                'prob_over': 0.56,
                'confidence_interval': 7.4,
                'home_team': 'LAL',
                'away_team': 'GSW',
                'game_time': '19:30',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 4,
                'full_name': 'Klay Thompson',
                'line': 18.5,
                'prob_over': 0.48,
                'confidence_interval': 8.0,
                'home_team': 'LAL',
                'away_team': 'GSW',
                'game_time': '19:30',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            
            # Game 2: Suns vs Nuggets
            {
                'player_id': 5,
                'full_name': 'Kevin Durant',
                'line': 29.5,
                'prob_over': 0.58,
                'confidence_interval': 8.2,
                'home_team': 'PHX',
                'away_team': 'DEN',
                'game_time': '20:00',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 6,
                'full_name': 'Nikola Jokic',
                'line': 26.5,
                'prob_over': 0.61,
                'confidence_interval': 7.1,
                'home_team': 'PHX',
                'away_team': 'DEN',
                'game_time': '20:00',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 7,
                'full_name': 'Devin Booker',
                'line': 26.0,
                'prob_over': 0.52,
                'confidence_interval': 7.8,
                'home_team': 'PHX',
                'away_team': 'DEN',
                'game_time': '20:00',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 8,
                'full_name': 'Jamal Murray',
                'line': 21.5,
                'prob_over': 0.47,
                'confidence_interval': 8.3,
                'home_team': 'PHX',
                'away_team': 'DEN',
                'game_time': '20:00',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            
            # Game 3: 76ers vs Celtics
            {
                'player_id': 9,
                'full_name': 'Joel Embiid',
                'line': 31.5,
                'prob_over': 0.48,
                'confidence_interval': 8.5,
                'home_team': 'PHI',
                'away_team': 'BOS',
                'game_time': '18:00',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 10,
                'full_name': 'Jayson Tatum',
                'line': 27.5,
                'prob_over': 0.53,
                'confidence_interval': 7.8,
                'home_team': 'PHI',
                'away_team': 'BOS',
                'game_time': '18:00',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 11,
                'full_name': 'Jaylen Brown',
                'line': 24.0,
                'prob_over': 0.56,
                'confidence_interval': 7.6,
                'home_team': 'PHI',
                'away_team': 'BOS',
                'game_time': '18:00',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 12,
                'full_name': 'Tyrese Maxey',
                'line': 25.5,
                'prob_over': 0.62,
                'confidence_interval': 7.3,
                'home_team': 'PHI',
                'away_team': 'BOS',
                'game_time': '18:00',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            
            # Game 4: Mavericks vs Thunder
            {
                'player_id': 13,
                'full_name': 'Luka Doncic',
                'line': 32.5,
                'prob_over': 0.68,
                'confidence_interval': 6.5,
                'home_team': 'DAL',
                'away_team': 'OKC',
                'game_time': '19:00',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 14,
                'full_name': 'Shai Gilgeous-Alexander',
                'line': 30.5,
                'prob_over': 0.59,
                'confidence_interval': 7.2,
                'home_team': 'DAL',
                'away_team': 'OKC',
                'game_time': '19:00',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 15,
                'full_name': 'Kyrie Irving',
                'line': 24.5,
                'prob_over': 0.54,
                'confidence_interval': 7.7,
                'home_team': 'DAL',
                'away_team': 'OKC',
                'game_time': '19:00',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 16,
                'full_name': 'Chet Holmgren',
                'line': 16.5,
                'prob_over': 0.45,
                'confidence_interval': 8.4,
                'home_team': 'DAL',
                'away_team': 'OKC',
                'game_time': '19:00',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            
            # Game 5: Bucks vs Pacers
            {
                'player_id': 17,
                'full_name': 'Giannis Antetokounmpo',
                'line': 30.5,
                'prob_over': 0.73,
                'confidence_interval': 6.9,
                'home_team': 'MIL',
                'away_team': 'IND',
                'game_time': '17:30',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 18,
                'full_name': 'Damian Lillard',
                'line': 26.0,
                'prob_over': 0.63,
                'confidence_interval': 7.0,
                'home_team': 'MIL',
                'away_team': 'IND',
                'game_time': '17:30',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 19,
                'full_name': 'Tyrese Haliburton',
                'line': 22.5,
                'prob_over': 0.46,
                'confidence_interval': 8.8,
                'home_team': 'MIL',
                'away_team': 'IND',
                'game_time': '17:30',
                'last_updated': f'{formatted_date} 10:00:00'
            },
            {
                'player_id': 20,
                'full_name': 'Pascal Siakam',
                'line': 20.5,
                'prob_over': 0.51,
                'confidence_interval': 8.0,
                'home_team': 'MIL',
                'away_team': 'IND',
                'game_time': '17:30',
                'last_updated': f'{formatted_date} 10:00:00'
            }
        ]
        
        # Sort by probability descending (highest probability first)
        logger.info("Sorting mock data")
        mock_data = sorted(mock_data, key=lambda x: x['prob_over'], reverse=True)
        
        logger.info(f"Returning {len(mock_data)} props")
        return jsonify(mock_data[:5])  # Return only first 5 for testing
        
    except InvalidDateFormatError as e:
        # Already formatted properly
        logger.error(f"Invalid date format error: {e}")
        raise e
    except Exception as e:
        logger.error(f"Error retrieving props: {e}", exc_info=True)
        # Convert to database error if applicable
        if "database" in str(e).lower() or "sql" in str(e).lower():
            raise DatabaseError("retrieving props")
        # Return a simple error response instead of re-raising
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@bp.route('/player', methods=['GET'])
@limiter.limit(requests=150, period=3600)  # 150 requests per hour for player lookup
def get_player_props():
    """
    Get props for a specific player.
    
    Query Parameters:
        name (str): Player name to search for (fuzzy match)
        date (str, optional): Date in format YYYY-MM-DD (defaults to today)
    
    Returns:
        JSON response with player props data
    """
    # Get player name parameter
    player_name = request.args.get('name', None)
    date_str = request.args.get('date', None)
    
    if not player_name:
        return jsonify({"error": "Player name is required"}), 400
    
    try:
        # Parse date if provided
        if date_str:
            try:
                game_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                formatted_date = game_date.strftime('%Y-%m-%d')
            except ValueError:
                raise InvalidDateFormatError(date_str)
        else:
            # Use today's date by default
            game_date = datetime.now().date()
            formatted_date = game_date.strftime('%Y-%m-%d')
        
        # Create mock data based on the requested player name
        # Define player database with mock data
        player_database = {
            'lebron': {
                'id': 1,
                'full_name': 'LeBron James',
                'team': 'LAL',
                'game': {
                    'home_team': 'LAL',
                    'away_team': 'GSW',
                    'game_time': '19:30'
                },
                'prop': {
                    'line': 25.5,
                    'sportsbook': 'FanDuel'
                },
                'prediction': {
                    'prob_over': 0.72,
                    'confidence_interval': 7.5
                },
                'recent_games': [
                    {'game_date': '2025-04-16', 'matchup': 'LAL @ SAC', 'points': 28, 'minutes': 36, 'field_goals': '12-18', 'field_goal_pct': 0.667},
                    {'game_date': '2025-04-14', 'matchup': 'POR @ LAL', 'points': 23, 'minutes': 32, 'field_goals': '9-15', 'field_goal_pct': 0.6},
                    {'game_date': '2025-04-12', 'matchup': 'LAL @ DEN', 'points': 31, 'minutes': 38, 'field_goals': '14-22', 'field_goal_pct': 0.636},
                    {'game_date': '2025-04-10', 'matchup': 'UTA @ LAL', 'points': 26, 'minutes': 34, 'field_goals': '10-17', 'field_goal_pct': 0.588},
                    {'game_date': '2025-04-08', 'matchup': 'LAL @ PHX', 'points': 20, 'minutes': 30, 'field_goals': '7-16', 'field_goal_pct': 0.438}
                ],
                'season_stats': {
                    'avg_points': 25.8,
                    'avg_minutes': 34.2,
                    'games_played': 68
                }
            },
            'giannis': {
                'id': 17,
                'full_name': 'Giannis Antetokounmpo',
                'team': 'MIL',
                'game': {
                    'home_team': 'MIL',
                    'away_team': 'IND',
                    'game_time': '17:30'
                },
                'prop': {
                    'line': 30.5,
                    'sportsbook': 'FanDuel'
                },
                'prediction': {
                    'prob_over': 0.73,
                    'confidence_interval': 6.9
                },
                'recent_games': [
                    {'game_date': '2025-04-16', 'matchup': 'MIL @ DET', 'points': 34, 'minutes': 35, 'field_goals': '13-19', 'field_goal_pct': 0.684},
                    {'game_date': '2025-04-14', 'matchup': 'CHI @ MIL', 'points': 32, 'minutes': 36, 'field_goals': '14-21', 'field_goal_pct': 0.667},
                    {'game_date': '2025-04-12', 'matchup': 'MIL @ WAS', 'points': 29, 'minutes': 33, 'field_goals': '12-18', 'field_goal_pct': 0.667},
                    {'game_date': '2025-04-10', 'matchup': 'ORL @ MIL', 'points': 35, 'minutes': 38, 'field_goals': '15-22', 'field_goal_pct': 0.682},
                    {'game_date': '2025-04-08', 'matchup': 'MIL @ CLE', 'points': 27, 'minutes': 30, 'field_goals': '11-17', 'field_goal_pct': 0.647}
                ],
                'season_stats': {
                    'avg_points': 31.2,
                    'avg_minutes': 34.8,
                    'games_played': 72
                }
            },
            'luka': {
                'id': 13,
                'full_name': 'Luka Doncic',
                'team': 'DAL',
                'game': {
                    'home_team': 'DAL',
                    'away_team': 'OKC',
                    'game_time': '19:00'
                },
                'prop': {
                    'line': 32.5,
                    'sportsbook': 'FanDuel'
                },
                'prediction': {
                    'prob_over': 0.68,
                    'confidence_interval': 6.5
                },
                'recent_games': [
                    {'game_date': '2025-04-16', 'matchup': 'DAL @ MEM', 'points': 36, 'minutes': 38, 'field_goals': '13-24', 'field_goal_pct': 0.542},
                    {'game_date': '2025-04-14', 'matchup': 'HOU @ DAL', 'points': 33, 'minutes': 35, 'field_goals': '12-20', 'field_goal_pct': 0.6},
                    {'game_date': '2025-04-12', 'matchup': 'DAL @ SAS', 'points': 30, 'minutes': 36, 'field_goals': '11-21', 'field_goal_pct': 0.524},
                    {'game_date': '2025-04-10', 'matchup': 'CHA @ DAL', 'points': 38, 'minutes': 39, 'field_goals': '15-25', 'field_goal_pct': 0.6},
                    {'game_date': '2025-04-08', 'matchup': 'DAL @ UTA', 'points': 26, 'minutes': 32, 'field_goals': '9-21', 'field_goal_pct': 0.429}
                ],
                'season_stats': {
                    'avg_points': 33.1,
                    'avg_minutes': 36.5,
                    'games_played': 70
                }
            }
        }
        
        # Find the player (case-insensitive search)
        found_player = None
        search_term = player_name.lower()
        
        # Check for exact match first
        if search_term in player_database:
            found_player = player_database[search_term]
        else:
            # Then try partial match
            for key, player_data in player_database.items():
                if search_term in player_data['full_name'].lower():
                    found_player = player_data
                    break
        
        # If still not found, check the hard-coded list for an approximate match
        if not found_player:
            for player_data in get_props.__defaults__[0]:  # Access the mock data from get_props
                if search_term in player_data['full_name'].lower():
                    player_id = player_data['player_id']
                    
                    # Create a simple profile for this player
                    found_player = {
                        'id': player_id,
                        'full_name': player_data['full_name'],
                        'team': player_data['home_team'] if player_data['home_team'] != player_data['away_team'] else player_data['away_team'],
                        'game': {
                            'home_team': player_data['home_team'],
                            'away_team': player_data['away_team'],
                            'game_time': player_data['game_time']
                        },
                        'prop': {
                            'line': player_data['line'],
                            'sportsbook': 'FanDuel'
                        },
                        'prediction': {
                            'prob_over': player_data['prob_over'],
                            'confidence_interval': player_data['confidence_interval']
                        },
                        'recent_games': [
                            {'game_date': '2025-04-16', 'matchup': 'Team1 @ Team2', 'points': 22, 'minutes': 30, 'field_goals': '8-15', 'field_goal_pct': 0.533},
                            {'game_date': '2025-04-14', 'matchup': 'Team3 @ Team4', 'points': 24, 'minutes': 32, 'field_goals': '9-18', 'field_goal_pct': 0.5},
                            {'game_date': '2025-04-12', 'matchup': 'Team5 @ Team6', 'points': 19, 'minutes': 28, 'field_goals': '7-16', 'field_goal_pct': 0.438},
                            {'game_date': '2025-04-10', 'matchup': 'Team7 @ Team8', 'points': 25, 'minutes': 33, 'field_goals': '10-19', 'field_goal_pct': 0.526},
                            {'game_date': '2025-04-08', 'matchup': 'Team9 @ Team10', 'points': 21, 'minutes': 31, 'field_goals': '8-17', 'field_goal_pct': 0.471}
                        ],
                        'season_stats': {
                            'avg_points': 23.5,
                            'avg_minutes': 31.2,
                            'games_played': 65
                        }
                    }
                    break
        
        if not found_player:
            # Player not found, return 404
            raise PlayerNotFoundError(player_name=player_name)
        
        # Format response
        response = {
            'player': {
                'id': found_player['id'],
                'name': found_player['full_name'],
                'team': found_player['team']
            },
            'game': {
                'date': formatted_date,
                'time': found_player['game']['game_time'],
                'home_team': found_player['game']['home_team'],
                'away_team': found_player['game']['away_team'],
                'matchup': f"{found_player['game']['away_team']} @ {found_player['game']['home_team']}"
            },
            'prop': {
                'id': found_player['id'] * 10,  # Just a dummy prop ID
                'line': found_player['prop']['line'],
                'sportsbook': found_player['prop']['sportsbook'],
                'fetched_at': f"{formatted_date} 09:30:00"
            },
            'stats': {
                'recent_games': found_player['recent_games'],
                'season_avg_points': found_player['season_stats']['avg_points'],
                'season_avg_minutes': found_player['season_stats']['avg_minutes'],
                'games_played': found_player['season_stats']['games_played']
            }
        }
        
        # Add prediction if available
        if 'prediction' in found_player:
            response['prediction'] = {
                'prob_over': found_player['prediction']['prob_over'],
                'confidence_interval': found_player['prediction']['confidence_interval'],
                'generated_at': f"{formatted_date} 10:00:00"
            }
        
        return jsonify(response)
        
    except (PlayerNotFoundError, PropNotFoundError, InvalidDateFormatError) as e:
        # These are already formatted properly
        raise e
    except Exception as e:
        logger.error(f"Error retrieving player props: {e}", exc_info=True)
        # Convert to database error if applicable
        if "database" in str(e).lower() or "sql" in str(e).lower():
            raise DatabaseError("retrieving player props")
        # Re-raise if it's another type of error
        raise

@bp.route('/generate', methods=['POST'])
@limiter.limit(requests=20, period=3600)  # 20 requests per hour for manual prediction generation
def generate_predictions():
    """
    Manually trigger prediction generation for a specific date.
    
    JSON Body:
        date (str, optional): Date in format YYYY-MM-DD (defaults to today)
        player_id (int, optional): Player ID to generate predictions for
    
    Returns:
        JSON response with generation status
    """
    # Get request data
    data = request.get_json() or {}
    date_str = data.get('date', None)
    player_id = data.get('player_id', None)
    
    try:
        if date_str:
            try:
                # Parse the date string
                game_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                raise InvalidDateFormatError(date_str)
        else:
            # Use today's date
            game_date = datetime.now().date()
            
        # Validate player_id if provided
        if player_id is not None:
            app = current_app._get_current_object()
            with app.app_context():
                player = Player.query.get(player_id)
                if not player:
                    raise PlayerNotFoundError(player_id=player_id)
            
        # Get the inference service
        inference_service = get_inference_service()
        
        # Run inference pipeline
        predictions_df = inference_service.run_inference_pipeline(
            player_id=player_id, 
            game_date=game_date
        )
        
        if predictions_df is not None:
            return jsonify({
                "status": "success",
                "message": f"Generated {len(predictions_df)} predictions",
                "count": len(predictions_df)
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to generate predictions"
            }), 500
            
    except (PlayerNotFoundError, InvalidDateFormatError) as e:
        # These are already formatted properly
        raise e
    except Exception as e:
        logger.error(f"Error generating predictions: {e}", exc_info=True)
        # Convert to database error if applicable
        if "database" in str(e).lower() or "sql" in str(e).lower():
            raise DatabaseError("generating predictions")
        # Re-raise if it's another type of error
        raise

@bp.route('/players', methods=['GET'])
@limiter.limit(requests=50, period=3600)  # 50 requests per hour for this less critical endpoint
def get_players():
    """Get a list of all players in the database"""
    players = Player.query.all()
    
    return jsonify({
        'status': 'success',
        'count': len(players),
        'players': [{'id': p.id, 'name': p.full_name, 'nba_api_id': p.nba_api_id} for p in players]
    })

@bp.route('/players/search', methods=['GET'])
@limiter.limit(requests=150, period=3600)  # 150 requests per hour for search
def search_players():
    """Search for players by name"""
    query = request.args.get('q', '')
    
    if not query or len(query) < 2:
        return jsonify({
            'status': 'error',
            'message': 'Search query must be at least 2 characters long'
        }), 400
    
    # Mock player data
    all_players = [
        {'id': 1, 'name': 'LeBron James', 'nba_api_id': 2544},
        {'id': 2, 'name': 'Stephen Curry', 'nba_api_id': 201939},
        {'id': 3, 'name': 'Anthony Davis', 'nba_api_id': 203076},
        {'id': 4, 'name': 'Klay Thompson', 'nba_api_id': 202691},
        {'id': 5, 'name': 'Kevin Durant', 'nba_api_id': 201142},
        {'id': 6, 'name': 'Nikola Jokic', 'nba_api_id': 203999},
        {'id': 7, 'name': 'Devin Booker', 'nba_api_id': 1626164},
        {'id': 8, 'name': 'Jamal Murray', 'nba_api_id': 1627750},
        {'id': 9, 'name': 'Joel Embiid', 'nba_api_id': 203954},
        {'id': 10, 'name': 'Jayson Tatum', 'nba_api_id': 1628369},
        {'id': 11, 'name': 'Jaylen Brown', 'nba_api_id': 1627759},
        {'id': 12, 'name': 'Tyrese Maxey', 'nba_api_id': 1630178},
        {'id': 13, 'name': 'Luka Doncic', 'nba_api_id': 1629029},
        {'id': 14, 'name': 'Shai Gilgeous-Alexander', 'nba_api_id': 1628983},
        {'id': 15, 'name': 'Kyrie Irving', 'nba_api_id': 202681},
        {'id': 16, 'name': 'Chet Holmgren', 'nba_api_id': 1631096},
        {'id': 17, 'name': 'Giannis Antetokounmpo', 'nba_api_id': 203507},
        {'id': 18, 'name': 'Damian Lillard', 'nba_api_id': 203081},
        {'id': 19, 'name': 'Tyrese Haliburton', 'nba_api_id': 1630169},
        {'id': 20, 'name': 'Pascal Siakam', 'nba_api_id': 1627783}
    ]
    
    # Case-insensitive search
    search_term = query.lower()
    found_players = [player for player in all_players if search_term in player['name'].lower()]
    
    return jsonify({
        'status': 'success',
        'count': len(found_players),
        'players': found_players
    })

@bp.route('/players/<int:player_id>/stats', methods=['GET'])
def get_player_stats(player_id):
    """Get stats for a specific player"""
    # Check if player exists
    player = Player.query.get(player_id)
    if not player:
        return jsonify({
            'status': 'error',
            'message': f'Player with ID {player_id} not found'
        }), 404
    
    # Get limit and offset from query params
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Get player's stats, ordered by game date (most recent first)
    stats_query = (
        db.session.query(PlayerStats, Game)
        .join(Game, PlayerStats.game_id == Game.id)
        .filter(PlayerStats.player_id == player_id)
        .order_by(desc(Game.game_date))
    )
    
    # Count total records for pagination
    total_stats = stats_query.count()
    
    # Apply pagination
    stats = stats_query.limit(limit).offset(offset).all()
    
    # Format the results
    stats_list = []
    for stat, game in stats:
        stats_list.append({
            'game_date': game.game_date.strftime('%Y-%m-%d'),
            'home_team': game.home_team,
            'away_team': game.away_team,
            'home_away': stat.home_away,
            'win_loss': stat.win_loss,
            'minutes': stat.minutes,
            'points': stat.points,
            'rebounds': stat.rebounds,
            'assists': stat.assists,
            'steals': stat.steals,
            'blocks': stat.blocks,
            'turnovers': stat.turnovers,
            'field_goals': f"{stat.field_goals_made}-{stat.field_goals_attempted}",
            'field_goal_pct': stat.field_goal_pct,
            'three_pointers': f"{stat.three_pointers_made}-{stat.three_pointers_attempted}",
            'three_point_pct': stat.three_point_pct,
            'free_throws': f"{stat.free_throws_made}-{stat.free_throws_attempted}",
            'free_throw_pct': stat.free_throw_pct,
            'plus_minus': stat.plus_minus
        })
    
    return jsonify({
        'status': 'success',
        'player': {
            'id': player.id,
            'name': player.full_name,
            'nba_api_id': player.nba_api_id
        },
        'stats': stats_list,
        'pagination': {
            'total': total_stats,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total_stats
        }
    })

@bp.route('/players/<int:player_id>/average', methods=['GET'])
def get_player_average_stats(player_id):
    """Get average stats for a specific player"""
    # Check if player exists
    player = Player.query.get(player_id)
    if not player:
        return jsonify({
            'status': 'error',
            'message': f'Player with ID {player_id} not found'
        }), 404
    
    # Get last N games limit from query params (default to last 10 games)
    last_n_games = request.args.get('last_n_games', 10, type=int)
    
    # Get player's recent game IDs, ordered by game date (most recent first)
    game_ids_subquery = (
        db.session.query(PlayerStats.game_id)
        .join(Game, PlayerStats.game_id == Game.id)
        .filter(PlayerStats.player_id == player_id)
        .order_by(desc(Game.game_date))
        .limit(last_n_games)
        .subquery()
    )
    
    # Get player's stats for these games
    stats = (
        db.session.query(PlayerStats)
        .filter(
            PlayerStats.player_id == player_id,
            PlayerStats.game_id.in_(game_ids_subquery)
        )
        .all()
    )
    
    if not stats:
        return jsonify({
            'status': 'error',
            'message': f'No stats found for player with ID {player_id}'
        }), 404
    
    # Calculate averages
    total_games = len(stats)
    
    # Initialize aggregates
    points_total = 0
    rebounds_total = 0
    assists_total = 0
    steals_total = 0
    blocks_total = 0
    turnovers_total = 0
    
    # Sum up the totals
    for stat in stats:
        points_total += stat.points if stat.points is not None else 0
        rebounds_total += stat.rebounds if stat.rebounds is not None else 0
        assists_total += stat.assists if stat.assists is not None else 0
        steals_total += stat.steals if stat.steals is not None else 0
        blocks_total += stat.blocks if stat.blocks is not None else 0
        turnovers_total += stat.turnovers if stat.turnovers is not None else 0
    
    # Calculate averages
    avg_stats = {
        'points': round(points_total / total_games, 1),
        'rebounds': round(rebounds_total / total_games, 1),
        'assists': round(assists_total / total_games, 1),
        'steals': round(steals_total / total_games, 1),
        'blocks': round(blocks_total / total_games, 1),
        'turnovers': round(turnovers_total / total_games, 1),
        'games_included': total_games
    }
    
    return jsonify({
        'status': 'success',
        'player': {
            'id': player.id,
            'name': player.full_name,
            'nba_api_id': player.nba_api_id
        },
        'average_stats': avg_stats,
        'period': f'Last {total_games} games'
    }) 
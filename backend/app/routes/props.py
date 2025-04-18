from flask import Blueprint, jsonify, request
from app.models.base import Player, PropLine, Prediction, Game, PlayerStats
from app import db
from datetime import datetime, date
from sqlalchemy import desc

props_bp = Blueprint('props', __name__, url_prefix='/api')

@props_bp.route('/props', methods=['GET'])
def get_props():
    """Get all props for a specific date"""
    # Default to today if no date provided
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    # This is a placeholder that will eventually return real data
    return jsonify({
        'status': 'success',
        'message': 'API is working!',
        'date': date_str,
        'props': []
    })

@props_bp.route('/props/player', methods=['GET'])
def get_player_prop():
    """Get prop for a specific player"""
    player_name = request.args.get('name', '')
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    if not player_name:
        return jsonify({
            'status': 'error',
            'message': 'Player name is required'
        }), 400
    
    # This is a placeholder that will eventually search for a player
    return jsonify({
        'status': 'success',
        'message': f'Player lookup for {player_name}',
        'date': date_str,
        'player': {
            'name': player_name,
            'prop': None
        }
    })

@props_bp.route('/players', methods=['GET'])
def get_players():
    """Get a list of all players in the database"""
    players = Player.query.all()
    
    return jsonify({
        'status': 'success',
        'count': len(players),
        'players': [{'id': p.id, 'name': p.full_name, 'nba_api_id': p.nba_api_id} for p in players]
    })

@props_bp.route('/players/search', methods=['GET'])
def search_players():
    """Search for players by name"""
    query = request.args.get('q', '')
    
    if not query or len(query) < 2:
        return jsonify({
            'status': 'error',
            'message': 'Search query must be at least 2 characters long'
        }), 400
    
    # Case-insensitive search
    players = Player.query.filter(Player.full_name.ilike(f'%{query}%')).all()
    
    return jsonify({
        'status': 'success',
        'count': len(players),
        'players': [{'id': p.id, 'name': p.full_name, 'nba_api_id': p.nba_api_id} for p in players]
    })

@props_bp.route('/players/<int:player_id>/stats', methods=['GET'])
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

@props_bp.route('/players/<int:player_id>/average', methods=['GET'])
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
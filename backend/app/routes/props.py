from flask import Blueprint, jsonify, request
from app.models.base import Player, PropLine, Prediction
from app import db
from datetime import datetime, date

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
import logging
from flask import jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, InternalServerError

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base exception for API errors with status code and message."""
    def __init__(self, message, status_code=400, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or {})
        rv['error'] = self.message
        rv['status'] = 'error'
        return rv

class PlayerNotFoundError(APIError):
    """Raised when a player cannot be found."""
    def __init__(self, player_name=None, player_id=None):
        message = "Player not found"
        if player_name:
            message = f"Player not found: '{player_name}'"
        elif player_id:
            message = f"Player not found with ID: {player_id}"
        super().__init__(message=message, status_code=404)

class PropNotFoundError(APIError):
    """Raised when a prop cannot be found."""
    def __init__(self, player_name=None, date=None):
        message = "Prop not found"
        if player_name and date:
            message = f"No prop found for {player_name} on {date}"
        elif player_name:
            message = f"No props found for {player_name}"
        elif date:
            message = f"No props found for date: {date}"
        super().__init__(message=message, status_code=404)

class ModelNotLoadedError(APIError):
    """Raised when prediction model cannot be loaded."""
    def __init__(self):
        super().__init__(
            message="Prediction model could not be loaded. Please try again later.",
            status_code=500
        )

class InvalidDateFormatError(APIError):
    """Raised when date format is invalid."""
    def __init__(self, date_str=None):
        message = "Invalid date format. Use YYYY-MM-DD format."
        if date_str:
            message = f"Invalid date format: '{date_str}'. Use YYYY-MM-DD format."
        super().__init__(message=message, status_code=400)

class DatabaseError(APIError):
    """Raised when a database error occurs."""
    def __init__(self, operation=None):
        message = "Database error occurred"
        if operation:
            message = f"Database error occurred during {operation}"
        super().__init__(message=message, status_code=500)

def register_error_handlers(app):
    """Register error handlers with the Flask app."""
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Handle custom API errors."""
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response
    
    @app.errorhandler(NotFound)
    def handle_not_found(error):
        """Handle 404 errors."""
        logger.info(f"Not found: {error}")
        return jsonify({
            'status': 'error',
            'error': 'Resource not found'
        }), 404
    
    @app.errorhandler(BadRequest)
    def handle_bad_request(error):
        """Handle 400 errors."""
        logger.info(f"Bad request: {error}")
        return jsonify({
            'status': 'error',
            'error': 'Bad request: ' + str(error)
        }), 400
    
    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        """Handle database errors."""
        logger.error(f"Database error: {error}")
        return jsonify({
            'status': 'error',
            'error': 'Database error occurred'
        }), 500
    
    @app.errorhandler(InternalServerError)
    def handle_internal_server_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'status': 'error',
            'error': 'Internal server error'
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all other exceptions."""
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': 'An unexpected error occurred'
        }), 500

    logger.info("Error handlers registered") 
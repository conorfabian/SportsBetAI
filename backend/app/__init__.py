import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
import threading

# Initialize database
db = SQLAlchemy()
migrate = Migrate()

# Initialize rate limiter (will be set in create_app)
limiter = None

def create_app(test_config=None):
    """Create and configure the Flask application"""
    app = Flask(__name__, instance_relative_config=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure app from environment variables or defaults
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key_change_in_production'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///sportsbetai.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # CORS settings
        CORS_ORIGINS=os.environ.get('CORS_ORIGINS', '*'),
        CORS_METHODS=['GET', 'POST', 'OPTIONS'],
        CORS_ALLOW_HEADERS=['Content-Type', 'Authorization'],
        CORS_MAX_AGE=86400,  # 24 hours in seconds
        # Rate limiting settings
        RATE_LIMIT_REQUESTS=os.environ.get('RATE_LIMIT_REQUESTS', 100),
        RATE_LIMIT_PERIOD=os.environ.get('RATE_LIMIT_PERIOD', 3600),  # 1 hour in seconds
        RATE_LIMIT_BY_ENDPOINT=os.environ.get('RATE_LIMIT_BY_ENDPOINT', False),
        REDIS_URL=os.environ.get('REDIS_URL')
    )
    
    # Apply test config if provided
    if test_config:
        app.config.from_mapping(test_config)
    
    # Initialize database with app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Configure CORS with specific options
    cors_origins = app.config['CORS_ORIGINS']
    if cors_origins != '*':
        # Split comma-separated string into list
        origins = [origin.strip() for origin in cors_origins.split(',')]
        app.logger.info(f"Configuring CORS for origins: {origins}")
    else:
        origins = '*'
        app.logger.info("Configuring CORS for all origins")
        
    CORS(app, 
         resources={r"/api/*": {
             "origins": origins,
             "methods": app.config['CORS_METHODS'],
             "allow_headers": app.config['CORS_ALLOW_HEADERS'],
             "max_age": app.config['CORS_MAX_AGE']
         }},
         supports_credentials=True)
    
    # Initialize rate limiter
    from app.utils.rate_limiter import RateLimiter
    global limiter
    limiter = RateLimiter(
        app=app,
        redis_url=app.config.get('REDIS_URL'),
        default_limits={
            "requests": int(app.config['RATE_LIMIT_REQUESTS']),
            "period": int(app.config['RATE_LIMIT_PERIOD']),
            "by_endpoint": bool(app.config['RATE_LIMIT_BY_ENDPOINT'])
        }
    )
    app.logger.info(f"Rate limiter initialized: {app.config['RATE_LIMIT_REQUESTS']} requests per {app.config['RATE_LIMIT_PERIOD']} seconds")
    
    # Create instance folder if it doesn't exist
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Register blueprints for API routes
    from app.routes import props
    app.register_blueprint(props.bp)
    
    # Register error handlers
    from app.utils.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    # Initialize inference service at app startup
    def initialize_services():
        from app.utils.inference_service import get_inference_service
        app.logger.info("Initializing inference service...")
        inference_service = get_inference_service()
        if inference_service.model is None:
            app.logger.error("Failed to initialize inference service: model could not be loaded")
        else:
            app.logger.info("Inference service initialized successfully")
    
    # Call the initialization function during app setup
    initialize_services()
    
    # Home route
    @app.route('/')
    def home():
        return {"status": "API running", "version": "1.0.0"}
    
    # Mock route for props (for testing)
    @app.route('/api/props/', methods=['GET'])
    def mock_props():
        """Temporary mock implementation that returns static data for testing"""
        mock_data = [
            {
                'player_id': 1,
                'full_name': 'LeBron James',
                'line': 25.5,
                'prob_over': 0.72,
                'confidence_interval': 7.5,
                'home_team': 'LAL',
                'away_team': 'GSW',
                'game_time': '19:30',
                'last_updated': '2025-04-18 10:00:00'
            },
            {
                'player_id': 9,
                'full_name': 'Giannis Antetokounmpo',
                'line': 30.5,
                'prob_over': 0.73,
                'confidence_interval': 6.9,
                'home_team': 'MIL',
                'away_team': 'IND',
                'game_time': '17:30',
                'last_updated': '2025-04-18 10:00:00'
            },
            {
                'player_id': 7,
                'full_name': 'Luka Doncic',
                'line': 32.5,
                'prob_over': 0.68,
                'confidence_interval': 6.5,
                'home_team': 'DAL',
                'away_team': 'OKC',
                'game_time': '19:00',
                'last_updated': '2025-04-18 10:00:00'
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
                'last_updated': '2025-04-18 10:00:00'
            },
            {
                'player_id': 4,
                'full_name': 'Nikola Jokic',
                'line': 26.5,
                'prob_over': 0.61,
                'confidence_interval': 7.1,
                'home_team': 'PHX',
                'away_team': 'DEN',
                'game_time': '20:00',
                'last_updated': '2025-04-18 10:00:00'
            }
        ]
        from flask import jsonify
        return jsonify(mock_data)
    
    # Start the scheduler in a background thread if not in testing mode
    if not test_config:
        try:
            # Temporarily commented out for testing
            # from app.utils.scheduler import run_scheduler
            # scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            # scheduler_thread.start()
            app.logger.info("Scheduler disabled for testing")
        except Exception as e:
            app.logger.error(f"Failed to start scheduler: {str(e)}")
    
    return app 
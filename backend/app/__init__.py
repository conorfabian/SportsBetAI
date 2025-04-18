from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import threading

# Initialize database
db = SQLAlchemy()
migrate = Migrate()

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Set up configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost/nba_props'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    
    # Initialize plugins
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.routes.props import props_bp
    app.register_blueprint(props_bp)
    
    # Start the scheduler in a background thread if not in testing mode
    if not test_config:
        from app.utils.scheduler import run_scheduler
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        app.logger.info("Started odds fetcher scheduler in background thread")
    
    # Sample route
    @app.route('/')
    def hello():
        return {'message': 'Hello, World!'}
    
    return app 
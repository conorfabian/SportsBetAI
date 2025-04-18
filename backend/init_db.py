#!/usr/bin/env python
"""
Initialize the database and create all tables.
This script should be run once when setting up the application for the first time.
"""
import logging
import argparse
from app import create_app, db

def setup_logging(verbose=False):
    """Configure logging for the script"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def init_db(app):
    """Initialize the database by creating all tables"""
    with app.app_context():
        db.create_all()
        logging.info("Database tables created successfully!")

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Initialize the database for the NBA Props application')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--drop-all', action='store_true', help='Drop all tables before creating them (WARNING: This will delete all data)')
    
    args = parser.parse_args()
    
    logger = setup_logging(args.verbose)
    
    app = create_app()
    
    if args.drop_all:
        logger.warning("WARNING: You have chosen to drop all tables. This will delete all existing data!")
        confirmation = input("Are you sure you want to proceed? (yes/no): ")
        if confirmation.lower() != 'yes':
            logger.info("Operation cancelled.")
            return
        
        with app.app_context():
            logger.info("Dropping all tables...")
            db.drop_all()
            logger.info("All tables dropped successfully.")
    
    logger.info("Initializing database...")
    init_db(app)
    logger.info("Database initialization complete.")
    
    logger.info("""
Successfully initialized the database!

Next steps:
1. Create a seed data sample by running:
   python -m app.utils.db_init

2. Fetch historical player data by running:
   python fetch_historical_data.py
   
3. Start the Flask application:
   python app.py
""")

if __name__ == '__main__':
    main() 
import os
import logging
import schedule
import time
from datetime import datetime, timedelta
import pytz
from odds_fetcher import fetch_live_prop_lines
from player_mapper import map_players_to_ids
from data_processor import run_data_processing
from prediction_service import run_daily_predictions
from feature_engineering import main as run_feature_engineering

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
EST_TIMEZONE = pytz.timezone('US/Eastern')
DB_CONNECTION_STRING = os.environ.get('DATABASE_URL')

def is_game_day():
    """
    Check if today is a game day. 
    In a production environment, this would check a games schedule API or database.
    For now, we'll assume all days are game days for demonstration purposes.
    
    Returns:
        bool: True if today is a game day, False otherwise
    """
    # TODO: Implement actual game day checking logic
    return True

def fetch_prop_lines_job():
    """
    Job to fetch prop lines and store them in the database.
    Only runs if it's a game day and within the specified time window.
    """
    now_est = datetime.now(EST_TIMEZONE)
    
    # Check if current time is between 3 PM and 6 PM EST
    if 15 <= now_est.hour <= 18:
        if is_game_day():
            logger.info(f"Running scheduled prop lines fetch at {now_est}")
            try:
                props = fetch_live_prop_lines(DB_CONNECTION_STRING)
                logger.info(f"Successfully fetched {len(props)} prop lines")
                
                # After fetching props, run the player mapper to map player names to IDs
                logger.info("Running player mapper to process raw prop lines")
                map_players_to_ids()
            except Exception as e:
                logger.error(f"Error in scheduled prop lines fetch: {str(e)}")
        else:
            logger.info("Not a game day, skipping prop lines fetch")
    else:
        logger.debug("Outside of scheduled fetch window (3 PM - 6 PM EST)")

def feature_engineering_job():
    """
    Job to generate features from player data.
    Runs once a day, before data processing.
    """
    now_est = datetime.now(EST_TIMEZONE)
    
    # Run at 12:30 AM EST every day
    if now_est.hour == 0 and 30 <= now_est.minute < 45:
        logger.info(f"Running scheduled feature engineering at {now_est}")
        try:
            run_feature_engineering()
            logger.info("Feature engineering completed successfully")
        except Exception as e:
            logger.error(f"Error in scheduled feature engineering: {str(e)}")

def process_data_job():
    """
    Job to process data and prepare it for the ML model.
    Runs once a day, typically after new game data has been added.
    """
    now_est = datetime.now(EST_TIMEZONE)
    
    # Run at 1 AM EST every day
    if now_est.hour == 1 and 0 <= now_est.minute < 15:
        logger.info(f"Running scheduled data processing at {now_est}")
        try:
            run_data_processing()
            logger.info("Data processing completed successfully")
        except Exception as e:
            logger.error(f"Error in scheduled data processing: {str(e)}")

def generate_predictions_job():
    """
    Job to generate predictions for today's games.
    Runs after prop lines have been fetched, typically in the early evening.
    """
    now_est = datetime.now(EST_TIMEZONE)
    
    # Run at 6:30 PM EST every game day
    if now_est.hour == 18 and 30 <= now_est.minute < 45:
        if is_game_day():
            logger.info(f"Running scheduled predictions generation at {now_est}")
            try:
                predictions = run_daily_predictions()
                logger.info(f"Successfully generated {len(predictions)} predictions")
            except Exception as e:
                logger.error(f"Error in scheduled predictions generation: {str(e)}")
        else:
            logger.info("Not a game day, skipping predictions generation")

def setup_scheduler():
    """
    Set up the scheduler to run all scheduled jobs.
    """
    logger.info("Setting up scheduler")
    
    # Schedule prop lines fetcher (every hour between 3 PM and 6 PM EST on game days)
    schedule.every().hour.do(fetch_prop_lines_job)
    
    # Schedule feature engineering (runs daily at 12:30 AM EST)
    schedule.every().hour.do(feature_engineering_job)
    
    # Schedule data processing (runs daily at 1 AM EST)
    schedule.every().hour.do(process_data_job)
    
    # Schedule predictions generation (runs daily at 6:30 PM EST on game days)
    schedule.every().hour.do(generate_predictions_job)
    
    # Also run immediately when started (for testing)
    fetch_prop_lines_job()
    
    logger.info("Scheduler set up successfully")

def run_scheduler():
    """
    Run the scheduler continuously.
    """
    setup_scheduler()
    
    logger.info("Starting scheduler loop")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check for pending jobs every minute

if __name__ == "__main__":
    run_scheduler() 
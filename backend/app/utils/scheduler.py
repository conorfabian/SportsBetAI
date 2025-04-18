import os
import logging
import schedule
import time
from datetime import datetime, timedelta
import pytz
from odds_fetcher import fetch_live_prop_lines
from player_mapper import map_players_to_ids

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

def setup_scheduler():
    """
    Set up the scheduler to run the prop lines fetcher every hour between 3 PM and 6 PM EST.
    """
    logger.info("Setting up prop lines fetcher scheduler")
    
    # Schedule the job to run every hour
    schedule.every().hour.do(fetch_prop_lines_job)
    
    # Also run immediately when started
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
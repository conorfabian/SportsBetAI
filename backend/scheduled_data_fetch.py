#!/usr/bin/env python
"""
Scheduled data fetcher script to be run by cron or another scheduler.
This fetches new NBA game data on a regular basis.
"""
import os
import sys
import logging
import argparse
from datetime import datetime, timedelta
from app.utils.historical_data_fetcher import fetch_and_store_historical_data

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, f'data_fetch_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Scheduled NBA data fetcher')
    parser.add_argument('--full-season', action='store_true', help='Fetch data for the full current season')
    parser.add_argument('--recent-days', type=int, default=3, help='Fetch data for the recent N days only')
    parser.add_argument('--dry-run', action='store_true', help='Do not save to database, just show what would be fetched')
    
    args = parser.parse_args()
    
    logger.info("Starting scheduled data fetch")
    
    # Determine seasons to fetch
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Adjust for NBA season (which runs from October to June)
    if current_month >= 10:  # October-December
        current_season = f"{current_year}-{str(current_year+1)[2:]}"
    else:  # January-September
        current_season = f"{current_year-1}-{str(current_year)[2:]}"
    
    if args.full_season:
        seasons = [current_season]
        logger.info(f"Fetching full current season: {current_season}")
    else:
        # Fetch only recent days (incremental update)
        seasons = None  # Let the fetcher determine the seasons
        logger.info(f"Fetching data for the last {args.recent_days} days")
    
    if args.dry_run:
        logger.info("DRY RUN: Would fetch data but not save to database")
        logger.info(f"Would fetch seasons: {seasons or 'current'}")
    else:
        # Actually fetch the data
        result = fetch_and_store_historical_data(seasons=seasons)
        
        # Log the result
        logger.info(f"Data fetch completed: {result}")
    
    logger.info("Scheduled data fetch complete")

if __name__ == '__main__':
    main() 
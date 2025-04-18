#!/usr/bin/env python
"""
Command-line script to fetch and store historical NBA player data.
"""
import argparse
import logging
from app.utils.historical_data_fetcher import fetch_and_store_historical_data

def setup_logging(verbose=False):
    """Configure logging for the script"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Fetch and store historical NBA player data')
    parser.add_argument('--seasons', nargs='+', help='Seasons to fetch (format: YYYY-YY)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Run the data fetching process
    result = fetch_and_store_historical_data(seasons=args.seasons)
    
    # Print summary
    print("\n--- SUMMARY ---")
    if result['status'] == 'success':
        print(f"Total players processed: {result['total_players']}")
        print(f"Players with data saved: {result['successful_players']}")
        print(f"Total game logs saved: {result['total_games_saved']}")
        print(f"Seasons processed: {', '.join(result['seasons'])}")
    else:
        print(f"Error: {result['message']}")

if __name__ == '__main__':
    main() 
# NBA Prop Betting Predictor Backend

This is the backend service for the NBA Prop Betting Predictor application. It fetches historical NBA player data, stores it in a database, and provides APIs for the frontend to access predictions.

## Setup

1. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Set up environment variables in `.env` file (copy from `.env.example`):
```bash
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://postgres:postgres@localhost/nba_props
ODDS_API_KEY=your_odds_api_key_here
FLASK_APP=app.py
FLASK_ENV=development
```

3. Create and initialize the database:
```bash
# Create the PostgreSQL database (if not using Docker)
createdb nba_props

# Initialize the database schema
python init_db.py
```

## Data Fetcher

The application includes several scripts for fetching NBA player data:

### 1. Historical Data Fetcher

This fetches game data for all active NBA players for multiple seasons.

```bash
# Fetch data for the default 3 seasons
python fetch_historical_data.py

# Fetch data for specific seasons
python fetch_historical_data.py --seasons 2022-23 2023-24

# Enable verbose logging
python fetch_historical_data.py --verbose
```

### 2. Test Single Player Fetch

This script is useful for testing data fetching for a single player:

```bash
# Fetch LeBron James' game logs for the current season
python test_player_gamelog.py "LeBron James"

# Fetch for a specific season
python test_player_gamelog.py "Stephen Curry" --season 2022-23

# Save the game log to a CSV file
python test_player_gamelog.py "Nikola Jokic" --save
```

### 3. Scheduled Data Fetcher

This script is designed to be run as a scheduled task (e.g., with cron) to keep the database updated:

```bash
# Update data for recent games (default: last 3 days)
python scheduled_data_fetch.py

# Fetch the entire current season's data
python scheduled_data_fetch.py --full-season

# Dry run (don't save to database)
python scheduled_data_fetch.py --dry-run
```

Example crontab entry to run daily at 2 AM:
```
0 2 * * * cd /path/to/sportsbetai/backend && /path/to/python scheduled_data_fetch.py >> /path/to/sportsbetai/backend/logs/cron.log 2>&1
```

## API Endpoints

### Player Stats

- GET `/api/players` - List all players
- GET `/api/players/search?q=<query>` - Search for players by name
- GET `/api/players/<id>/stats` - Get game stats for a player
- GET `/api/players/<id>/average` - Get average stats for a player's last N games

### Props

- GET `/api/props` - Get all prop bets for today
- GET `/api/props/player?name=<name>` - Get prop info for a specific player

## Running the Application

```bash
# Run in development mode
python app.py

# Or using Flask CLI
flask run
```

## Running Tests

```bash
# Run unit tests
python -m unittest discover tests

# Run a specific test
python -m tests.test_historical_data_fetcher

# Test database integration
python test_db_integration.py
``` 
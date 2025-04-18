# Project Overview
The goal of this project is to build a full‑stack web application that predicts the probability a given NBA player prop (specifically, points scored) will hit on FanDuel. Historical player performance and box‑score data will be ingested via the nba_api Python package, while live prop lines will be fetched through the Odds API. A machine learning model—trained on that historical data—will compute, for each player prop that day, the likelihood of surpassing the FanDuel line. Users will see a ranked list of today's props from most to least likely, and can also look up any individual player via a search bar. The front end will be developed in Next.js, the backend prediction service in Flask, and eventually the app will be containerized and deployed to scale for many simultaneous users and additional sports/prop types.

# Core Functionalities
1. Data Ingestion & Storage
1.1 Historical Data Fetcher

Source: nba_api Python client
Scope: Pull game logs for every active NBA player over the past 3 seasons
Fields collected: player_id, game_date, team, opponent, home_away, minutes_played, points, rebounds, assists, plus advanced metrics (pace, usage rate)
Frequency: One-time seed, then nightly cron job at 2 AM PST to backfill new games

1.2 Live Prop Lines Fetcher

Source: Odds API (FanDuel market)
Endpoint: GET /v1/odds?sport=basketball_nba&region=us&market=player_points
Fields collected: player_name, player_id (mapped via lookup table), prop_line (e.g. 24.5 points), timestamp
Frequency: Every hour between 3 PM and 6 PM EST on game days; failsafe retry on HTTP 5xx

1.3 Database Schema (PostgreSQL)

players (id SERIAL, nba_api_id INT, full_name TEXT)
games (id SERIAL, game_date DATE, home_team TEXT, away_team TEXT)
player_stats (id SERIAL, player_id INT → players.id, game_id INT → games.id, points INT, …)
prop_lines (id SERIAL, player_id INT, game_date DATE, line FLOAT, fetched_at TIMESTAMP)
predictions (id SERIAL, prop_line_id INT → prop_lines.id, prob_over FLOAT, generated_at TIMESTAMP)

2. Data Preprocessing
2.1. Cleaning & Validation

Deduplicate records, enforce correct data types, and handle missing values (e.g. impute opponent defensive rating to league average; drop or zero-fill missed games).

2.2. Data Join & Label Creation

Merge player_stats with prop_lines on (player_id, game_date).
Create binary target:

pythondf["hit"] = (df.points >= df.line).astype(int)
2.3. Feature Engineering

Rolling aggregates: last 5 games' mean & SD of points per player.
Contextual features: opponent defensive rating, home_vs_away flag, days_of_rest.

2.4. Encoding & Scaling

One-hot or target encode categorical (home_vs_away); clip outliers (e.g. rest days > 10).
Optional standardization for numeric features if experimenting beyond tree-based models.

2.5. Reproducible Pipeline

Wrap steps in an sklearn.pipeline.Pipeline or similar to guarantee identical transforms at training and inference.

2. Machine Learning Pipeline
2.1 Feature Engineering Script

Compute rolling aggregates for each player:

Last 5-game average points, standard deviation
Opponent's season defensive rating
Home vs. away indicator, days of rest


Output feature table: one row per player_id + game_date + features

2.2 Model Training & Persistence

Algorithm Selection:
- Primary model: XGBoost classifier for optimal predictive power with tabular data
- Baseline models for comparison:
  - Logistic Regression (for interpretability)
  - Random Forest (ensemble method with different characteristics)
  - LightGBM (gradient boosting alternative)

Hyperparameter Tuning:
- For best model (typically XGBoost), run grid search with 5-fold CV to optimize:
  - learning_rate: [0.01, 0.05, 0.1]
  - max_depth: [3, 5, 7]
  - n_estimators: [100, 200, 300]
  - subsample: [0.8, 0.9, 1.0]
  - min_child_weight: [1, 3, 5]

Model Evaluation Metrics:
- Primary: ROC-AUC (ranking ability)
- Secondary: Brier score (calibration quality)
- Additional: Log loss, PR-AUC, classification report at 0.5 threshold

Calibration:
- Apply Platt scaling (logistic regression on raw predictions) to ensure probabilistic outputs match observed frequencies
- Calibration curves to visually inspect reliability

Model Persistence:
- Save each model version with timestamp: `/models/YYYYMMDD_HHMMSS/`
- Artifacts stored:
  - model.joblib: Serialized trained model
  - feature_columns.json: List of expected feature names/order
  - metrics.json: Performance metrics, hyperparameters
  - calibration.joblib: Calibration model (if applied)
- Create symlink `/models/latest/` pointing to most recent version
- Version tracking in database for reproducibility

Model Monitoring:
- Log predictions to database with confidence intervals
- Track actual outcomes vs. predictions for drift detection
- Automated retraining when performance degrades beyond threshold

2.3 Inference Service

- [x] Load the latest model at Flask startup
  - Implemented singleton inference service that loads model at application startup
  - Handles model loading failures gracefully with proper error logging
- [x] Process features for prediction
  - Uses DataProcessor to prepare features for real-time prediction
  - Supports filtering by specific player or game date
- [x] Generate probability predictions for prop lines
  - Computes probability of player going over the point line
  - Includes confidence intervals based on model calibration metrics
  - Stores predictions in database with timestamps
- [x] API endpoints for accessing predictions
  - GET /api/props/ - Returns all predictions for a given date
  - GET /api/props/player - Returns predictions for a specific player
  - POST /api/props/generate - Manually trigger new predictions

3. Backend API (Flask)
3.1 Endpoint: List Today's Props

- [x] Route: GET /api/props?date=YYYY-MM-DD
  - Implemented endpoint that returns all prop predictions for a given date (defaults to today)
  - Response includes player details, prop line, and probability prediction
  - Results are sorted by probability (highest first)
  - Automatically triggers prediction generation if none exist for the requested date
- [x] Response: JSON array of objects { player_id, full_name, line, prob_over }, sorted by prob_over DESC
  - Format includes additional useful information:
    - confidence_interval: margin of error based on model calibration
    - home_team/away_team: game matchup information
    - game_time: scheduled time of the game
    - last_updated: when the prediction was generated

3.2 Endpoint: Player Lookup

- [x] Route: GET /api/props/player?name=Name&date=YYYY-MM-DD
  - Implemented endpoint that searches for a player by name (case-insensitive fuzzy match)
  - Accepts optional date parameter (defaults to today)
  - Returns detailed information about the player's prop and prediction
- [x] Behavior: Case-insensitive fuzzy match on players.full_name; return that single prop prediction
  - Includes comprehensive player information including:
    - Player details (ID, name, team)
    - Game information (matchup, date, time)
    - Prop line details (value, sportsbook, fetch time)
    - Recent performance (last 5 games)
    - Season averages (points, minutes, games played)
    - Prediction data (probability, confidence interval)
- [x] Additional features:
  - Automatically generates a prediction if one doesn't exist
  - Returns appropriate 404 errors when player or prop not found
  - Provides detailed error messages for easy debugging

3.3 Error Handling

- [x] 404 if no data for date or player
  - Implemented custom error classes for common error scenarios
  - Returns clear, descriptive error messages with appropriate status codes:
    - PlayerNotFoundError: When a requested player doesn't exist
    - PropNotFoundError: When no prop exists for a player/date
- [x] 500 on model loading failures with descriptive error message
  - ModelNotLoadedError provides detailed feedback when prediction model fails to load
  - DatabaseError with context about the failed operation
  - Comprehensive logging for all errors to assist debugging
- [x] Additional error handling features:
  - InvalidDateFormatError for date parsing issues
  - Consistent error response format across all endpoints
  - Exception tracking with full stack traces in logs
  - Automatic categorization of database-related errors

3.4 CORS & Rate Limiting

- [x] Allow requests from the Next.js frontend domain
  - Implemented flexible CORS with configurable origins
  - Support for multiple origins via comma-separated list in CORS_ORIGINS env var
  - Defaults to allowing all origins ('*') for development
  - Configurable methods, headers, and caching settings
- [x] Simple rate limit: 100 requests per IP per hour (e.g. via Flask-Limiter)
  - Created custom rate limiter with Redis support for production
  - In-memory fallback for development environment
  - Endpoint-specific rate limits:
    - Main props list: 100 requests/hour
    - Player lookup: 150 requests/hour
    - Manual prediction generation: 20 requests/hour
    - Player search: 150 requests/hour
  - Standard rate limit headers (X-RateLimit-*) for client feedback
  - Configurable limits via environment variables

4. Frontend UI (Next.js)
4.1 Homepage (/)

- [x] Data Fetch: Use SWR to call /api/props?date=today
  - Implemented data fetching with proper loading and error states
  - Added date selection functionality to view props for different dates
  - Implemented automatic refresh to keep data current
- [x] List View:
  - Created responsive table showing player information, prop lines, and probability
  - Table rows include player name, prop line, probability displayed as a percentage badge
  - Default sort by highest probability first for quick identification of best bets
  - Color-coded probability badges for visual identification of confidence
- [x] Loading/Error States:
  - Added loading spinner while data is being fetched
  - Implemented friendly error messages with retry functionality
  - Empty state handling when no props are available for selected date
- [x] Additional features:
  - Responsive design that works on mobile, tablet, and desktop
  - Player search component that allows quick lookups
  - Individual player details page with comprehensive statistics and predictions
  - Dynamic route updates to support sharing and bookmarking specific views

4.2 Search Component

Typeahead: As user types, query /api/props/player?name=<query>&date=today
Display: If match found, show that player's card with line and probability; otherwise "No matching player found"

4.3 Styling & UX

Responsive, mobile-first CSS with Tailwind
Probability badges colored:

≥ 70% → green outline
50-70% → yellow outline
< 50% → red outline


Hover tooltip on each badge: show "Model confidence interval: ±X%" (pulled from model's calibration stats)

# Doc
## Documentation for fetching complete gamelod data for an nba player
CODE EXAMPLE:
```
from nba_api.stats.endpoints import playergamelog
import pandas as pd

# Nikola Jokić's player ID
JOKIC_ID = 203999

def get_jokic_gamelog():
    # Fetch Jokić's game log for the 2024-25 season
    # Note: The season format is YYYY-YY (e.g., 2024-25)
    gamelog = playergamelog.PlayerGameLog(
        player_id=JOKIC_ID,
        season='2024-25',  # 2024-25 season
        season_type_all_star='Regular Season'
    )
    
    # Convert to DataFrame
    df = gamelog.get_data_frames()[0]
    
    # Display basic stats
    print(f"Total games played: {len(df)}")
    print("\nLast 5 games:")
    
    # Select important columns for display
    display_cols = ['GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG_PCT', 'FG3_PCT', 'FT_PCT']
    
    # Show last 5 games (most recent first)
    print(df[display_cols].head(5).to_string(index=False))
    
    # Save to CSV
    df.to_csv('jokic_2024_25_gamelog.csv', index=False)
    print("\nComplete game log saved to 'jokic_2024_25_gamelog.csv'")
    
    return df

if __name__ == "__main__":
    try:
        jokic_games = get_jokic_gamelog()
    except Exception as e:
        # If season hasn't started yet or there's another error
        print(f"Error fetching data: {e}")
        print("Note: If you're getting a 400 error, the 2024-25 season data may not be available yet.") 
```

## Documentation for fetching live odds for nba player props for points scored in a game
CODE EXAMPLE:
```
const axios = require('axios');

const API_KEY = 'd5fc1dff6519aedb48fee57ec75af13d';
const SPORT = 'basketball_nba';
const MARKET = 'player_points';
const REGIONS = 'us';
const ODDS_FORMAT = 'american';

/**
 * Fetches NBA player props for points from The Odds API
 */
async function fetchNBAPlayerPointsProps() {
  try {
    console.log('Fetching NBA player points props...');
    
    const url = `https://api.the-odds-api.com/v4/sports/${SPORT}/odds`;
    const response = await axios.get(url, {
      params: {
        apiKey: API_KEY,
        regions: REGIONS,
        markets: MARKET,
        oddsFormat: ODDS_FORMAT
      }
    });

    const games = response.data;
    console.log(`Found ${games.length} NBA games with player points props`);
    
    // Process and display the data
    games.forEach(game => {
      console.log(`\n${game.away_team} @ ${game.home_team} - ${new Date(game.commence_time).toLocaleString()}`);
      
      game.bookmakers.forEach(bookmaker => {
        console.log(`\n  Bookmaker: ${bookmaker.title}`);
        
        const playerPointsMarket = bookmaker.markets.find(market => market.key === MARKET);
        if (playerPointsMarket) {
          console.log(`  Last Updated: ${new Date(playerPointsMarket.last_update).toLocaleString()}`);
          
          playerPointsMarket.outcomes.forEach(outcome => {
            const price = outcome.price > 0 ? `+${outcome.price}` : outcome.price;
            console.log(`    ${outcome.name}: Over/Under ${outcome.point} (${price})`);
          });
        } else {
          console.log('  No player points props available');
        }
      });
    });

    return games;
  } catch (error) {
    console.error('Error fetching NBA player points props:', error.message);
    if (error.response) {
      console.error('API Response:', error.response.data);
      console.error('Status:', error.response.status);
    }
    throw error;
  }
}

// Execute the function
fetchNBAPlayerPointsProps()
  .then(() => console.log('Done!'))
  .catch(err => console.error('Failed to fetch data:', err)); 
```

# Current File Structure
```
/
├── frontend/                  # Next.js frontend application
│   ├── app/                   # Next.js app directory
│   │   ├── api/               # Next.js API routes
│   │   │   └── props/         # API routes for props
│   │   │       └── route.ts   # API route for props
│   │   ├── page.tsx           # Homepage
│   │   ├── layout.tsx         # Root layout
│   │   └── globals.css        # Global CSS
│   ├── public/                # Static assets
│   ├── Dockerfile             # Frontend Docker configuration
│   └── package.json           # Frontend dependencies
├── backend/                   # Flask backend application
│   ├── app/                   # Main application directory
│   │   ├── models/            # Database models
│   │   │   └── base.py        # Base database models
│   │   ├── routes/            # API routes
│   │   │   └── props.py       # Routes for props
│   │   ├── utils/             # Utility scripts
│   │   │   ├── data_fetcher.py # Script for fetching NBA data
│   │   │   └── db_init.py     # Database initialization script
│   │   └── __init__.py        # Flask app initialization
│   ├── app.py                 # Flask application entry point
│   ├── Dockerfile             # Backend Docker configuration
│   ├── requirements.txt       # Python dependencies
│   └── .env.example           # Example environment variables
├── docker-compose.yml         # Docker Compose configuration
└── README.md                  # Project documentation
``` 
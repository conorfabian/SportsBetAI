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

Algorithm: XGBoost binary classifier (over vs. under)
Training set: All historical games where we know the actual over/under outcome relative to FanDuel's line
Validation: 5-fold cross-validation, track AUC and calibration
Artifacts: Save model weights and feature_columns.json to disk (/models/latest/)

2.3 Inference Service

Load the latest model at Flask startup
Given today's features, output prob_over for each prop

3. Backend API (Flask)
3.1 Endpoint: List Today's Props

Route: GET /api/props?date=YYYY-MM-DD
Response: JSON array of objects { player_id, full_name, line, prob_over }, sorted by prob_over DESC

3.2 Endpoint: Player Lookup

Route: GET /api/props/player?name=LeBron James&date=YYYY-MM-DD
Behavior: Case-insensitive fuzzy match on players.full_name; return that single prop prediction

3.3 Error Handling

404 if no data for date or player
500 on model loading failures with descriptive error message

3.4 CORS & Rate Limiting

Allow requests from the Next.js frontend domain
Simple rate limit: 100 requests per IP per hour (e.g. via Flask-Limiter)

4. Frontend UI (Next.js)
4.1 Homepage (/)

Data Fetch: Use SWR to call /api/props?date=today
List View:

Table rows: Player photo thumbnail, name, FanDuel line, prob_over displayed as a percentage badge
Default sort: highest probability first


Loading/Error States: Spinner while loading; friendly error message if API fails

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
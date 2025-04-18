import pandas as pd
import numpy as np
import logging
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from app import db, create_app
from app.models.base import Player, Game, PlayerStats, PropLine

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """
    Feature Engineering Pipeline specifically for NBA player prop predictions.
    
    This class computes:
    1. Rolling averages for points scored (last 5, 10, 20 games)
    2. Performance variance metrics (standard deviation of points) 
    3. Opponent defensive metrics
    4. Rest days and game context features
    """
    
    def __init__(self, output_dir='backend/data/features'):
        """
        Initialize the Feature Engineer.
        
        Args:
            output_dir (str): Directory to store feature files
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Configure feature specifications
        self.rolling_windows = [5, 10, 20]  # Last 5, 10, and 20 games
        
        # Define feature groups
        self.rolling_features = []
        for window in self.rolling_windows:
            self.rolling_features.extend([
                f'avg_points_last_{window}',
                f'std_points_last_{window}',
                f'avg_minutes_last_{window}',
                f'avg_fga_last_{window}',
                f'avg_fg_pct_last_{window}',
                f'avg_3pa_last_{window}',
                f'avg_3p_pct_last_{window}',
                f'avg_fta_last_{window}',
                f'avg_ft_pct_last_{window}'
            ])
        
        self.context_features = [
            'days_rest',
            'home_away',
            'opp_pts_allowed_avg',
            'opp_pace',
            'team_pace'
        ]
        
        self.season_features = [
            'season_avg_points',
            'season_avg_minutes',
            'season_avg_fga'
        ]
        
        # All features combined
        self.features = self.rolling_features + self.context_features + self.season_features
    
    def extract_minutes_as_float(self, minutes_str):
        """
        Convert minutes string format (MM:SS) to float.
        
        Args:
            minutes_str (str): Minutes in format "MM:SS"
            
        Returns:
            float: Minutes as a float
        """
        try:
            if pd.isna(minutes_str) or minutes_str == '':
                return 0.0
                
            if ':' in minutes_str:
                mins, secs = minutes_str.split(':')
                return float(mins) + float(secs) / 60
            else:
                return float(minutes_str)
        except:
            return 0.0
    
    def get_player_data(self):
        """
        Retrieve player data from the database.
        
        Returns:
            DataFrame: Player game stats
        """
        app = create_app()
        with app.app_context():
            # Get all player stats with game info
            logger.info("Retrieving player stats from database")
            
            query = """
            SELECT 
                ps.id, ps.player_id, p.full_name, ps.game_id, g.game_date, 
                g.home_team, g.away_team, ps.points, ps.rebounds, ps.assists,
                ps.steals, ps.blocks, ps.turnovers, ps.minutes, 
                ps.field_goals_made, ps.field_goals_attempted, ps.field_goal_pct,
                ps.three_pointers_made, ps.three_pointers_attempted, ps.three_point_pct,
                ps.free_throws_made, ps.free_throws_attempted, ps.free_throw_pct,
                ps.home_away, ps.win_loss, ps.plus_minus
            FROM player_stats ps
            JOIN players p ON ps.player_id = p.id
            JOIN games g ON ps.game_id = g.id
            ORDER BY p.id, g.game_date
            """
            
            df = pd.read_sql_query(query, db.engine)
            
            if df.empty:
                logger.warning("No player data found in database")
                return pd.DataFrame()
            
            logger.info(f"Retrieved {len(df)} player game records")
            return df
    
    def compute_features(self, player_data):
        """
        Compute all features from player game data.
        
        Args:
            player_data (DataFrame): Player game stats
            
        Returns:
            DataFrame: Computed features
        """
        logger.info("Computing features")
        
        # Convert minutes to float
        player_data['minutes_float'] = player_data['minutes'].apply(self.extract_minutes_as_float)
        
        # Sort by player and date
        player_data = player_data.sort_values(['player_id', 'game_date'])
        
        # Create a list to store processed data
        processed_data = []
        
        # Get unique player IDs
        player_ids = player_data['player_id'].unique()
        logger.info(f"Processing {len(player_ids)} players")
        
        # Process each player
        for player_id in player_ids:
            player_games = player_data[player_data['player_id'] == player_id].copy()
            
            # Only process players with at least 10 games to get meaningful stats
            if len(player_games) < 10:
                continue
            
            player_name = player_games['full_name'].iloc[0]
            logger.info(f"Processing player {player_name} with {len(player_games)} games")
            
            # Calculate days between games (for rest days)
            player_games['prev_game_date'] = player_games['game_date'].shift(1)
            player_games['days_rest'] = (player_games['game_date'] - player_games['prev_game_date']).dt.days
            
            # Fill NaN values for first game
            player_games['days_rest'] = player_games['days_rest'].fillna(3)
            
            # Cap rest days at 10 (outlier handling)
            player_games['days_rest'] = player_games['days_rest'].clip(upper=10)
            
            # Calculate rolling averages for key stats
            for window in self.rolling_windows:
                # Points
                player_games[f'avg_points_last_{window}'] = player_games['points'].rolling(window=window, min_periods=1).mean()
                player_games[f'std_points_last_{window}'] = player_games['points'].rolling(window=window, min_periods=3).std()
                
                # Minutes
                player_games[f'avg_minutes_last_{window}'] = player_games['minutes_float'].rolling(window=window, min_periods=1).mean()
                
                # Shooting volume and efficiency
                player_games[f'avg_fga_last_{window}'] = player_games['field_goals_attempted'].rolling(window=window, min_periods=1).mean()
                player_games[f'avg_fg_pct_last_{window}'] = player_games['field_goal_pct'].rolling(window=window, min_periods=1).mean()
                
                player_games[f'avg_3pa_last_{window}'] = player_games['three_pointers_attempted'].rolling(window=window, min_periods=1).mean()
                player_games[f'avg_3p_pct_last_{window}'] = player_games['three_point_pct'].rolling(window=window, min_periods=1).mean()
                
                player_games[f'avg_fta_last_{window}'] = player_games['free_throws_attempted'].rolling(window=window, min_periods=1).mean()
                player_games[f'avg_ft_pct_last_{window}'] = player_games['free_throw_pct'].rolling(window=window, min_periods=1).mean()
            
            # Calculate season averages (expanding window)
            player_games['season_avg_points'] = player_games['points'].expanding().mean()
            player_games['season_avg_minutes'] = player_games['minutes_float'].expanding().mean()
            player_games['season_avg_fga'] = player_games['field_goals_attempted'].expanding().mean()
            
            # Process opponent data - calculate average points allowed by opponent
            home_away_map = {'HOME': 'away_team', 'AWAY': 'home_team'}
            
            for idx, game in player_games.iterrows():
                opponent_col = home_away_map[game['home_away']]
                opponent = game[opponent_col]
                
                # Calculate opponent's defensive stats from previous games
                opponent_games = player_data[
                    ((player_data['home_team'] == opponent) | (player_data['away_team'] == opponent)) &
                    (player_data['game_date'] < game['game_date'])
                ]
                
                opp_pts_allowed = opponent_games['points'].mean()
                
                # If we don't have enough data, use a reasonable default
                if pd.isna(opp_pts_allowed):
                    opp_pts_allowed = 110  # League average
                
                player_games.at[idx, 'opp_pts_allowed_avg'] = opp_pts_allowed
                
                # Add pace factors (simplified implementation)
                player_games.at[idx, 'opp_pace'] = 100.0
                player_games.at[idx, 'team_pace'] = 100.0
            
            # Fill NaN values with appropriate defaults
            player_games = player_games.fillna({
                'opp_pts_allowed_avg': 110,
                'opp_pace': 100,
                'team_pace': 100
            })
            
            # Add to processed data
            processed_data.append(player_games)
        
        # Combine all processed data
        if not processed_data:
            logger.warning("No data after processing")
            return pd.DataFrame()
            
        features_df = pd.concat(processed_data)
        logger.info(f"Generated features for {len(features_df)} player games")
        
        return features_df
    
    def save_features(self, features_df, date_str=None):
        """
        Save computed features to disk.
        
        Args:
            features_df (DataFrame): Computed features
            date_str (str): Date string for the filename (default: today's date)
            
        Returns:
            str: Path to the saved file
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
            
        # Create a features directory with date
        date_dir = os.path.join(self.output_dir, date_str)
        os.makedirs(date_dir, exist_ok=True)
        
        # Save full features dataset
        features_path = os.path.join(date_dir, 'player_features.csv')
        features_df.to_csv(features_path, index=False)
        
        # Save feature definitions
        feature_metadata = {
            'rolling_features': self.rolling_features,
            'context_features': self.context_features,
            'season_features': self.season_features,
            'all_features': self.features,
            'generated_at': datetime.now().isoformat(),
            'num_players': len(features_df['player_id'].unique()),
            'num_games': len(features_df)
        }
        
        with open(os.path.join(date_dir, 'feature_metadata.json'), 'w') as f:
            json.dump(feature_metadata, f, indent=2)
        
        logger.info(f"Saved features to {features_path}")
        
        # Also save the latest features to a fixed location for ease of access
        latest_dir = os.path.join(self.output_dir, 'latest')
        os.makedirs(latest_dir, exist_ok=True)
        
        latest_path = os.path.join(latest_dir, 'player_features.csv')
        features_df.to_csv(latest_path, index=False)
        
        with open(os.path.join(latest_dir, 'feature_metadata.json'), 'w') as f:
            json.dump(feature_metadata, f, indent=2)
        
        logger.info(f"Updated latest features at {latest_path}")
        
        return features_path
    
    def load_features(self, date_str=None):
        """
        Load previously computed features from disk.
        
        Args:
            date_str (str): Date string for the filename (default: latest)
            
        Returns:
            DataFrame: Loaded features
        """
        if date_str is None:
            # Load from the latest directory
            features_path = os.path.join(self.output_dir, 'latest', 'player_features.csv')
        else:
            # Load from the specified date directory
            features_path = os.path.join(self.output_dir, date_str, 'player_features.csv')
        
        if not os.path.exists(features_path):
            logger.warning(f"Features file {features_path} not found")
            return pd.DataFrame()
        
        features_df = pd.read_csv(features_path)
        logger.info(f"Loaded features from {features_path}: {len(features_df)} rows")
        
        return features_df
    
    def run_feature_engineering(self):
        """
        Run the complete feature engineering pipeline.
        
        Returns:
            str: Path to the saved features file
        """
        logger.info("Starting feature engineering pipeline")
        
        # Get player data
        player_data = self.get_player_data()
        
        if player_data.empty:
            logger.error("No player data available")
            return None
        
        # Compute features
        features_df = self.compute_features(player_data)
        
        if features_df.empty:
            logger.error("Failed to compute features")
            return None
        
        # Save features
        features_path = self.save_features(features_df)
        
        logger.info("Feature engineering pipeline complete")
        
        return features_path


def main():
    """
    Main function to run the feature engineering pipeline.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Initializing feature engineering script")
    
    # Create Feature Engineer
    engineer = FeatureEngineer()
    
    # Run feature engineering
    features_path = engineer.run_feature_engineering()
    
    if features_path:
        logger.info(f"Features saved to {features_path}")
    else:
        logger.error("Feature engineering failed")


if __name__ == "__main__":
    main() 
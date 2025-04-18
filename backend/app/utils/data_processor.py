import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from sqlalchemy import create_engine, text
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
import joblib
import os
from app import db, create_app
from app.models.base import Player, Game, PlayerStats, PropLine, Prediction
from app.utils.feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Processes raw NBA game data and prop lines to create features for the ML model.
    
    This class handles all data preprocessing steps:
    1. Data cleaning and missing value handling
    2. Feature engineering (rolling stats, matchup info, etc.)
    3. Creating training labels from historical prop lines
    4. Preparing data for model training and inference
    """
    
    def __init__(self, db_connection_string=None, model_dir='backend/models', features_dir='backend/data/features'):
        """
        Initialize the data processor.
        
        Args:
            db_connection_string (str): Database connection string
            model_dir (str): Directory to store/load model artifacts
            features_dir (str): Directory where feature engineering outputs are stored
        """
        self.db_connection_string = db_connection_string
        self.model_dir = model_dir
        self.features_dir = features_dir
        self.pipeline = None
        self.feature_engineer = FeatureEngineer(output_dir=features_dir)
        
        # Create directories if they don't exist
        os.makedirs(os.path.join(model_dir, 'latest'), exist_ok=True)
        
        # Configure feature specifications
        self.rolling_windows = [5, 10, 20]  # Last 5, 10, and 20 games
        
        # Define column groups for the pipeline
        self.numeric_features = [
            'avg_points_last_5', 'avg_points_last_10', 'avg_points_last_20',
            'std_points_last_5', 'std_points_last_10', 'std_points_last_20',
            'avg_minutes_last_5', 'avg_minutes_last_10', 'avg_minutes_last_20',
            'avg_fga_last_5', 'avg_fga_last_10', 'avg_fga_last_20',
            'avg_fg_pct_last_5', 'avg_fg_pct_last_10', 'avg_fg_pct_last_20',
            'avg_3pa_last_5', 'avg_3pa_last_10', 'avg_3pa_last_20',
            'avg_3p_pct_last_5', 'avg_3p_pct_last_10', 'avg_3p_pct_last_20',
            'avg_fta_last_5', 'avg_fta_last_10', 'avg_fta_last_20',
            'avg_ft_pct_last_5', 'avg_ft_pct_last_10', 'avg_ft_pct_last_20',
            'days_rest', 'opp_pts_allowed_avg', 'opp_pace', 'team_pace',
            'season_avg_points', 'season_avg_minutes', 'season_avg_fga', 
            'point_line'
        ]
        
        self.categorical_features = [
            'home_away'
        ]
        
        # Special handling for player ID (will be treated separately)
        self.id_features = ['player_id']
    
    def create_preprocessing_pipeline(self):
        """
        Create a preprocessing pipeline for transforming features.
        
        Returns:
            Pipeline: Scikit-learn pipeline for preprocessing data
        """
        # Numeric features: impute missing values and scale
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])
        
        # Categorical features: impute missing values and one-hot encode
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='constant', fill_value='AWAY')),
            ('onehot', OneHotEncoder(drop='first', sparse_output=False))
        ])
        
        # Combine transformers into a column transformer
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, self.numeric_features),
                ('cat', categorical_transformer, self.categorical_features)
            ],
            remainder='passthrough'  # Pass player_id through unchanged
        )
        
        # Create the complete pipeline
        self.pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor)
        ])
        
        return self.pipeline
    
    def save_pipeline(self, filename='preprocessing_pipeline.joblib'):
        """
        Save the preprocessing pipeline to disk.
        
        Args:
            filename (str): Filename to save the pipeline
        """
        if self.pipeline is None:
            self.create_preprocessing_pipeline()
            
        filepath = os.path.join(self.model_dir, 'latest', filename)
        joblib.dump(self.pipeline, filepath)
        logger.info(f"Saved preprocessing pipeline to {filepath}")
        
        # Also save feature columns list for reference
        feature_columns = self.numeric_features + self.categorical_features + self.id_features
        with open(os.path.join(self.model_dir, 'latest', 'feature_columns.json'), 'w') as f:
            import json
            json.dump(feature_columns, f)
    
    def load_pipeline(self, filename='preprocessing_pipeline.joblib'):
        """
        Load the preprocessing pipeline from disk.
        
        Args:
            filename (str): Filename of the saved pipeline
            
        Returns:
            Pipeline: Loaded preprocessing pipeline
        """
        filepath = os.path.join(self.model_dir, 'latest', filename)
        self.pipeline = joblib.load(filepath)
        return self.pipeline
    
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
    
    def get_player_stats_for_training(self):
        """
        Query the database for player stats and prop lines for model training.
        
        Returns:
            DataFrame: Combined player stats and prop lines
        """
        app = create_app()
        with app.app_context():
            # Get all player stats with game info
            logger.info("Retrieving player stats and game info from database")
            
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
            
            stats_df = pd.read_sql_query(query, db.engine)
            
            # Get all prop lines
            logger.info("Retrieving prop lines from database")
            query = """
            SELECT 
                pl.id, pl.player_id, p.full_name, pl.game_date, pl.line,
                pl.fetched_at
            FROM prop_lines pl
            JOIN players p ON pl.player_id = p.id
            ORDER BY p.id, pl.game_date
            """
            
            props_df = pd.read_sql_query(query, db.engine)
            
            if stats_df.empty or props_df.empty:
                logger.warning("No data found in the database")
                return pd.DataFrame()
            
            logger.info(f"Retrieved {len(stats_df)} player stats records and {len(props_df)} prop lines")
            
            return stats_df, props_df
    
    def prepare_training_data(self):
        """
        Prepare the full training dataset with features and labels.
        
        Returns:
            tuple: (X, y) - features and target
        """
        # Try to load pre-computed features from feature engineering
        features_df = self.feature_engineer.load_features()
        
        if features_df.empty:
            logger.warning("No pre-computed features found, running feature engineering...")
            # Generate features if not available
            features_path = self.feature_engineer.run_feature_engineering()
            if features_path:
                features_df = self.feature_engineer.load_features()
            else:
                logger.error("Feature engineering failed")
                return None, None
        
        # Get prop lines for training
        _, props_df = self.get_player_stats_for_training()
        
        if props_df.empty:
            logger.error("No prop lines available for training")
            return None, None
        
        # Join feature data with prop lines
        logger.info("Joining feature data with prop lines")
        training_data = pd.merge(
            features_df,
            props_df[['player_id', 'game_date', 'line']],
            on=['player_id', 'game_date'],
            how='inner'
        )
        
        training_data = training_data.rename(columns={'line': 'point_line'})
        
        if training_data.empty:
            logger.error("No matching data between features and prop lines")
            return None, None
            
        # Create target variable (whether player went over the line)
        training_data['hit'] = (training_data['points'] >= training_data['point_line']).astype(int)
        
        # Select features and target
        feature_columns = self.numeric_features + self.categorical_features + self.id_features
        
        # Ensure all required columns are present
        missing_cols = [col for col in feature_columns if col not in training_data.columns]
        if missing_cols:
            logger.warning(f"Missing columns in training data: {missing_cols}")
            # Add missing columns with default values
            for col in missing_cols:
                if col in self.numeric_features:
                    training_data[col] = 0.0
                elif col in self.categorical_features:
                    training_data[col] = 'AWAY'
        
        X = training_data[feature_columns]
        y = training_data['hit']
        
        logger.info(f"Prepared training data with {len(X)} samples and {len(feature_columns)} features")
        
        return X, y
    
    def engineer_features(self, stats_df, props_df=None):
        """
        Engineer features for model training or prediction.
        This method is maintained for backward compatibility but now
        leverages the FeatureEngineer class for consistency.
        
        Args:
            stats_df (DataFrame): Player game stats
            props_df (DataFrame, optional): Prop lines (for training or prediction)
            
        Returns:
            DataFrame: Processed data with engineered features
        """
        logger.info("Engineering features from player stats")
        
        # Use the feature engineer to compute features from the stats data
        features_df = self.feature_engineer.compute_features(stats_df)
        
        if features_df.empty:
            logger.warning("Failed to compute features")
            return None
        
        # Join with prop lines data if provided
        if props_df is not None:
            logger.info("Joining with prop lines data")
            
            # Merge on player_id and game_date
            merged_df = pd.merge(
                features_df,
                props_df[['player_id', 'game_date', 'line']],
                on=['player_id', 'game_date'],
                how='inner'
            )
            
            # Rename prop line column to be more clear
            merged_df = merged_df.rename(columns={'line': 'point_line'})
            
            logger.info(f"Final dataset has {len(merged_df)} rows after joining with prop lines")
            return merged_df
        
        # For prediction, just return the processed features
        return features_df
    
    def prepare_prediction_features(self, player_id=None, game_date=None):
        """
        Prepare features for prediction for a specific player and game.
        
        Args:
            player_id (int): ID of the player to predict
            game_date (date): Date of the game to predict
            
        Returns:
            DataFrame: Features for prediction
        """
        # Try to load pre-computed features
        features_df = self.feature_engineer.load_features()
        
        if features_df.empty:
            logger.warning("No pre-computed features found, falling back to live feature computation")
            app = create_app()
            with app.app_context():
                # Get player stats
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
                """
                
                # Add filters if specific player
                if player_id is not None:
                    query += f" WHERE ps.player_id = {player_id}"
                    
                query += " ORDER BY p.id, g.game_date"
                
                stats_df = pd.read_sql_query(query, db.engine)
                
                # Compute features directly
                features_df = self.feature_engineer.compute_features(stats_df)
        
        # Get today's prop lines
        if game_date is None:
            game_date = datetime.now().date()
            
        app = create_app()
        with app.app_context():
            prop_query = f"""
            SELECT 
                pl.id, pl.player_id, p.full_name, pl.game_date, pl.line,
                pl.fetched_at
            FROM prop_lines pl
            JOIN players p ON pl.player_id = p.id
            WHERE pl.game_date = '{game_date}'
            """
            
            if player_id is not None:
                prop_query += f" AND pl.player_id = {player_id}"
                
            props_df = pd.read_sql_query(prop_query, db.engine)
        
        if features_df.empty or props_df.empty:
            logger.warning("No data found for prediction")
            return None
        
        # Filter features for the game date if needed
        if game_date:
            features_df = features_df[features_df['game_date'] == game_date]
            
        # Merge with prop lines
        prediction_data = pd.merge(
            features_df,
            props_df[['id', 'player_id', 'game_date', 'line']],
            on=['player_id', 'game_date'],
            how='inner'
        )
        
        prediction_data = prediction_data.rename(columns={'line': 'point_line', 'id': 'prop_id'})
        
        if prediction_data.empty:
            logger.warning("No matching data between features and prop lines for prediction")
            return None
            
        # Select features
        feature_columns = self.numeric_features + self.categorical_features + self.id_features
        
        # Ensure all required columns are present
        missing_cols = [col for col in feature_columns if col not in prediction_data.columns]
        if missing_cols:
            logger.warning(f"Missing columns in prediction data: {missing_cols}")
            # Add missing columns with default values
            for col in missing_cols:
                if col in self.numeric_features:
                    prediction_data[col] = 0.0
                elif col in self.categorical_features:
                    prediction_data[col] = 'AWAY'
        
        X_pred = prediction_data[feature_columns]
        X_pred['prop_id'] = prediction_data['prop_id']
        
        return X_pred
    
    def transform_features(self, X):
        """
        Apply the preprocessing pipeline to transform features.
        
        Args:
            X (DataFrame): Raw features
            
        Returns:
            DataFrame/array: Transformed features
        """
        if self.pipeline is None:
            try:
                self.load_pipeline()
            except:
                self.create_preprocessing_pipeline()
                self.save_pipeline()
        
        return self.pipeline.transform(X)


def run_data_processing():
    """
    Run the data processing pipeline to prepare training data.
    """
    logger.info("Starting data processing")
    
    # Initialize processor
    processor = DataProcessor()
    
    # Prepare training data
    X, y = processor.prepare_training_data()
    
    if X is None or y is None:
        logger.error("Failed to prepare training data")
        return
    
    logger.info(f"Successfully prepared training data with {X.shape[0]} samples and {X.shape[1]} features")
    
    # Create and save preprocessing pipeline
    processor.create_preprocessing_pipeline()
    processor.save_pipeline()
    
    # Save training data for model training
    X.to_csv(os.path.join(processor.model_dir, 'latest', 'X_train.csv'), index=False)
    y.to_csv(os.path.join(processor.model_dir, 'latest', 'y_train.csv'), index=False)
    
    logger.info("Data processing complete")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run data processing
    run_data_processing() 
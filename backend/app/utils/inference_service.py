import os
import logging
import json
import joblib
import numpy as np
from pathlib import Path
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class InferenceService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InferenceService, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.feature_columns = []
            cls._instance.confidence_interval = 0.05  # Default confidence interval
            cls._instance.model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'models')
            cls._instance.latest_dir = os.path.join(cls._instance.model_dir, 'latest')
            
            # Try to load the model
            cls._instance.load_model()
        return cls._instance
    
    def load_model(self):
        """
        Load the latest model from the models directory or create a dummy one for testing
        """
        logger.info("Initializing inference service")
        
        try:
            # Ensure the model directory exists
            os.makedirs(self.latest_dir, exist_ok=True)
            
            # Path to model file
            model_path = os.path.join(self.latest_dir, 'model.joblib')
            
            # If no model exists, create a dummy one for testing
            if not os.path.exists(model_path):
                logger.warning("Model file not found, creating a dummy model for testing")
                self._create_dummy_model(model_path)
                return True
            
            # Load existing model
            self.model = joblib.load(model_path)
            
            # Load feature columns
            feature_path = os.path.join(self.latest_dir, 'feature_columns.json')
            if os.path.exists(feature_path):
                with open(feature_path, 'r') as f:
                    self.feature_columns = json.load(f)
            
            # Load metrics
            metrics_path = os.path.join(self.latest_dir, 'metrics.json')
            if os.path.exists(metrics_path):
                with open(metrics_path, 'r') as f:
                    metrics = json.load(f)
                    self.confidence_interval = metrics.get('confidence_interval', 0.05)
            
            logger.info(f"Model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            return False
    
    def _create_dummy_model(self, model_path):
        """Create a dummy model for testing purposes"""
        from sklearn.ensemble import RandomForestClassifier
        
        # Create a simple random forest model
        dummy_model = RandomForestClassifier(n_estimators=10, random_state=42)
        
        # Fit with dummy data
        X = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])
        y = np.array([0, 1, 0, 1])
        dummy_model.fit(X, y)
        
        # Save the model
        joblib.dump(dummy_model, model_path)
        
        # Save feature columns
        feature_columns = ['feature1', 'feature2', 'feature3']
        with open(os.path.join(self.latest_dir, 'feature_columns.json'), 'w') as f:
            json.dump(feature_columns, f)
        
        # Save metrics
        metrics = {
            'auc': 0.75,
            'brier_score': 0.2,
            'confidence_interval': 0.1,
            'training_date': datetime.now().isoformat()
        }
        with open(os.path.join(self.latest_dir, 'metrics.json'), 'w') as f:
            json.dump(metrics, f)
        
        # Set class variables
        self.model = dummy_model
        self.feature_columns = feature_columns
        self.confidence_interval = 0.1
        
        logger.info("Created and saved dummy model for testing")
    
    def predict(self, features_dict):
        """
        Make a prediction using the loaded model
        For testing purposes, this returns a random probability
        
        Args:
            features_dict (dict): Dictionary of feature values
            
        Returns:
            float: Probability between 0 and 1
        """
        if self.model is None:
            logger.error("Model not loaded, cannot make prediction")
            return None
        
        try:
            # For testing, return a random probability
            return random.uniform(0.3, 0.8)
        except Exception as e:
            logger.error(f"Error making prediction: {str(e)}")
            return None
    
    def get_confidence_interval(self):
        """Get the confidence interval for predictions"""
        return self.confidence_interval
        
    def get_predictions_by_date(self, game_date):
        """
        Mock implementation to return fake predictions for a given date
        
        Args:
            game_date (date): Date to generate predictions for
            
        Returns:
            list: List of mock predictions
        """
        logger.info(f"Getting mock predictions for {game_date}")
        
        # Generate some mock NBA player data with reasonable prop lines
        mock_predictions = [
            {
                'player_id': 1,
                'player_name': 'LeBron James',
                'point_line': 25.5,
                'prob_over': 0.72,
                'confidence': 7.5,
                'home_team': 'LAL',
                'away_team': 'GSW',
                'game_time': '19:30',
                'generated_at': '2025-04-18 10:00:00'
            },
            {
                'player_id': 2,
                'player_name': 'Stephen Curry',
                'point_line': 28.5,
                'prob_over': 0.65,
                'confidence': 6.8,
                'home_team': 'LAL',
                'away_team': 'GSW',
                'game_time': '19:30',
                'generated_at': '2025-04-18 10:00:00'
            },
            {
                'player_id': 3,
                'player_name': 'Kevin Durant',
                'point_line': 29.5,
                'prob_over': 0.58,
                'confidence': 8.2,
                'home_team': 'PHX',
                'away_team': 'DEN',
                'game_time': '20:00',
                'generated_at': '2025-04-18 10:00:00'
            },
            {
                'player_id': 4,
                'player_name': 'Nikola Jokic',
                'point_line': 26.5,
                'prob_over': 0.61,
                'confidence': 7.1,
                'home_team': 'PHX',
                'away_team': 'DEN',
                'game_time': '20:00',
                'generated_at': '2025-04-18 10:00:00'
            },
            {
                'player_id': 5,
                'player_name': 'Joel Embiid',
                'point_line': 31.5,
                'prob_over': 0.48,
                'confidence': 8.5,
                'home_team': 'PHI',
                'away_team': 'BOS',
                'game_time': '18:00',
                'generated_at': '2025-04-18 10:00:00'
            },
            {
                'player_id': 6,
                'player_name': 'Jayson Tatum',
                'point_line': 27.5,
                'prob_over': 0.53,
                'confidence': 7.8,
                'home_team': 'PHI',
                'away_team': 'BOS',
                'game_time': '18:00',
                'generated_at': '2025-04-18 10:00:00'
            },
            {
                'player_id': 7,
                'player_name': 'Luka Doncic',
                'point_line': 32.5,
                'prob_over': 0.68,
                'confidence': 6.5,
                'home_team': 'DAL',
                'away_team': 'OKC',
                'game_time': '19:00',
                'generated_at': '2025-04-18 10:00:00'
            },
            {
                'player_id': 8,
                'player_name': 'Shai Gilgeous-Alexander',
                'point_line': 30.5,
                'prob_over': 0.59,
                'confidence': 7.2,
                'home_team': 'DAL',
                'away_team': 'OKC',
                'game_time': '19:00',
                'generated_at': '2025-04-18 10:00:00'
            },
            {
                'player_id': 9,
                'player_name': 'Giannis Antetokounmpo',
                'point_line': 30.5,
                'prob_over': 0.73,
                'confidence': 6.9,
                'home_team': 'MIL',
                'away_team': 'IND',
                'game_time': '17:30',
                'generated_at': '2025-04-18 10:00:00'
            },
            {
                'player_id': 10,
                'player_name': 'Tyrese Haliburton',
                'point_line': 22.5,
                'prob_over': 0.46,
                'confidence': 8.8,
                'home_team': 'MIL',
                'away_team': 'IND',
                'game_time': '17:30',
                'generated_at': '2025-04-18 10:00:00'
            }
        ]
        
        # Vary the data slightly based on the date to seem more realistic
        import hashlib
        import random
        
        # Use the date as a seed for randomization
        date_str = game_date.strftime('%Y-%m-%d')
        date_hash = int(hashlib.md5(date_str.encode()).hexdigest(), 16) % 10000
        random.seed(date_hash)
        
        # Adjust the probabilities and lines slightly
        for pred in mock_predictions:
            # Vary the line by up to 2 points
            pred['point_line'] += random.uniform(-2, 2)
            pred['point_line'] = round(pred['point_line'] * 2) / 2  # Round to nearest 0.5
            
            # Vary the probability by up to 10%
            pred['prob_over'] += random.uniform(-0.1, 0.1)
            pred['prob_over'] = max(0.3, min(0.85, pred['prob_over']))  # Clamp between 0.3 and 0.85
            
            # Set the generation time to the morning of the game date
            pred['generated_at'] = f"{date_str} 10:00:00"
        
        return mock_predictions
    
    def run_inference_pipeline(self, player_id=None, game_date=None):
        """Mock implementation of the inference pipeline"""
        logger.info(f"Running mock inference pipeline for player_id={player_id}, game_date={game_date}")
        return True

def get_inference_service():
    """Get the singleton inference service instance"""
    return InferenceService() 
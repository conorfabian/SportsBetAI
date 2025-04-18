import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from app import db, create_app
from app.models.base import Player, Game, PlayerStats, PropLine, Prediction
from app.utils.model_trainer import ModelTrainer
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class PredictionService:
    """
    Service for making predictions using the trained model.
    
    This class handles:
    1. Loading the trained model
    2. Preparing data for prediction
    3. Making predictions
    4. Storing predictions in the database
    """
    
    def __init__(self, model_dir='backend/models'):
        """
        Initialize the prediction service.
        
        Args:
            model_dir (str): Directory where model artifacts are stored
        """
        self.model_dir = model_dir
        self.trainer = ModelTrainer(model_dir=model_dir)
        
        # Load the model
        self.model = self.trainer.load_model()
        
        if self.model is None:
            logger.warning("No model loaded in prediction service initialization")
    
    def generate_predictions_for_date(self, game_date=None):
        """
        Generate predictions for all props on a specific date.
        
        Args:
            game_date (date): The date to generate predictions for (default: today)
            
        Returns:
            list: List of prediction results
        """
        app = create_app()
        with app.app_context():
            # Use today if no date provided
            if game_date is None:
                game_date = datetime.now().date()
                
            logger.info(f"Generating predictions for {game_date}")
                
            # Get all prop lines for this date
            prop_lines = PropLine.query.filter_by(game_date=game_date).all()
            
            if not prop_lines:
                logger.warning(f"No prop lines found for {game_date}")
                return []
                
            logger.info(f"Found {len(prop_lines)} prop lines for {game_date}")
            
            # Process each prop line
            results = []
            for prop in prop_lines:
                try:
                    # Get features for this player and date
                    X_pred = self.trainer.processor.prepare_prediction_features(
                        player_id=prop.player_id, 
                        game_date=game_date
                    )
                    
                    if X_pred is None or X_pred.empty:
                        logger.warning(f"No features available for player_id={prop.player_id}, date={game_date}")
                        continue
                    
                    # Make prediction
                    prob_over = self.trainer.make_predictions(X_pred)[0]
                    
                    # Store prediction in database
                    prediction = self.store_prediction(prop.id, prob_over)
                    
                    if prediction:
                        results.append({
                            'player_id': prop.player_id,
                            'player_name': prop.player.full_name,
                            'line': prop.line,
                            'prob_over': prob_over,
                            'prediction_id': prediction.id
                        })
                    
                except Exception as e:
                    logger.error(f"Error generating prediction for prop_id={prop.id}: {str(e)}")
            
            logger.info(f"Generated {len(results)} predictions for {game_date}")
            return results
    
    def generate_prediction_for_player(self, player_id, game_date=None):
        """
        Generate prediction for a specific player on a specific date.
        
        Args:
            player_id (int): The player's ID
            game_date (date): The date to generate prediction for (default: today)
            
        Returns:
            dict: Prediction result or None if not available
        """
        app = create_app()
        with app.app_context():
            # Use today if no date provided
            if game_date is None:
                game_date = datetime.now().date()
                
            logger.info(f"Generating prediction for player_id={player_id} on {game_date}")
                
            # Get prop line for this player and date
            prop = PropLine.query.filter_by(player_id=player_id, game_date=game_date).first()
            
            if not prop:
                logger.warning(f"No prop line found for player_id={player_id} on {game_date}")
                return None
            
            try:
                # Get features for this player and date
                X_pred = self.trainer.processor.prepare_prediction_features(
                    player_id=player_id, 
                    game_date=game_date
                )
                
                if X_pred is None or X_pred.empty:
                    logger.warning(f"No features available for player_id={player_id}, date={game_date}")
                    return None
                
                # Make prediction
                prob_over = self.trainer.make_predictions(X_pred)[0]
                
                # Store prediction in database
                prediction = self.store_prediction(prop.id, prob_over)
                
                if prediction:
                    return {
                        'player_id': prop.player_id,
                        'player_name': prop.player.full_name,
                        'line': prop.line,
                        'prob_over': prob_over,
                        'prediction_id': prediction.id
                    }
                
            except Exception as e:
                logger.error(f"Error generating prediction for player_id={player_id}: {str(e)}")
                
            return None
    
    def store_prediction(self, prop_line_id, prob_over):
        """
        Store a prediction in the database.
        
        Args:
            prop_line_id (int): The prop line ID
            prob_over (float): Predicted probability of going over
            
        Returns:
            Prediction: Created prediction object or None if failed
        """
        try:
            # Check if a prediction already exists
            existing = Prediction.query.filter_by(prop_line_id=prop_line_id).first()
            
            if existing:
                # Update existing prediction
                existing.prob_over = prob_over
                existing.generated_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"Updated prediction for prop_line_id={prop_line_id}")
                return existing
            
            # Create new prediction
            prediction = Prediction(
                prop_line_id=prop_line_id,
                prob_over=prob_over,
                generated_at=datetime.utcnow()
            )
            
            db.session.add(prediction)
            db.session.commit()
            
            logger.info(f"Created new prediction for prop_line_id={prop_line_id}")
            return prediction
            
        except SQLAlchemyError as e:
            logger.error(f"Database error storing prediction: {str(e)}")
            db.session.rollback()
            return None
    
    def get_predictions_for_date(self, game_date=None):
        """
        Get all predictions for a specific date.
        
        Args:
            game_date (date): The date to get predictions for (default: today)
            
        Returns:
            list: List of prediction results
        """
        app = create_app()
        with app.app_context():
            # Use today if no date provided
            if game_date is None:
                game_date = datetime.now().date()
                
            logger.info(f"Getting predictions for {game_date}")
            
            # Query for predictions with prop lines for this date
            query = """
            SELECT 
                p.id as player_id, p.full_name as player_name,
                pl.line, pred.prob_over, pred.id as prediction_id
            FROM predictions pred
            JOIN prop_lines pl ON pred.prop_line_id = pl.id
            JOIN players p ON pl.player_id = p.id
            WHERE pl.game_date = :game_date
            ORDER BY pred.prob_over DESC
            """
            
            result = db.session.execute(query, {'game_date': game_date})
            
            predictions = [dict(row) for row in result]
            
            logger.info(f"Found {len(predictions)} predictions for {game_date}")
            return predictions
    
    def get_prediction_for_player(self, player_id, game_date=None):
        """
        Get prediction for a specific player on a specific date.
        
        Args:
            player_id (int): The player's ID
            game_date (date): The date to get prediction for (default: today)
            
        Returns:
            dict: Prediction result or None if not available
        """
        app = create_app()
        with app.app_context():
            # Use today if no date provided
            if game_date is None:
                game_date = datetime.now().date()
                
            logger.info(f"Getting prediction for player_id={player_id} on {game_date}")
            
            # Query for prediction with prop line for this player and date
            query = """
            SELECT 
                p.id as player_id, p.full_name as player_name,
                pl.line, pred.prob_over, pred.id as prediction_id
            FROM predictions pred
            JOIN prop_lines pl ON pred.prop_line_id = pl.id
            JOIN players p ON pl.player_id = p.id
            WHERE pl.game_date = :game_date AND p.id = :player_id
            """
            
            result = db.session.execute(query, {
                'game_date': game_date,
                'player_id': player_id
            }).first()
            
            if result:
                return dict(result)
            
            # If no prediction found, generate one
            logger.info(f"No existing prediction found, generating new one")
            return self.generate_prediction_for_player(player_id, game_date)
    
    def validate_predictions(self, evaluation_date):
        """
        Validate predictions by comparing with actual results.
        This would be run after games are completed.
        
        Args:
            evaluation_date (date): Date for which to validate predictions
            
        Returns:
            dict: Validation metrics
        """
        app = create_app()
        with app.app_context():
            logger.info(f"Validating predictions for {evaluation_date}")
            
            # Find all predictions for the given date
            query = """
            SELECT 
                ps.points, pl.line, pred.prob_over, 
                p.id as player_id, p.full_name as player_name, 
                g.id as game_id
            FROM predictions pred
            JOIN prop_lines pl ON pred.prop_line_id = pl.id
            JOIN players p ON pl.player_id = p.id
            JOIN player_stats ps ON ps.player_id = p.id
            JOIN games g ON ps.game_id = g.id
            WHERE g.game_date = :game_date
            """
            
            result = db.session.execute(query, {'game_date': evaluation_date})
            validation_data = [dict(row) for row in result]
            
            if not validation_data:
                logger.warning(f"No validation data found for {evaluation_date}")
                return {}
                
            # Calculate validation metrics
            total = len(validation_data)
            correct = 0
            actual_hits = 0
            predicted_hits = 0
            
            for item in validation_data:
                # Actual result
                actual_hit = item['points'] >= item['line']
                if actual_hit:
                    actual_hits += 1
                    
                # Predicted result
                predicted_hit = item['prob_over'] >= 0.5
                if predicted_hit:
                    predicted_hits += 1
                
                # Check if prediction was correct
                if (predicted_hit and actual_hit) or (not predicted_hit and not actual_hit):
                    correct += 1
            
            # Calculate metrics
            accuracy = correct / total if total > 0 else 0
            actual_hit_rate = actual_hits / total if total > 0 else 0
            predicted_hit_rate = predicted_hits / total if total > 0 else 0
            
            metrics = {
                'date': evaluation_date,
                'total_props': total,
                'correct_predictions': correct,
                'accuracy': accuracy,
                'actual_hit_rate': actual_hit_rate,
                'predicted_hit_rate': predicted_hit_rate
            }
            
            logger.info(f"Validation results for {evaluation_date}: Accuracy={accuracy:.4f}, "
                       f"Actual hit rate={actual_hit_rate:.4f}, Predicted hit rate={predicted_hit_rate:.4f}")
            
            return metrics


def run_daily_predictions():
    """
    Run predictions for today's games.
    """
    logger.info("Starting daily predictions")
    
    service = PredictionService()
    today = datetime.now().date()
    
    # Generate predictions for today
    predictions = service.generate_predictions_for_date(today)
    
    logger.info(f"Generated {len(predictions)} predictions for {today}")
    
    # Optional: Also validate yesterday's predictions if games are complete
    yesterday = today - timedelta(days=1)
    try:
        validation = service.validate_predictions(yesterday)
        if validation:
            logger.info(f"Validation results for {yesterday}: Accuracy={validation.get('accuracy', 0):.4f}")
    except Exception as e:
        logger.error(f"Error validating yesterday's predictions: {str(e)}")
    
    logger.info("Daily predictions complete")
    
    return predictions


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run daily predictions
    run_daily_predictions() 
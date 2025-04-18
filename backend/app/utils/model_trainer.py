import os
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime
import joblib
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss, classification_report
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
import xgboost as xgb
import lightgbm as lgb
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve
from data_processor import DataProcessor

logger = logging.getLogger(__name__)

class ModelTrainer:
    """
    Handles model training, evaluation, selection, and persistence for NBA prop bet predictions.
    
    This class:
    1. Loads processed training data
    2. Trains and evaluates multiple model types
    3. Performs hyperparameter tuning
    4. Calibrates probability outputs
    5. Saves trained models with versioning
    """
    
    def __init__(self, model_dir='backend/models'):
        """
        Initialize the model trainer.
        
        Args:
            model_dir (str): Directory to store/load model artifacts
        """
        self.model_dir = model_dir
        self.data_processor = DataProcessor(model_dir=model_dir)
        
        # Ensure model directories exist
        os.makedirs(os.path.join(model_dir, 'latest'), exist_ok=True)
        
        # Define random state for reproducibility
        self.random_state = 42
        
    def load_training_data(self):
        """
        Load the training data prepared by the data processor.
        
        Returns:
            tuple: (X, y) - features and target
        """
        # Try to load from files first
        X_path = os.path.join(self.model_dir, 'latest', 'X_train.csv')
        y_path = os.path.join(self.model_dir, 'latest', 'y_train.csv')
        
        if os.path.exists(X_path) and os.path.exists(y_path):
            logger.info("Loading training data from files")
            X = pd.read_csv(X_path)
            y = pd.read_csv(y_path).iloc[:, 0]  # First column
            
            logger.info(f"Loaded training data: {X.shape[0]} samples, {X.shape[1]} features")
            return X, y
        
        # If files don't exist, prepare data
        logger.info("Training data files not found, preparing data")
        X, y = self.data_processor.prepare_training_data()
        
        if X is None or y is None:
            logger.error("Failed to prepare training data")
            return None, None
            
        # Save the processed data
        X.to_csv(X_path, index=False)
        pd.DataFrame(y, columns=['hit']).to_csv(y_path, index=False)
        
        return X, y
        
    def train_models(self, X, y, test_size=0.2):
        """
        Train and evaluate multiple models, selecting the best performer.
        
        Args:
            X (DataFrame): Features
            y (Series): Target variable
            test_size (float): Proportion of data to hold out for testing
            
        Returns:
            dict: Results of model training and evaluation
        """
        # Split data into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=self.random_state)
        
        # Keep track of player_id for stratification if present
        player_ids = None
        if 'player_id' in X.columns:
            player_ids = X['player_id']
            X_train = X_train.drop('player_id', axis=1)
            X_test = X_test.drop('player_id', axis=1)
        
        logger.info(f"Training data: {X_train.shape[0]} samples, Test data: {X_test.shape[0]} samples")
        
        # Define models to evaluate
        models = {
            'logistic': Pipeline([
                ('scaler', StandardScaler()),
                ('model', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=self.random_state))
            ]),
            'random_forest': RandomForestClassifier(
                n_estimators=100, 
                class_weight='balanced',
                random_state=self.random_state
            ),
            'xgboost': xgb.XGBClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                min_child_weight=1,
                gamma=0,
                subsample=0.8,
                colsample_bytree=0.8,
                objective='binary:logistic',
                scale_pos_weight=sum(y_train==0)/sum(y_train==1),  # Balance classes
                random_state=self.random_state
            ),
            'lightgbm': lgb.LGBMClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                class_weight='balanced',
                random_state=self.random_state
            )
        }
        
        # Train and evaluate each model
        results = {}
        for name, model in models.items():
            logger.info(f"Training {name} model")
            
            # 5-fold cross-validation on training data
            cv_auc = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc')
            
            # Fit on full training set
            model.fit(X_train, y_train)
            
            # Evaluate on test set
            y_prob = model.predict_proba(X_test)[:,1]
            auc = roc_auc_score(y_test, y_prob)
            brier = brier_score_loss(y_test, y_prob)
            
            results[name] = {
                'model': model,
                'cv_auc_mean': cv_auc.mean(),
                'cv_auc_std': cv_auc.std(),
                'test_auc': auc,
                'brier_score': brier,  # Lower is better, measures calibration
            }
            
            logger.info(f"{name} - CV AUC: {cv_auc.mean():.4f} ± {cv_auc.std():.4f}, Test AUC: {auc:.4f}, Brier: {brier:.4f}")
        
        # Select best model based on test AUC
        best_model_name = max(results, key=lambda k: results[k]['test_auc'])
        best_model = results[best_model_name]['model']
        
        logger.info(f"Best model: {best_model_name} with Test AUC: {results[best_model_name]['test_auc']:.4f}")
        
        return {
            'best_model_name': best_model_name,
            'best_model': best_model,
            'results': results,
            'X_train': X_train,
            'X_test': X_test,
            'y_train': y_train,
            'y_test': y_test,
            'feature_importance': self.get_feature_importance(best_model, best_model_name, X_train.columns)
        }
    
    def tune_hyperparameters(self, best_model_results):
        """
        Perform hyperparameter tuning on the best model.
        
        Args:
            best_model_results (dict): Results from initial model training
            
        Returns:
            dict: Updated results with tuned model
        """
        best_model_name = best_model_results['best_model_name']
        X_train = best_model_results['X_train']
        y_train = best_model_results['y_train']
        X_test = best_model_results['X_test']
        y_test = best_model_results['y_test']
        
        logger.info(f"Tuning hyperparameters for {best_model_name}")
        
        # Define parameter grids for each model type
        param_grids = {
            'logistic': {
                'model__C': [0.01, 0.1, 1.0, 10.0],
                'model__solver': ['liblinear', 'saga']
            },
            'random_forest': {
                'n_estimators': [100, 200, 300],
                'max_depth': [5, 10, 15, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            },
            'xgboost': {
                'learning_rate': [0.01, 0.05, 0.1],
                'max_depth': [3, 5, 7],
                'n_estimators': [100, 200, 300],
                'subsample': [0.8, 0.9, 1.0],
                'min_child_weight': [1, 3, 5]
            },
            'lightgbm': {
                'learning_rate': [0.01, 0.05, 0.1],
                'max_depth': [3, 5, 7, -1],
                'n_estimators': [100, 200, 300],
                'subsample': [0.8, 0.9, 1.0],
                'min_child_weight': [1, 3, 5]
            }
        }
        
        # Get the right model and parameter grid
        if best_model_name not in param_grids:
            logger.warning(f"No hyperparameter grid defined for {best_model_name}")
            return best_model_results
            
        model = best_model_results['best_model']
        param_grid = param_grids[best_model_name]
        
        # For pipeline models, we need to use the parameter prefix
        if best_model_name == 'logistic':
            grid_search = GridSearchCV(
                model, 
                param_grid, 
                cv=5, 
                scoring='roc_auc', 
                n_jobs=-1,
                verbose=1
            )
        else:
            grid_search = GridSearchCV(
                model, 
                param_grid, 
                cv=5, 
                scoring='roc_auc', 
                n_jobs=-1,
                verbose=1
            )
            
        # Fit grid search
        logger.info("Starting grid search (this may take a while)...")
        grid_search.fit(X_train, y_train)
        
        # Get best model
        best_params = grid_search.best_params_
        best_cv_score = grid_search.best_score_
        
        logger.info(f"Best parameters: {best_params}")
        logger.info(f"Best CV score: {best_cv_score:.4f}")
        
        # Evaluate on test set
        tuned_model = grid_search.best_estimator_
        y_prob = tuned_model.predict_proba(X_test)[:,1]
        auc = roc_auc_score(y_test, y_prob)
        brier = brier_score_loss(y_test, y_prob)
        
        logger.info(f"Tuned model - Test AUC: {auc:.4f}, Brier: {brier:.4f}")
        
        # Update results
        best_model_results['tuned_model'] = tuned_model
        best_model_results['tuned_params'] = best_params
        best_model_results['tuned_cv_score'] = best_cv_score
        best_model_results['tuned_test_auc'] = auc
        best_model_results['tuned_brier_score'] = brier
        
        # Update feature importance
        best_model_results['feature_importance'] = self.get_feature_importance(tuned_model, best_model_name, X_train.columns)
        
        return best_model_results
    
    def calibrate_model(self, model_results):
        """
        Calibrate the probabilistic outputs of the model using Platt scaling.
        
        Args:
            model_results (dict): Results from model training/tuning
            
        Returns:
            dict: Updated results with calibrated model
        """
        # Use tuned model if available, otherwise use best model
        if 'tuned_model' in model_results and model_results['tuned_model'] is not None:
            model = model_results['tuned_model']
            logger.info("Calibrating tuned model")
        else:
            model = model_results['best_model']
            logger.info("Calibrating best model")
            
        X_train = model_results['X_train']
        y_train = model_results['y_train']
        X_test = model_results['X_test']
        y_test = model_results['y_test']
        
        # Apply Platt scaling with isotonic calibration
        calibrated_model = CalibratedClassifierCV(
            model, 
            method='isotonic',  # 'sigmoid' for Platt scaling, 'isotonic' for non-parametric
            cv=5  # Use cross-validation for calibration
        )
        
        # Fit calibration model
        calibrated_model.fit(X_train, y_train)
        
        # Evaluate calibrated model
        y_prob_calibrated = calibrated_model.predict_proba(X_test)[:,1]
        auc_calibrated = roc_auc_score(y_test, y_prob_calibrated)
        brier_calibrated = brier_score_loss(y_test, y_prob_calibrated)
        
        logger.info(f"Calibrated model - Test AUC: {auc_calibrated:.4f}, Brier: {brier_calibrated:.4f}")
        
        # Update results
        model_results['calibrated_model'] = calibrated_model
        model_results['calibrated_test_auc'] = auc_calibrated
        model_results['calibrated_brier_score'] = brier_calibrated
        
        # Create calibration curves for visualization
        try:
            self.plot_calibration_curve(model, calibrated_model, X_test, y_test)
        except Exception as e:
            logger.warning(f"Failed to create calibration plot: {e}")
        
        return model_results
    
    def save_model_artifacts(self, model_results):
        """
        Save the trained model and associated artifacts with versioning.
        
        Args:
            model_results (dict): Results from model training/tuning/calibration
            
        Returns:
            str: Path to the saved model directory
        """
        # Create timestamped directory for this model version
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_dir = os.path.join(self.model_dir, timestamp)
        os.makedirs(model_dir, exist_ok=True)
        
        # Save the best model (use calibrated if available, otherwise tuned, then best)
        if 'calibrated_model' in model_results and model_results['calibrated_model'] is not None:
            final_model = model_results['calibrated_model']
            model_type = f"{model_results['best_model_name']}_calibrated"
            metrics = {
                'auc': model_results['calibrated_test_auc'],
                'brier_score': model_results['calibrated_brier_score']
            }
        elif 'tuned_model' in model_results and model_results['tuned_model'] is not None:
            final_model = model_results['tuned_model']
            model_type = f"{model_results['best_model_name']}_tuned"
            metrics = {
                'auc': model_results['tuned_test_auc'],
                'brier_score': model_results['tuned_brier_score']
            }
        else:
            final_model = model_results['best_model']
            model_type = model_results['best_model_name']
            metrics = {
                'auc': model_results['results'][model_type]['test_auc'],
                'brier_score': model_results['results'][model_type]['brier_score']
            }
        
        # Save model
        model_path = os.path.join(model_dir, 'model.joblib')
        joblib.dump(final_model, model_path)
        
        # Save feature names
        X_train = model_results['X_train']
        with open(os.path.join(model_dir, 'feature_columns.json'), 'w') as f:
            json.dump({'features': X_train.columns.tolist()}, f)
        
        # Save feature importance
        if model_results['feature_importance']:
            with open(os.path.join(model_dir, 'feature_importance.json'), 'w') as f:
                json.dump(model_results['feature_importance'], f)
        
        # Save performance metrics
        metrics.update({
            'model_type': model_type,
            'timestamp': timestamp,
            'training_samples': len(model_results['X_train']),
            'test_samples': len(model_results['X_test']),
            'features_count': len(model_results['X_train'].columns)
        })
        
        # Add hyperparameters if available
        if 'tuned_params' in model_results:
            metrics['hyperparameters'] = model_results['tuned_params']
            
        with open(os.path.join(model_dir, 'metrics.json'), 'w') as f:
            json.dump(metrics, f)
        
        # Create symlink to latest
        latest_dir = os.path.join(self.model_dir, 'latest')
        
        # Save model to latest as well (for simpler loading)
        joblib.dump(final_model, os.path.join(latest_dir, 'model.joblib'))
        
        # Save metrics to latest
        with open(os.path.join(latest_dir, 'metrics.json'), 'w') as f:
            json.dump(metrics, f)
        
        logger.info(f"Saved model artifacts to {model_dir}")
        logger.info(f"Updated latest model pointer to {timestamp}")
        
        return model_dir
    
    def get_feature_importance(self, model, model_name, feature_names):
        """
        Extract feature importance from the model.
        
        Args:
            model: Trained model
            model_name (str): Name of the model type
            feature_names (list): List of feature names
            
        Returns:
            dict: Feature importances
        """
        try:
            if model_name == 'logistic':
                # For logistic regression in a pipeline
                coefs = model.named_steps['model'].coef_[0]
                return dict(zip(feature_names, coefs))
            elif model_name == 'random_forest':
                return dict(zip(feature_names, model.feature_importances_))
            elif model_name == 'xgboost':
                return dict(zip(feature_names, model.feature_importances_))
            elif model_name == 'lightgbm':
                return dict(zip(feature_names, model.feature_importances_))
            return {}
        except Exception as e:
            logger.warning(f"Failed to extract feature importance: {e}")
            return {}
    
    def plot_calibration_curve(self, uncalibrated_model, calibrated_model, X_test, y_test, filename="calibration_curve.png"):
        """
        Plot and save calibration curves for both models.
        
        Args:
            uncalibrated_model: Original model
            calibrated_model: Calibrated model
            X_test: Test features
            y_test: Test targets
            filename (str): Output filename
        """
        plt.figure(figsize=(10, 6))
        
        # Calculate calibration curves
        prob_true, prob_pred = calibration_curve(y_test, uncalibrated_model.predict_proba(X_test)[:,1], n_bins=10)
        prob_true_cal, prob_pred_cal = calibration_curve(y_test, calibrated_model.predict_proba(X_test)[:,1], n_bins=10)
        
        # Plot perfectly calibrated
        plt.plot([0, 1], [0, 1], linestyle='--', label='Perfectly calibrated')
        
        # Plot models
        plt.plot(prob_pred, prob_true, marker='o', label='Uncalibrated')
        plt.plot(prob_pred_cal, prob_true_cal, marker='s', label='Calibrated')
        
        plt.xlabel('Mean predicted probability')
        plt.ylabel('Fraction of positives')
        plt.title('Calibration curve')
        plt.legend(loc='best')
        plt.grid(True)
        
        # Save the plot
        output_path = os.path.join(self.model_dir, 'latest', filename)
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Saved calibration curve to {output_path}")
    
    def train_and_save_model(self):
        """
        Run the complete model training pipeline.
        
        Returns:
            str: Path to the saved model directory
        """
        logger.info("Starting model training pipeline")
        
        # Load training data
        X, y = self.load_training_data()
        
        if X is None or y is None:
            logger.error("Failed to load training data")
            return None
        
        # Train initial models
        model_results = self.train_models(X, y)
        
        # Tune hyperparameters of best model
        model_results = self.tune_hyperparameters(model_results)
        
        # Calibrate probabilities
        model_results = self.calibrate_model(model_results)
        
        # Save model artifacts
        model_path = self.save_model_artifacts(model_results)
        
        logger.info("Model training pipeline complete")
        
        return model_path


def main():
    """
    Main function to run the model training pipeline.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Initializing model training")
    
    # Create model trainer
    trainer = ModelTrainer()
    
    # Run model training pipeline
    model_path = trainer.train_and_save_model()
    
    if model_path:
        logger.info(f"Model saved to {model_path}")
    else:
        logger.error("Model training failed")


if __name__ == "__main__":
    main() 
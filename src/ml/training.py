"""Orchestrates the loading of data and training of the regression model."""

import logging
import os
import joblib

from db.database import get_db
from db.queries import fetch_model_features
from ml.model import train_regression_model
import config

# TODO: make saving location customizable -> AWS S3, AWS SageMaker Model Registry, etc.
def run_training_pipeline():
    """Runs the full data fetching and model training pipeline and saves the model."""
    logging.info("Starting training pipeline...")
    logging.info("Connecting to the database...")
    with get_db() as db:
        try:
            logging.info("Fetching model features from the database...")
            features_df = fetch_model_features(db)

            if features_df.empty:
                logging.warning("No features were fetched. Aborting training pipeline.")
                return None # Indicate failure or lack of data

            logging.info(f"Fetched {len(features_df)} records. Proceeding to model training.")
            model = train_regression_model(features_df)

            if model:
                logging.info("Model training completed successfully.")
                
                try:
                    os.makedirs(config.DATA_DIR, exist_ok=True) 
                    logging.info(f"Saving model to {config.MODEL_SAVE_PATH}...")
                    joblib.dump(model, config.MODEL_SAVE_PATH)
                    logging.info("Model saved successfully.")
                except Exception as e:
                    logging.error(f"Failed to save the model to {config.MODEL_SAVE_PATH}: {e}", exc_info=True)
                    
                return model # Return the trained model object even if saving failed, but log error
            else:
                logging.error("Model training failed.")
                return None # Indicate failure

        except Exception as e:
            logging.error(f"An error occurred during the training pipeline: {e}", exc_info=True)
            return None # Indicate failure

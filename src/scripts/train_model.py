"""
This script is responsible for initiating and managing the model training process.
It imports the `run_training_pipeline` function from the `ml.training` module
and executes it when the script is run directly.

The main function within this script calls the training pipeline and prints
information about the trained model, such as its intercept and coefficient,
or a message indicating if the training was unsuccessful.
"""
from ml.training import run_training_pipeline

import logging

def main():
    logging.info("Running training pipeline as standalone script...")
    trained_model = run_training_pipeline()
    if trained_model:
        logging.info("Pipeline finished. Trained model object is available.")
        logging.info(f"Model intercept: {trained_model.intercept_}")
        logging.info(f"Model coefficient: {trained_model.coef_[0]}")
    else:
        logging.info(
            "Pipeline finished, but model training was unsuccessful or no data was found."
        )

if __name__ == "__main__":
    main()

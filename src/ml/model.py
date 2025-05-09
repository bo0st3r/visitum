"""Functions for training and evaluating the ML model."""

import logging
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split 

logger = logging.getLogger(__name__)

def train_regression_model(features_df: pd.DataFrame) -> LinearRegression | None:
    """
    Trains a simple linear regression model (Population vs. Visitor Count).

    Args:
        features_df: A Pandas DataFrame with 'population' (feature X) 
                     and 'visitors_count' (target y) columns.

    Returns:
        A trained scikit-learn LinearRegression model object, or None if 
        training is not possible (e.g., insufficient data).
    """
    logging.info(f"Starting model training with {len(features_df)} records.")

    if features_df.empty or len(features_df) < 2: # Need at least 2 points for regression
        logging.error("Insufficient data to train the regression model.")
        return None

    try:
        # Prepare features (X) and target (y)
        # Reshape X to be a 2D array as required by scikit-learn
        X = features_df[['population']]
        y = features_df['visitors_count']

        # While the assignment doesn't explicitly require evaluation, splitting helps evaluate the model's performance.
        X_train, X_test, y_train, y_test = train_test_split(X, y, train_size=0.8, test_size=0.2, random_state=42)

        # Initialize and train the model
        model = LinearRegression()
        model.fit(X_train, y_train)
        
        # Evaluate the model
        score = model.score(X_test, y_test)
        score_result = None
        if score > 0.8:
            score_result = "Good"
        elif score > 0.5:
            score_result = "Moderate"
        elif score > 0.2:
            score_result = "Low"
        elif score >= 0.0:
            score_result = "Terrible"
        else:
            score_result = "CATASTROPHIC :("
        logging.info(f"Model R-squared score: {score:.2f}; it's... {score_result}")

        # Log model coefficients
        intercept = model.intercept_
        coefficient = model.coef_[0] # It's a 1D array for single feature
        logging.info(f"Model training complete. Intercept: {intercept:.2f}, Coefficient: {coefficient:.2f}")
        logging.info(f"Model equation: visitors_count ≈ {coefficient:.2f} * population + {intercept:.2f}")

        return model

    except Exception as e:
        logging.error(f"An error occurred during model training: {e}", exc_info=True)
        return None
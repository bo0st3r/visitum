import pandas as pd
from sklearn.linear_model import LinearRegression
from unittest.mock import patch
from src.ml.model import train_regression_model


def test_train_regression_model_logic():
    """Tests the train_regression_model function for various scenarios."""
    
    # 1. Test with valid data for successful training
    valid_data = pd.DataFrame({
        'population': [100000, 200000, 300000, 400000, 500000],
        'visitors_count': [10000, 19000, 31000, 42000, 48000]
    })
    with patch('src.ml.model.logging') as mock_logging: # Just making sure the logging has been called
        model = train_regression_model(valid_data)
        assert model is not None, "Model should be trained with valid data"
        assert isinstance(model, LinearRegression), "Should return a LinearRegression model"
        assert hasattr(model, 'coef_') and model.coef_ is not None, "Model should have coefficients"
        assert hasattr(model, 'intercept_') and model.intercept_ is not None, "Model should have an intercept"
        # For this predictable data, coefficient should be around 0.1
        assert 0.05 < model.coef_[0] < 0.15, f"Coefficient {model.coef_[0]} out of expected range"
        assert any("Model R-squared score:" in call.args[0] for call in mock_logging.info.call_args_list) 
        
    # 2. Test with an empty DataFrame
    empty_df = pd.DataFrame(columns=['population', 'visitors_count'])
    model_empty = train_regression_model(empty_df)
    assert model_empty is None, "Model should be None for empty DataFrame"

    # 3. Test with insufficient data (less than 2 rows)
    insufficient_df = pd.DataFrame({
        'population': [100000],
        'visitors_count': [10000]
    })
    model_insufficient = train_regression_model(insufficient_df)
    assert model_insufficient is None, "Model should be None for insufficient data"


import pandas as pd
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

# Import the function to be tested
from src.db.queries import fetch_model_features

@patch('src.db.queries.pd.read_sql')
def test_fetch_model_features_success(mock_read_sql):
    """Tests successful fetching and processing of model features."""
    mock_db_session = MagicMock(spec=Session) # create a mock session
    
    filtered_db_data = [
        (1000000, 1500000),
        (2000000, 2500000),
        (500000, 750000)
    ]
    columns = ['population', 'visitors_count']
    
    # Assign a basic mock engine to db_session.bind
    mock_db_session.bind = None # pandas.read_sql doesn't actually use the engine object because it's mocked

    # Configure the mock for pd.read_sql to return specific data
    mock_read_sql.return_value = pd.DataFrame(filtered_db_data, columns=columns)

    result_df = fetch_model_features(mock_db_session)

    mock_read_sql.assert_called_once()

    expected_df = pd.DataFrame({
        'population': [1000000, 2000000, 500000],
        'visitors_count': [1500000, 2500000, 750000]
    })
    
    pd.testing.assert_frame_equal(result_df.sort_values(by=['population']).reset_index(drop=True), 
                                   expected_df.sort_values(by=['population']).reset_index(drop=True))
    assert list(result_df.columns) == ['population', 'visitors_count']
    assert not result_df.isnull().any().any(), "DataFrame should not contain nulls after filtering"

@patch('src.db.queries.pd.read_sql') # Apply patch here for consistency if desired, or keep as context manager
def test_fetch_model_features_db_error(mock_read_sql_arg): # Renamed to avoid conflict if also using with below
    """Tests behavior when pd.read_sql raises an exception."""
    mock_db_session = MagicMock(spec=Session)

    # Configure the mock for pd.read_sql to raise an exception
    mock_read_sql_arg.side_effect = Exception("Database connection error")
        
    result_df = fetch_model_features(mock_db_session)
    
    assert result_df.empty
    # When an exception occurs, fetch_model_features returns pd.DataFrame(), which has no columns.
    assert list(result_df.columns) == [] 
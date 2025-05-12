import pandas as pd
from unittest.mock import patch

# Imports from the src directory
from src.data.transformation import clean_museum_data, handle_compound_city
from src.data.models import FetchFailureReason

# Assuming config values like year to filter might be used implicitly or explicitly

# Sample DataFrames for testing clean_museum_data

RAW_MUSEUM_DATA_FOR_PARSING_FILTERING = pd.DataFrame(
    {
        "Museum Name": [
            "Tokyo Skytree",
            "Louvre",
            "British Museum",
            "Met",
            "Small Museum",
            "Old Museum",
            "Biodome",
        ],
        "City": [
            "Tokyo",
            "Paris",
            "London",
            "New York",
            "Anytown",
            "Historic City",
            "Montreal",
        ],
        "Country": ["Japan", "France", "UK", "USA", "CountryA", "CountryB", "Canada"],
        "Visitors in 2024": [
            "2,825,000",  # Valid, > 1.25M, year 2024 (implicit)
            "1.3 million",  # Valid, > 1.25M, year 2024 (implicit)
            "1,000,000 (2024)",  # Below threshold
            "2,000,000 (2023)",  # Wrong year
            "Invalid Data",  # Unparseable
            "1,500,000 (2025)",  # Wrong year (future)
            "2,5 million [in 2024]",  # Combo, and , separator for 'x millions'
        ],
    }
)

EXPECTED_AFTER_PARSING_FILTERING = pd.DataFrame(
    {
        "name": ["Tokyo Skytree", "Louvre", "Biodome"],
        "city": ["Tokyo", "Paris", "Montreal"],
        "country": ["Japan", "France", "Canada"],
        "visitors_count": [2825000, 1300000, 2500000],
        "visitors_year": [2024, 2024, 2024],
    }
)

RAW_MUSEUM_DATA_FOR_COL_CLEANUP = pd.DataFrame(
    {
        "Museum Name": ["Louvre"],
        "  City  ": ["Paris[1]"],  # Needs stripping and citation removal
        "COUNTRY": ["France"],
        "visitors_in_2024": ["2,825,000"],
        "Extra Column": ["should be dropped"],
    }
)

EXPECTED_AFTER_COL_CLEANUP = pd.DataFrame(
    {
        "name": ["Louvre"],
        "city": ["Paris"],  # Cleaned city name
        "country": ["France"],
        "visitors_count": [2825000],
        "visitors_year": [2024],
    }
)


def test_clean_museum_data_visitor_parsing_and_filtering():
    """Tests visitor string parsing, year extraction, and filtering logic."""
    # Override config for the test if necessary, e.g. if a specific year is hardcoded
    # For now, assumes default config.py values (e.g. implicit 2024 if not in string)

    cleaned_df = clean_museum_data(RAW_MUSEUM_DATA_FOR_PARSING_FILTERING.copy())

    assert cleaned_df is not None, "Cleaned DataFrame should not be None"
    # Sort by name for consistent comparison
    cleaned_df = cleaned_df.sort_values(by="name").reset_index(drop=True)
    expected_df = EXPECTED_AFTER_PARSING_FILTERING.sort_values(by="name").reset_index(
        drop=True
    )

    pd.testing.assert_frame_equal(cleaned_df, expected_df, check_dtype=True)


def test_clean_museum_data_column_operations():
    """Tests column name standardization, final selection, and city name cleaning."""
    cleaned_df = clean_museum_data(RAW_MUSEUM_DATA_FOR_COL_CLEANUP.copy())

    assert cleaned_df is not None, "Cleaned DataFrame should not be None"
    # Sort by name for consistent comparison if multiple rows were expected
    cleaned_df = cleaned_df.sort_values(by="name").reset_index(drop=True)
    expected_df = EXPECTED_AFTER_COL_CLEANUP.sort_values(by="name").reset_index(
        drop=True
    )

    pd.testing.assert_frame_equal(cleaned_df, expected_df, check_dtype=True)


@patch("src.data.transformation.fetch_city_population_with_geocoder")
def test_handle_compound_city_logic(mock_fetch_population):
    """Tests special rules and general comma-splitting for compound cities."""

    # Test single city name - no splitting, direct fetch
    mock_fetch_population.reset_mock()
    mock_fetch_population.side_effect = None  # Clear previous side_effect
    mock_fetch_population.return_value = 500000
    pop_single = handle_compound_city("Lyon", "France")
    mock_fetch_population.assert_called_once_with("Lyon", "France")
    assert pop_single == 500000

    # Test Vatican City rule
    mock_fetch_population.reset_mock()  # Reset for each case
    mock_fetch_population.return_value = 12345  # Mocked population for Rome
    pop_vatican = handle_compound_city("Vatican City", "Vatican City")
    mock_fetch_population.assert_called_once_with("Rome", "Italy")
    assert pop_vatican == 12345

    # Test South Kensington, London rule
    mock_fetch_population.reset_mock()
    mock_fetch_population.return_value = 9000000  # Mocked population for London
    pop_sk = handle_compound_city("South Kensington, London", "United Kingdom")
    mock_fetch_population.assert_called_once_with("London", "United Kingdom")
    assert pop_sk == 9000000

    # To precisely test general splitting, let's make the full string fail, and first part succeed
    def side_effect_general_split(city, country):
        if city == "Paris, Some Other Place":
            return FetchFailureReason.NO_DATA_FOR_CITY  # Mock full string failing
        elif city == "Paris" and country == "France":
            return 2000000  # Mock "Paris" succeeding
        return FetchFailureReason.FETCH_ERROR  # Fallback for other parts

    mock_fetch_population.reset_mock()
    mock_fetch_population.side_effect = side_effect_general_split
    pop_paris_split = handle_compound_city("Paris, Some Other Place", "France")
    assert mock_fetch_population.call_count >= 2  # Called for full, then for "Paris"
    # Check one of the calls was for Paris, France 
    assert any(
        call_args[0] == ("Paris", "France")
        for call_args in mock_fetch_population.call_args_list
    )
    assert any(
        call_args[0] == ("Some Other Place", "France")
        for call_args in mock_fetch_population.call_args_list
    )
    assert pop_paris_split == 2000000

    # Test city string that results in no population after trying parts
    mock_fetch_population.reset_mock()
    mock_fetch_population.return_value = (
        FetchFailureReason.NO_DATA_FOR_CITY
    )  # All parts fail
    pop_not_found = handle_compound_city("Obscure Town, Nonexistent Region", "Far Away")
    # Call count depends on how many parts + full string are tried
    assert mock_fetch_population.call_count > 0
    assert pop_not_found.value == FetchFailureReason.NO_DATA_FOR_COMPOUND_CITY.value

    # Test empty city string
    mock_fetch_population.reset_mock()
    pop_empty = handle_compound_city("", "Country")
    mock_fetch_population.assert_not_called()  # Should not call if city string is empty
    assert pop_empty.value == FetchFailureReason.NO_DATA_FOR_COMPOUND_CITY.value

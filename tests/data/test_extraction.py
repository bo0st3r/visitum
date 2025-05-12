from unittest.mock import patch, MagicMock
import pandas as pd

from src.data.extraction import (
    get_wikipedia_museum_visitors_page_html,
    extract_museum_visitors_table_from_html,
    fetch_city_population_with_geocoder,
)
from src.config import (
    WIKIPEDIA_API_URL,
    MUSEUMS_VISITORS_WIKIPEDIA_PAGE_TITLE,
    MUSEUMS_VISITORS_MATCH_PATTERN,
    MAX_GEOCODER_RETRIES,
)
from src.data.models import FetchFailureReason


@patch("src.data.extraction.requests.get")
def test_get_wikipedia_museum_visitors_page_html_success(mock_get):
    """Tests fetching of Wikipedia page HTML via MediaWiki API."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "parse": {
            "title": "List of most-visited museums",
            "text": {"*": "<html><body>Mock HTML for successful fetch</body></html>"},
        }
    }
    mock_get.return_value = mock_response

    html_content = get_wikipedia_museum_visitors_page_html(
        MUSEUMS_VISITORS_WIKIPEDIA_PAGE_TITLE
    )

    expected_params = {
        "action": "parse",
        "page": MUSEUMS_VISITORS_WIKIPEDIA_PAGE_TITLE,
        "prop": "text",
        "format": "json",
        "redirects": True,
    }
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert args[0] == WIKIPEDIA_API_URL
    assert kwargs["params"] == expected_params
    assert html_content == "<html><body>Mock HTML for successful fetch</body></html>"


# Tests for extract_museum_visitors_table_from_html (2 Tests)


def test_extract_museum_visitors_table_from_html_success_with_match():
    """Tests successful extraction of museum data table when primary match pattern works."""
    df = extract_museum_visitors_table_from_html(
        f"""
<html><body>
    <p>Text including {MUSEUMS_VISITORS_MATCH_PATTERN}</p>
    <table class="wikitable sortable">
        <thead>
            <tr><th>Name</th><th>City</th><th>Country</th><th>Visitors per year</th><th>Year reported</th></tr>
        </thead>
        <tbody>
            <tr><td>Tokyo Skytree</td><td>Tokyo</td><td>Japan</td><td>2,825,000</td><td>2024</td></tr>
            <tr><td>Ghibli Museum</td><td>Tokyo</td><td>Japan</td><td>4,097,000</td><td>2024</td></tr>
        </tbody>
    </table>
</body></html>
"""
    )

    assert df is not None
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    expected_columns = ["Name", "City", "Country", "Visitors per year", "Year reported"]
    assert all(col in df.columns for col in expected_columns)
    assert df.iloc[0]["Name"] == "Tokyo Skytree"
    assert df.iloc[1]["Name"] == "Ghibli Museum"


def test_extract_museum_visitors_table_from_html_no_usable_table_found():
    """Tests behavior when HTML contains no tables at all, expecting None."""
    df = extract_museum_visitors_table_from_html(
        """
<html><body>
    <p>This HTML page contains no tables whatsoever.</p>
    <p>Just some text paragraphs.</p>
</body></html>
"""
    )
    assert df is None


# Tests for fetch_city_population_with_geocoder (2 Tests)


@patch("src.data.extraction.geocoder.geonames")
def test_fetch_city_population_with_geocoder_success(mock_geonames_call):
    """Tests successful fetching of city population."""
    mock_geo_response = MagicMock()
    mock_geo_response.ok = True
    mock_geo_response.population = 1234567
    mock_geonames_call.return_value = mock_geo_response

    population = fetch_city_population_with_geocoder("Test City", "Test Country")

    mock_geonames_call.assert_called_once_with("Test City, Test Country", key="visitum")
    assert population == 1234567


@patch("src.data.extraction.time.sleep")
@patch("src.data.extraction.geocoder.geonames")
def test_fetch_city_population_with_geocoder_persistent_api_failure(
    mock_geonames_call, mock_sleep
):
    """Tests geocoder API failing after all retries, returning FetchFailureReason.FETCH_ERROR."""
    mock_geo_response = MagicMock()
    mock_geo_response.ok = False
    mock_geo_response.status = "Persistent API Error"
    mock_geonames_call.return_value = mock_geo_response

    result = fetch_city_population_with_geocoder("Failed City", "Failed Country")

    assert mock_geonames_call.call_count == MAX_GEOCODER_RETRIES
    # Sleep is called (MAX_GEOCODER_RETRIES - 1) times because it's called *before* a retry attempt,
    # not after the last failed attempt in the loop.
    assert (
        mock_sleep.call_count == max(0, MAX_GEOCODER_RETRIES - 1)
    )
    assert result.value == FetchFailureReason.FETCH_ERROR.value

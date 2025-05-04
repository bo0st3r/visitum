import requests
import pandas as pd
from io import StringIO
import logging
import time
import geocoder
from typing import Optional, Union

# Imports assuming src is the top-level package directory
import config 
from data.models import FetchFailureReason

# Configure logging for this module
logger = logging.getLogger(__name__)

def get_wikipedia_museum_visitors_page_html(page_title: str) -> Optional[str]:
    """
    Fetches the parsed HTML content of a Wikipedia page using the MediaWiki API.

    Args:
        page_title: The title of the Wikipedia page.

    Returns:
        The HTML content as a string, or None if an error occurs.
    """
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "text",  # Request the parsed HTML content
        "format": "json",
        "redirects": True, # Follow redirects
    }

    headers = {
        "User-Agent": config.WIKIPEDIA_USER_AGENT
    }

    logger.info(f"Requesting HTML for page: {page_title} from {config.WIKIPEDIA_API_URL}")
    try:
        response = requests.get(config.WIKIPEDIA_API_URL, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        if "parse" in data and "text" in data["parse"] and "*" in data["parse"]["text"]:
            html_content = data["parse"]["text"]["*"]
            logger.info(f"Successfully retrieved HTML for {page_title}")
            return html_content
        else:
            logger.error(f"Could not find parsed text in API response for {page_title}")
            logger.debug(f"API Response: {data}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error fetching Wikipedia page {page_title}: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred fetching Wikipedia page {page_title}: {e}")
        return None

def extract_museum_visitors_table_from_html(html_content: str) -> Optional[pd.DataFrame]:
    """
    Extracts the main museum table from HTML content using pandas.read_html.

    Args:
        html_content: The HTML string containing the tables.

    Returns:
        A pandas DataFrame representing the museum table, or None if not found.
    """
    if not html_content:
        logger.warning("HTML content provided for table extraction is empty.")
        return None

    try:
        html_io = StringIO(html_content)
        list_of_dataframes = []

        # Attempt 1: Match specific table header
        try:
            logger.info(f"Attempting table extraction matching pattern: '{config.MUSEUMS_VISITORS_MATCH_PATTERN}'")
            list_of_dataframes = pd.read_html(html_io, match=config.MUSEUMS_VISITORS_MATCH_PATTERN)
            logger.info(f"Found table using match='{config.MUSEUMS_VISITORS_MATCH_PATTERN}'.")

        except ValueError:
            logger.warning(f"No table found matching '{config.MUSEUMS_VISITORS_MATCH_PATTERN}'. Trying fallback.")
            list_of_dataframes = []

        # Attempt 2: Fallback - Read all tables and select largest
        if not list_of_dataframes:
            try:
                logger.info("Fallback: Reading all tables from HTML.")
                html_io.seek(0)
                all_dataframes = pd.read_html(html_io)

                if all_dataframes:
                     museum_df = max(all_dataframes, key=lambda df: df.size)
                     list_of_dataframes = [museum_df]
                     logger.info(f"Fallback successful. Selected largest table with shape: {museum_df.shape}")
                else:
                     logger.error("Fallback failed: No tables found in the HTML content.")
                     return None

            except Exception as e:
                logger.error(f"Error during fallback table extraction: {e}")
                return None

        if list_of_dataframes:
            museum_df = list_of_dataframes[0]
            logger.info(f"Processing extracted table with shape: {museum_df.shape}")
            # Basic column check
            if 'Name' not in museum_df.columns or 'City' not in museum_df.columns:
                logger.warning(f"Extracted table missing essential columns ('Name', 'City'). Columns: {museum_df.columns.tolist()}")
                # Consider returning None or raising a specific error if essential columns are missing
                # return None
            return museum_df
        else:
            logger.error("Extraction failed: No DataFrame selected after all attempts.")
            return None

    except Exception as e:
        logger.error(f"An unexpected error occurred during table extraction: {e}")
        return None

def fetch_city_population_with_geocoder(city: str, country: str) -> Optional[Union[int, FetchFailureReason]]:
    """
    Fetch city population using the geocoder library (Geonames provider).

    Args:
        city: City name.
        country: Country name.

    Returns:
        Population as integer, a FetchFailureReason enum member, or None for unexpected errors.
    """
    query = f"{city}, {country}"
    logger.debug(f"Fetching population for query: '{query}' using Geonames (User: {config.GEONAMES_USERNAME})")

    for attempt in range(config.MAX_GEOCODER_RETRIES):
        try:
            # Specify provider and key explicitly
            g = geocoder.geonames(query, key=config.GEONAMES_USERNAME)

            if g.ok:
                if hasattr(g, 'population') and g.population and g.population > 0:
                    pop = int(g.population)
                    logger.debug(f"Successfully fetched population for {query}: {pop}")
                    return pop
                else:
                    # City found, but no population data
                    logger.warning(f"No population data found for {query} via Geonames.")
                    return FetchFailureReason.NO_DATA_FOR_CITY
            else:
                # Geocoder returned an error status
                logger.warning(f"Geocoder status not OK for {query} on attempt {attempt + 1}/{config.MAX_GEOCODER_RETRIES}. Status: {g.status}")

        except Exception as e:
            logger.error(f"Exception during geocoder call for {query} on attempt {attempt + 1}: {e}")

        # Wait before retrying if not the last attempt
        if attempt < config.MAX_GEOCODER_RETRIES - 1:
            logger.info(f"Retrying geocoder lookup for {query} after delay...")
            time.sleep(config.GEOCODER_RETRY_DELAY_SECONDS)

    logger.error(f"Could not get population data for {query} after {config.MAX_GEOCODER_RETRIES} attempts.")
    return FetchFailureReason.FETCH_ERROR 
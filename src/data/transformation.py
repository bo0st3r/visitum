import pandas as pd
import re
import logging
import concurrent.futures
from typing import Optional, Tuple

# Imports assuming src is the top-level package directory
import config 
from data.models import FetchFailureReason
from data.extraction import fetch_city_population_with_geocoder


def clean_museum_data(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Cleans the raw museum DataFrame extracted from Wikipedia.

    - Standardizes column names.
    - Extracts visitor count and year from a combined column.
    - Filters based on year (2024) and visitor count (> 1,250,000).
    - Selects and renames final columns.
    - Cleans city names.

    Args:
        df: Raw DataFrame extracted from Wikipedia.

    Returns:
        Cleaned and filtered DataFrame, or None if processing fails.
    """
    if df is None or df.empty:
        logging.warning("Input DataFrame for cleaning is None or empty.")
        return None

    cleaned_df = df.copy()

    # Standardize column names (lowercase, replace space with underscore)
    cleaned_df.columns = [str(col).strip().lower().replace(' ', '_') for col in cleaned_df.columns]
    logging.debug(f"Standardized columns: {cleaned_df.columns.tolist()}")

    # --- Visitor Count and Year Extraction ---
    visitor_col = None
    # Prioritize columns matching the expected pattern or common names
    possible_visitor_cols = [
        'visitors_in_2024', # Exact match from pattern
        'visitors',         # Common fallback
    ]
    for col in possible_visitor_cols:
        if col in cleaned_df.columns:
            visitor_col = col
            logging.info(f"Using column '{visitor_col}' for visitor data.")
            break
    # If not found, try a broader search
    if not visitor_col:
        for col in cleaned_df.columns:
            if 'visitors' in col and ('2024' in col or 'year' in col):
                visitor_col = col
                logging.info(f"Using column '{visitor_col}' based on content search.")
                break

    if not visitor_col:
        logging.error("Could not identify the visitor count column. Cannot proceed with cleaning.")
        # Check if any column name contains 'visitor'
        fallback = [col for col in cleaned_df.columns if 'visitor' in col]
        if fallback:
            logging.warning(f"Potential visitor columns found but not used: {fallback}")
        return None

    def _extract_visitor_info(value_str):
        try:
            value_str = str(value_str).strip()
            value_str = re.sub(r'\[\d+\]', '', value_str) # Remove citation like [1]

            # Default year to 2024, extract if specified e.g., (2023)
            year_match = re.search(r'\((\d{4})\)', value_str)
            year = int(year_match.group(1)) if year_match else 2024

            # Extract number, removing commas
            count_match = re.search(r'([\d,\.]+)', value_str)
            if count_match:
                num_str = count_match.group(1).replace(',', '')
                count = float(num_str)
                if 'million' in value_str.lower():
                    count *= 1_000_000
                return int(count), year
            return None, year # No number found
        except Exception as e:
            logging.warning(f"Could not parse visitor info from '{value_str}': {e}")
            return None, None

    visitor_data = cleaned_df[visitor_col].apply(_extract_visitor_info)
    cleaned_df['visitors_count'] = visitor_data.apply(lambda x: x[0])
    cleaned_df['visitors_year'] = visitor_data.apply(lambda x: x[1])

    # Drop rows where visitor count is missing after parsing
    original_rows = len(cleaned_df)
    cleaned_df = cleaned_df.dropna(subset=['visitors_count'])
    if len(cleaned_df) < original_rows:
        logging.info(f"Dropped {original_rows - len(cleaned_df)} rows due to missing visitor counts after parsing.")

    if cleaned_df.empty:
        logging.warning("DataFrame empty after dropping rows with missing visitor counts.")
        return cleaned_df # Return empty df

    # Convert count and year to integer types
    cleaned_df['visitors_count'] = cleaned_df['visitors_count'].astype(int)
    cleaned_df['visitors_year'] = cleaned_df['visitors_year'].astype(int)

    # --- Filtering ---
    logging.info(f"Rows before filtering: {len(cleaned_df)}")
    # 1. Filter for Year == 2024
    cleaned_df = cleaned_df[cleaned_df['visitors_year'] == 2024].copy()
    logging.info(f"Rows after filtering for Year == 2024: {len(cleaned_df)}")

    # 2. Filter for Visitors > 1,250,000
    min_visitors = 1_250_000
    cleaned_df = cleaned_df[cleaned_df['visitors_count'] > min_visitors].copy()
    logging.info(f"Rows after filtering for Visitors > {min_visitors:,}: {len(cleaned_df)}")

    if cleaned_df.empty:
        logging.warning("No museums remained after filtering. Returning empty DataFrame.")
        return cleaned_df

    # --- Final Column Selection and Renaming ---
    # Ensure essential columns exist, handling potential variations in naming
    final_cols_map = {
        'name': 'name', # Standardized name column
        'city': 'city',
        'country': 'country',
        'visitors_count': 'visitors_count',
        'visitors_year': 'visitors_year'
    }

    # Find actual column names in the DataFrame corresponding to the map keys
    cols_to_select = {}
    for target_col, source_col_pattern in final_cols_map.items():
        found = False
        if source_col_pattern in cleaned_df.columns:
            cols_to_select[target_col] = source_col_pattern
            found = True
        else:
             # Attempt partial match if exact not found (e.g., 'name_of_museum')
            for col in cleaned_df.columns:
                if source_col_pattern in col:
                    cols_to_select[target_col] = col
                    logging.debug(f"Mapped target '{target_col}' to source '{col}' (partial match)")
                    found = True
                    break
        if not found:
             logging.warning(f"Could not find a source column for target '{target_col}'. It will be missing.")

    # Select and rename columns based on the mapping
    cleaned_df = cleaned_df[[source for source in cols_to_select.values()]].copy()
    cleaned_df.rename(columns={v: k for k, v in cols_to_select.items()}, inplace=True)

    # Check if essential columns are present after selection/rename
    essential_cols = ['name', 'city', 'country', 'visitors_count']
    missing_essentials = [col for col in essential_cols if col not in cleaned_df.columns]
    if missing_essentials:
        logging.error(f"Essential columns missing after final selection: {missing_essentials}")
        # Decide whether to return None or the incomplete DataFrame
        # return None

    # Clean up city names (remove citations, strip whitespace)
    if 'city' in cleaned_df.columns:
        cleaned_df['city'] = cleaned_df['city'].astype(str).str.replace(r'\[\d+\]', '', regex=True).str.strip()
    else:
        logging.warning("Column 'city' not found for final cleaning.")

    logging.info(f"Cleaning complete. Final shape: {cleaned_df.shape}")
    return cleaned_df

def handle_compound_city(city_string: str, country: str) -> Optional[int]:
    """
    Handles compound city entries (e.g., "Vatican City, Rome") by attempting
    to fetch the population of the primary metropolitan area.

    Args:
        city_string: The city name string, potentially containing multiple parts.
        country: The country name.

    Returns:
        Population of the most relevant city/area, or a FetchFailureReason.
    """
    original_city_string = city_string # Keep for logging
    original_country = country

    # --- Special Case Handling ---
    # TODO: Move these rules to a configuration file or database for flexibility.
    city_lower = city_string.lower()
    country_lower = country.lower()

    if 'vatican' in city_lower and 'vatican' in country_lower:
        logging.info(f"Applying rule: '{original_city_string}, {original_country}' -> 'Rome, Italy'")
        city_string = "Rome"
        country = "Italy"
    elif 'london' in city_lower and 'south kensington' in city_lower:
        logging.info(f"Applying rule: '{original_city_string}, {original_country}' -> 'London, United Kingdom'")
        city_string = "London"
        country = "United Kingdom"
    # Add more rules here as needed

    # --- General Handling for Comma-Separated Cities ---
    cities = [city.strip() for city in city_string.split(',') if city.strip()]

    if not cities:
        logging.warning(f"Could not extract any city names from '{original_city_string}'")
        return FetchFailureReason.NO_DATA_FOR_COMPOUND_CITY # Or a more specific reason

    if len(cities) == 1:
        # Single city (or normalized to one), fetch its population
        return fetch_city_population_with_geocoder(cities[0], country)

    # --- Multiple Cities Detected --- #
    logging.info(f"Handling multiple cities for '{original_city_string}, {original_country}': {cities}")
    populations = {}
    failure_reasons = {}

    for city_part in cities:
        pop_result = fetch_city_population_with_geocoder(city_part, country)
        if isinstance(pop_result, int):
            populations[city_part] = pop_result
        else:
            failure_reasons[city_part] = pop_result
            logging.warning(f"Population lookup failed for part '{city_part}' of '{original_city_string}, {original_country}'. Reason: {pop_result}")

    if not populations:
        logging.error(f"Could not retrieve population for any part of '{original_city_string}, {original_country}'. Failures: {failure_reasons}")
        # Return the most severe failure reason, or a general one
        return FetchFailureReason.NO_DATA_FOR_COMPOUND_CITY
    elif len(populations) == 1:
        # Only one part yielded a population
        city_found, pop_found = list(populations.items())[0]
        logging.info(f"Using population {pop_found} from '{city_found}' for '{original_city_string}, {original_country}'")
        return pop_found
    else:
        # Multiple parts yielded populations, choose the largest (proxy for metro area)
        largest_city = max(populations, key=populations.get)
        max_pop = populations[largest_city]
        logging.info(f"Multiple populations found for '{original_city_string}, {original_country}': {populations}. Using max pop {max_pop} from '{largest_city}'.")
        return max_pop

def _city_population_worker(city_country_pair: Tuple[str, str]) -> Tuple[Tuple[str, str], Optional[int]]:
    """Worker function for parallel population fetching."""
    city, country = city_country_pair
    try:
        population = handle_compound_city(city, country)
        return (city_country_pair, population)
    except Exception as e:
        logging.error(f"Unhandled exception in population worker for {city_country_pair}: {e}")
        return (city_country_pair, None) # Return None on unexpected worker error

def enrich_museums_with_city_population(museums_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a 'population' column to the museum DataFrame using parallel processing.

    Args:
        museums_df: DataFrame containing cleaned museum data with 'city' and 'country' columns.

    Returns:
        DataFrame with an added 'population' column. Values can be integers,
pd.NA (if lookup failed), or potentially FetchFailureReason codes initially.
    """
    if 'city' not in museums_df.columns or 'country' not in museums_df.columns:
        logging.error("Missing 'city' or 'country' column. Cannot enrich with population.")
        museums_df['population'] = pd.NA # Add column but mark as Not Available
        return museums_df

    # Get unique city-country pairs as tuples, handling potential NaN values
    # Convert to list of tuples directly
    city_country_pairs = [tuple(x) for x in museums_df[['city', 'country']].dropna().drop_duplicates().values]
    logging.info(f"Fetching population data for {len(city_country_pairs)} unique city-country pairs using up to {config.MAX_POPULATION_WORKERS} workers.")

    populations_map = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_POPULATION_WORKERS) as executor:
        # Ensure pairs submitted are tuples
        future_to_pair = {executor.submit(_city_population_worker, pair): pair for pair in city_country_pairs}

        completed = 0
        total = len(future_to_pair)
        for future in concurrent.futures.as_completed(future_to_pair):
            completed += 1
            pair = future_to_pair[future] # pair is now a tuple
            try:
                pair_result, population_result = future.result()
                # Ensure pair_result is a tuple if the worker function didn't guarantee it
                if isinstance(pair_result, list):
                    pair_result = tuple(pair_result)
                populations_map[pair_result] = population_result
                # Log specific failures immediately
                if isinstance(population_result, FetchFailureReason):
                    logging.warning(f"Population lookup for {pair_result} failed with reason: {population_result.name}")
                elif population_result is None:
                     logging.error(f"Population lookup for {pair_result} returned None unexpectedly.")

            except Exception as exc:
                logging.error(f'Worker for {pair} generated an exception: {exc}')
                 # Ensure pair is a tuple for the key here as well
                populations_map[pair] = None # Mark as None on worker exception

            if completed % 10 == 0 or completed == total:
                logging.info(f"Processed {completed}/{total} city populations...")

    # Map populations back to the main DataFrame
    def get_population(row):
        if pd.isna(row.get('city')) or pd.isna(row.get('country')):
            return pd.NA
        # Key should be a tuple
        return populations_map.get(tuple([row['city'], row['country']]), pd.NA) # Ensure tuple lookup

    museums_df['population'] = museums_df.apply(get_population, axis=1)

    # Log summary of the enrichment
    pop_col = museums_df['population']
    total_rows = len(museums_df)
    valid_pop_count = pop_col.apply(lambda x: isinstance(x, (int, float)) and pd.notna(x) and x >= 0).sum()
    failed_lookups = pop_col.apply(lambda x: isinstance(x, FetchFailureReason)).sum()
    na_values = pop_col.isna().sum()

    logging.info(f"Population enrichment complete. Total museums processed: {total_rows}")
    logging.info(f"- Museums with valid population data: {valid_pop_count}")
    logging.info(f"- Museums where population lookup failed (specific reason recorded): {failed_lookups}")
    logging.info(f"- Museums with population marked NA (lookup error or missing key): {na_values}")

    # Optionally replace FetchFailureReason codes with pd.NA for cleaner output/storage
    museums_df['population'] = museums_df['population'].apply(lambda x: pd.NA if isinstance(x, FetchFailureReason) else x)

    # Log cities associated with NA values after replacement
    missing_cities_df = museums_df[museums_df['population'].isna()][['city', 'country']].drop_duplicates()
    if not missing_cities_df.empty:
        logging.warning(f"Cities with missing population data after enrichment ({len(missing_cities_df)} unique pairs):")
        for _, row in missing_cities_df.iterrows():
            logging.warning(f"  - {row['city']}, {row['country']}")

    return museums_df 
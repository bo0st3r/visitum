from enum import Enum
import requests
import pandas as pd
from io import StringIO
import logging
import re
import time
import geocoder
import concurrent.futures
from typing import Optional

# Define the Wikipedia page title and API endpoint
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
MUSEUMS_VISITORS_WIKIPEDIA_PAGE_TITLE = "List_of_most_visited_museums"
MUSEUMS_VISITORS_MATCH_PATTERN = "Visitors in 2024"
OUTPUT_FILENAME = 'enriched_museum_data.csv'

# Maximum parallel workers for fetching city data
MAX_WORKERS = 8
MAX_RETRIES = 3  # Maximum number of retries for geocoder API

class FetchFailureReason(Enum):
    NO_DATA_FOR_CITY = -1
    FETCH_ERROR = -2
    NO_DATA_FOR_COMPOUND_CITY = -3

def get_wikipedia_museum_visitors_page_html(page_title: str) -> str | None:
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
        "User-Agent": "visitum | bastiendct@gmail.com"
    }

    logging.info(f"Requesting HTML for page: {page_title}")
    try:
        response = requests.get(WIKIPEDIA_API_URL, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        if "parse" in data and "text" in data["parse"] and "*" in data["parse"]["text"]:
            html_content = data["parse"]["text"]["*"]
            logging.info(f"Successfully retrieved HTML for {page_title}")
            return html_content
        else:
            logging.error(f"Could not find parsed text in API response for {page_title}")
            logging.debug(f"API Response: {data}")
            return None

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None

def extract_museum_visitors_table_from_html(html_content: str) -> pd.DataFrame | None:
    """
    Extracts the main museum table from HTML content using pandas.read_html.

    Args:
        html_content: The HTML string containing the tables.

    Returns:
        A pandas DataFrame representing the museum table, or None if not found.
    """
    if not html_content:
        return None

    try:
        # Using StringIO to help pandas read the HTML content
        html_io = StringIO(html_content)
        list_of_dataframes = []

        # Attempt 1: Match specific table header
        try:
            logging.info(f"Attempting to extract table matching header pattern: '{MUSEUMS_VISITORS_MATCH_PATTERN}'")
            # pandas.read_html returns a list of all tables found
            # The 'match' argument uses regex and searches within the table's content (including headers).
            list_of_dataframes = pd.read_html(html_io, match=MUSEUMS_VISITORS_MATCH_PATTERN)
            logging.info(f"Successfully found table using match='{MUSEUMS_VISITORS_MATCH_PATTERN}'.")

        except ValueError:
            logging.warning(f"Could not find table matching '{MUSEUMS_VISITORS_MATCH_PATTERN}'. Trying fallback.")
            list_of_dataframes = []

        # Attempt 2: Fallback - Read all tables and select largest
        if not list_of_dataframes:
            try:
                logging.info("Fallback: Reading all tables from HTML.")
                # Go back to the beginning of the html_io just in case
                html_io.seek(0)
                all_dataframes = pd.read_html(html_io)

                if all_dataframes:
                     # Heuristic: Assume the largest table is the most likely candidate
                     museum_df = max(all_dataframes, key=lambda df: df.size)
                     list_of_dataframes = [museum_df]
                     logging.info(f"Fallback successful. Selected largest table with shape: {museum_df.shape}")
                else:
                     logging.error("Fallback failed: No tables found in the HTML content at all.")
                     return None

            except Exception as e:
                logging.error(f"Error during fallback table extraction: {e}")
                return None

        # Process the found table (either from match or fallback)
        if list_of_dataframes:
            museum_df = list_of_dataframes[0]
            logging.info(f"Processing extracted table with shape: {museum_df.shape}")
            museum_df.columns = [str(col).strip().replace(' ', '_') for col in museum_df.columns]

            expected_cols = ['Name', 'Visitors', 'City', 'Country']
            if not all(any(expected.lower() in col.lower() for col in museum_df.columns) for expected in expected_cols):
                 logging.warning(f"Extracted table might not be the correct one. Columns: {museum_df.columns.tolist()}")
                 return None

            return museum_df
        else:
            logging.error("Extraction failed: No DataFrame was selected after attempts.")
            return None

    except Exception as e:
        # Catch any other unexpected errors during the process
        logging.error(f"An unexpected error occurred during table extraction: {e}")
        return None

def clean_museum_data(df):
    # Create a copy to avoid modifying original
    cleaned_df = df.copy()

    # Function to extract visitor count and year
    def _extract_visitor_info(value_str):
        try:
            value_str = str(value_str) # Ensure it's a string
            # Remove citation references like [1], [2], etc.
            value_str = re.sub(r'\[\d+\]', '', value_str).strip()

            # Extract year if present (e.g., (2023)), Default to 2024 if no year found as this is how the data is formatted
            year_match = re.search(r'\((\d{4})\)', value_str)
            year = int(year_match.group(1)) if year_match else 2024

            # Extract the visitor count number
            count_match = re.search(r'([\d,\.]+)', value_str)
            if count_match:
                num_str = count_match.group(1).replace(',', '')
                count = float(num_str)
                # Check for 'million' keyword
                if 'million' in value_str.lower(): #TODO: other keywords to handle? not for now at least but we could be proactive.
                    count *= 1_000_000
                return int(count), year # Return count as int for clarity, and year
            return None, year # Return None for count if not found
        except Exception as e:
            logging.warning(f"Could not parse visitor info from '{value_str}': {e}")
            return None, None

    # Determine the correct visitor column name
    # It might be 'Visitors_in_2024' or similar based on initial extraction
    visitor_col = None
    for col in cleaned_df.columns:
        if 'visitors' in col.lower() and ('2024' in col.lower() or 'year' in col.lower() or col.lower() == 'visitors'): # Adjust search criteria as needed
            visitor_col = col
            break

    if not visitor_col:
         logging.error("Could not identify the visitor count column.")
         # Try a common fallback if the specific column name check fails
         if 'Visitors' in cleaned_df.columns:
             visitor_col = 'Visitors'
             logging.warning("Using fallback 'Visitors' column.")
         else:
            # If still not found, return None or raise an error
            return None # Or raise ValueError("Visitor column not found")


    logging.info(f"Using column '{visitor_col}' for visitor data.")

    # Apply the extraction function to create new columns
    visitor_data = cleaned_df[visitor_col].apply(_extract_visitor_info)
    cleaned_df['Visitors_Count'] = visitor_data.apply(lambda x: x[0] if x else None)
    cleaned_df['Visitors_Year'] = visitor_data.apply(lambda x: x[1] if x else None)

    # Drop rows where visitor count couldn't be parsed
    cleaned_df = cleaned_df.dropna(subset=['Visitors_Count'])
    # Convert count to integer type now that NaNs are dropped
    cleaned_df['Visitors_Count'] = cleaned_df['Visitors_Count'].astype(int)
    cleaned_df['Visitors_Year'] = cleaned_df['Visitors_Year'].astype(int)
    
    # Filtering
    logging.info(f"Total rows before year filtering: {len(cleaned_df)}")
    # 1. Filter for entries specifically from the year 2024
    cleaned_df = cleaned_df[cleaned_df['Visitors_Year'] == 2024].copy() # Use .copy() to avoid SettingWithCopyWarning
    logging.info(f"Rows after filtering for Year == 2024: {len(cleaned_df)}")

    # 2. Filter for museums with more than 1,250,000 visitors in 2024
    cleaned_df = cleaned_df[cleaned_df['Visitors_Count'] > 1_250_000].copy()
    logging.info(f"Rows after filtering for Visitors > 1,250,000: {len(cleaned_df)}")

    # Final Column Selection and Renaming
    # Keep only relevant columns and rename for clarity
    # Ensure 'Country' column exists or handle potential absence
    final_cols = ['Name', 'City','Country', 'Visitors_Count', 'Visitors_Year']

    # Select only the columns that actually exist in the dataframe
    existing_final_cols = [col for col in final_cols if col in cleaned_df.columns]
    cleaned_df = cleaned_df[existing_final_cols]

    # Clean up any citation references in city names (ensure 'City' column exists)
    if 'City' in cleaned_df.columns:
        cleaned_df['City'] = cleaned_df['City'].astype(str).str.replace(r'\[\d+\]', '', regex=True).str.strip()
    else:
        logging.warning("Column 'City' not found for final cleaning.")

    return cleaned_df

def fetch_city_population_with_geocoder(city: str, country: str) -> Optional[int]:
    """
    Fetch city population using the geocoder library.
    
    Args:
        city: City name
        country: Country name
    
    Returns:
        Population as integer or None if not found
    """
    for attempt in range(MAX_RETRIES):
        try:
            # Geonames is the only provider that has population data, but it's usually the city proper population
            # The metropolitan area population is a better proxy for the number of people that will visit the museums so.
            # consult """https://geocoder.readthedocs.io/search.html?q=population&check_keywords=yes&area=default""" to see if more providers have population data
            # TODO: use a provider that reliably has the metropolitan area population
            # TODO: get population by museum's coordinates rather than city, country (could possibly allow for more reliable results and less city-specific code?)
            g = geocoder.geonames(f"{city}, {country}", key='visitum')
            if g.ok:
                # Some providers have population data, some don't
                if hasattr(g, 'population') and g.population:
                    pop = int(g.population)
                    return pop
                else:
                    logging.warning(f"No population data for {city}, {country}")
                    return FetchFailureReason.NO_DATA_FOR_CITY
            time.sleep(1)
            
        except Exception as e:
            logging.error(f"Error on attempt {attempt+1} for {city}, {country}: {str(e)}")
            time.sleep(1)
    
    logging.warning(f"Could not get population data for {city}, {country} after {MAX_RETRIES} attempts. Returning specific indicator.")
    return FetchFailureReason.FETCH_ERROR

def handle_compound_city(city_string: str, country: str) -> Optional[int]:
    """
    Handle compound city entries like "Vatican City, Rome" or "London, South Kensington" by fetching and combining populations
    
    Args:
        city_string: String with potentially multiple cities separated by commas
        country: Country name
        
    Returns:
        Combined population or population of the largest city
    """
    
    # Special case handling for 'Vatican City, Rome', 'London, South Kensington', and other cities separated by commas
    # TODO: find a reusable way to account for edge cases, and store the conditions and their corresponding transformations in the database/csv file/config file
    # TODO: look into other edge cases that aren't in the dataset (wikipedia page) yet but might eventually be added (San Marino, Monaco, etc.)
    if 'vatican' in city_string.lower() and 'vatican' in country.lower():
        logging.info(f"Special case: {city_string} in {country} - treating as Rome, Italy for population purposes")
        city_string = "Rome"
        country = "Italy"
    elif 'london' in city_string.lower() and 'south kensington' in city_string.lower():
        logging.info(f"Special case: {city_string} in {country} - treating as London, UK for population purposes")
        city_string = "London"
        country = "United Kingdom"
        
    cities = [city.strip() for city in city_string.split(',')] # For cases we don't handle above, split on commas to get the different cities
    
    if len(cities) == 1:
        # Single city, just fetch its population
        return fetch_city_population_with_geocoder(cities[0], country)
    
    # If we have multiple cities, fetch population for each
    populations = []
    for city in cities:
        pop = fetch_city_population_with_geocoder(city, country)
        if not isinstance(pop, FetchFailureReason):
            populations.append(pop)
        else:
            logging.warning(f"Could not retrieve valid population for {city}, {country} due to {pop}.")

    if not populations:
        logging.warning(f"Could not retrieve valid population for any part of '{city_string}, {country}'.")
        return FetchFailureReason.NO_DATA_FOR_COMPOUND_CITY
    elif len(populations) == 1:
        # If we only found one city's population, return it
        return populations[0]
    else:
        # For multiple cities, return the largest as the metropolitan area population
        # This is better than summing, as cities in the same metro area would double-count
        return max(populations)

def city_population_worker(city_country_pair):
    """Process a city-country pair for parallel execution"""
    city, country = city_country_pair
    population = handle_compound_city(city, country)
    return ((city, country), population)

def enrich_museums_with_city_population(museums_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add metropolitan population data to the museum DataFrame using parallel processing.
    
    Args:
        museums_df: DataFrame containing clean museum data
        
    Returns:
        DataFrame with added Population column
    """
    # Get unique city-country pairs
    # Ensure 'City' and 'Country' columns exist
    if 'City' not in museums_df.columns or 'Country' not in museums_df.columns:
        logging.error("Missing 'City' or 'Country' column for population enrichment.")
        museums_df['Population'] = None
        return museums_df

    city_country_pairs = museums_df[['City', 'Country']].drop_duplicates().values.tolist()
    logging.info(f"Getting population data for {len(city_country_pairs)} unique city-country pairs")
    # city_country_pairs = [pair for pair in city_country_pairs if 'vatican' in pair[0].lower()]

    populations = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_city = {
            executor.submit(city_population_worker, city_country): city_country
            for city_country in city_country_pairs
        }

        completed = 0
        total = len(future_to_city)

        for future in concurrent.futures.as_completed(future_to_city):
            completed += 1
            city_country = future_to_city[future]
            city, country = city_country 

            try:
                _, population = future.result()
                populations[(city, country)] = population
                
                if population is None:
                     logging.warning(f"Population lookup returned None for {city}, {country}.")
                elif isinstance(population, FetchFailureReason):
                     logging.warning(f"Could not retrieve valid population for any part of {city}, {country} because of {population}.")

            except Exception as exc:
                logging.error(f'Generating population for {city}, {country} generated an exception: {exc}')
                populations[(city, country)] = None

            # Log progress periodically or based on completion percentage
            if completed % 10 == 0 or completed == total: 
                logging.info(f"Processed {completed}/{total} city populations...")


    # Map populations back to the main DataFrame
    def get_population(row):
        if pd.isna(row.get('City')) or pd.isna(row.get('Country')):
             return None
        return populations.get((row['City'], row['Country']), None)

    museums_df['Population'] = museums_df.apply(get_population, axis=1)

    # Log summary of the enrichment
    # Count specific failure codes and actual missing values (None)
    pop_col = museums_df['Population']
    total_rows = len(museums_df)
    valid_pop_count = pop_col.apply(lambda x: isinstance(x, (int, float)) and x >= 0).sum()
    no_data_for_city_count = (pop_col == FetchFailureReason.NO_DATA_FOR_CITY).sum()
    fetch_failed_count = (pop_col == FetchFailureReason.FETCH_ERROR).sum()
    no_data_for_compound_city_count = (pop_col == FetchFailureReason.NO_DATA_FOR_COMPOUND_CITY).sum()
    none_count = pop_col.isna().sum()

    logging.info(f"Population enrichment complete. Total museums processed: {total_rows}")
    logging.info(f"- Museums with valid population data: {valid_pop_count}")
    logging.info(f"- Museums where city was found but no population data available: {no_data_for_city_count}")
    logging.info(f"- Museums where population fetch failed after retries: {fetch_failed_count}")
    logging.info(f"- Museums where population lookup failed for any part of the city, country pair: {no_data_for_compound_city_count}")
    logging.info(f"- Museums with population marked as None (errors/missing keys): {none_count}")

    museums_df['Population'] = museums_df['Population'].replace([-1, -2, -3], pd.NA)

    # Log cities associated with failures/missing data
    missing_cities_df = museums_df[pop_col.isna() | (pop_col < 0)][['City', 'Country', 'Population']].drop_duplicates()
    if not missing_cities_df.empty:
        logging.warning("Cities with missing or failed population lookups:")
        for _, row in missing_cities_df.iterrows():
             status = row['Population']
             status_desc = "None/Error" if pd.isna(status) else ("No Data Available" if status == -1 else "Fetch Failed")
             logging.warning(f"  - {row['City']}, {row['Country']} (Status: {status_desc})")

    return museums_df

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger("geocoder").setLevel(logging.WARNING)

    logging.info("Starting Museum Data Processing")

    # 1. Get Wikipedia page content
    html = get_wikipedia_museum_visitors_page_html(MUSEUMS_VISITORS_WIKIPEDIA_PAGE_TITLE)

    if not html:
        logging.error("Failed to retrieve Wikipedia content. Exiting.")
        exit(1)

    # 2. Extract museum data table
    museum_data = extract_museum_visitors_table_from_html(html)

    if museum_data is None:
        logging.error("Failed to extract museum data table. Exiting.")
        exit(1)

    logging.info("Museum data extracted successfully.")
    logging.info(f"Extracted Table Columns: {museum_data.columns.tolist()}")
    logging.info(f"Extracted Table Head:\n{museum_data.head().to_string()}")

    # 3. Clean and filter museums
    logging.info("Cleaning museum data...")
    cleaned_museum_data = clean_museum_data(museum_data)

    if cleaned_museum_data is None or cleaned_museum_data.empty:
        logging.warning("No museums remained after cleaning and filtering. No data to enrich or save. Exiting.")
        exit(1)
        
    logging.info(f"After cleaning: {cleaned_museum_data.shape[0]} museums remaining.")

    # 4. Add city population data
    logging.info("Adding city population data...")
    enriched_museum_data = enrich_museums_with_city_population(cleaned_museum_data)

    # 5. Log results
    logging.info("Final Enriched Museum Data Head:\n" + enriched_museum_data.head().to_string())

    # 6. Save to CSV
    try:
        enriched_museum_data.to_csv(OUTPUT_FILENAME, index=False)
        logging.info(f"Successfully saved data to {OUTPUT_FILENAME}")
    except Exception as e:
        logging.error(f"Failed to save data to CSV: {e}")


    logging.info("Museum Data Processing Complete")

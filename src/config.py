"""Configuration settings for the Visitum project."""

import logging

# Wikipedia Data Fetching
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
MUSEUMS_VISITORS_WIKIPEDIA_PAGE_TITLE = "List_of_most_visited_museums"
MUSEUMS_VISITORS_MATCH_PATTERN = "Visitors in 2024"
WIKIPEDIA_USER_AGENT = "visitum | bastiendct@gmail.com" # Be polite to Wikipedia's API

# Geocoding / Population Data
# Geonames username required for the geocoder library
GEONAMES_USERNAME = 'visitum' # Replace with your actual Geonames username if needed
MAX_GEOCODER_RETRIES = 3
GEOCODER_RETRY_DELAY_SECONDS = 1 # Delay between retries

# Parallel Processing
MAX_POPULATION_WORKERS = 8

# Output
OUTPUT_FILENAME = 'data/enriched_museum_data.csv' # For the initial exploration script output

# Logging Configuration
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Database (Placeholder for later)
DATABASE_URL = "sqlite:///./visitum_data.db" 
"""Configuration settings for the Visitum project."""

import logging
import os

#TODO: put these in an environment variable

# Wikipedia Data Fetching
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
MUSEUMS_VISITORS_WIKIPEDIA_PAGE_TITLE = "List_of_most_visited_museums"
MUSEUMS_VISITORS_MATCH_PATTERN = "Visitors in 2024"

# Geocoding / Population Data
# Geonames username required for the geocoder library
MAX_GEOCODER_RETRIES = 3
GEOCODER_RETRY_DELAY_SECONDS = 1  # Delay between retries

# Parallel Processing For Population Data Extraction
MAX_POPULATION_WORKERS = 8

# Logging Configuration
#TODO: have a global logger with this config and use it instead of directly calling the logging module
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Project Paths
# Define project root assuming this config file is in src/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Database configuration
# Use an absolute path derived from the project root
DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT, 'data/visitum.db')}"

# Data file paths
# Derive data paths from project root
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
ENRICHED_DATA_CSV = os.path.join(DATA_DIR, "enriched_museum_data.csv")
OUTPUT_FILENAME = ENRICHED_DATA_CSV

# Model file paths
MODEL_FILENAME = "trained_regression_model.joblib"
MODEL_SAVE_PATH = os.path.join(DATA_DIR, MODEL_FILENAME)

# Wikipedia settings
WIKIPEDIA_PAGE_TITLE = "List_of_most_visited_museums"
WIKIPEDIA_VISITORS_COLUMN = "Visitors in 2024"

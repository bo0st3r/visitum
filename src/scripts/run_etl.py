import logging
import pandas as pd
import sys
import os # Import os to construct the output path relative to the project root

# Imports assuming src is the top-level package directory
import config 
from data.extraction import (
    get_wikipedia_museum_visitors_page_html,
    extract_museum_visitors_table_from_html
)
from data.transformation import (
    clean_museum_data,
    enrich_museums_with_city_population
)

def setup_logging():
    """Configures logging for the script."""
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format=config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout) # Log to stdout
        ]
    )
    # Set geocoder library logging level higher to avoid excessive noise
    logging.getLogger("geocoder").setLevel(logging.WARNING)
    # Set urllib3 logging level higher as well
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def main():
    """Main ETL execution flow."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Museum Data ETL Process")

    # 1. Get Wikipedia page content
    logger.info(f"Fetching Wikipedia page: {config.MUSEUMS_VISITORS_WIKIPEDIA_PAGE_TITLE}")
    html = get_wikipedia_museum_visitors_page_html(config.MUSEUMS_VISITORS_WIKIPEDIA_PAGE_TITLE)
    if not html:
        logger.error("Failed to retrieve Wikipedia content. Exiting.")
        sys.exit(1)

    # 2. Extract museum data table
    logger.info("Extracting museum data table from HTML...")
    raw_museum_data = extract_museum_visitors_table_from_html(html)
    if raw_museum_data is None or raw_museum_data.empty:
        logger.error("Failed to extract or empty museum data table. Exiting.")
        sys.exit(1)

    logger.info(f"Successfully extracted table. Shape: {raw_museum_data.shape}")
    logger.debug(f"Extracted Table Columns: {raw_museum_data.columns.tolist()}")
    logger.debug(f"Extracted Table Head:\n{raw_museum_data.head().to_string()}")

    # 3. Clean and filter museum data
    logger.info("Cleaning and filtering museum data...")
    cleaned_museum_data = clean_museum_data(raw_museum_data)

    if cleaned_museum_data is None:
        logger.error("Data cleaning failed critically. Exiting.")
        sys.exit(1)
    if cleaned_museum_data.empty:
        logger.warning("No museums remained after cleaning and filtering. Process finished.")
        sys.exit(0) # Exit normally, but indicate no data was processed further

    logger.info(f"Data cleaning finished. {cleaned_museum_data.shape[0]} museums remaining.")
    logger.debug(f"Cleaned data head:\n{cleaned_museum_data.head().to_string()}")

    # 4. Enrich with city population data
    logger.info("Enriching museum data with city population...")
    enriched_museum_data = enrich_museums_with_city_population(cleaned_museum_data)

    # Log final results preview
    logger.info(f"Enrichment complete. Final DataFrame shape: {enriched_museum_data.shape}")
    logger.info("Final Enriched Museum Data Head (with Population):\n" +
                enriched_museum_data.head().to_string())

    # Check for museums completely missing population data
    missing_pop_count = enriched_museum_data['population'].isna().sum()
    if missing_pop_count > 0:
        logger.warning(f"{missing_pop_count} museums have missing population data in the final dataset.")

    # 5. Save to CSV
    # Construct path relative to project root (assuming script is run from project root)
    # Project root is one level up from the src directory where this script resides
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    output_path = os.path.join(project_root, config.OUTPUT_FILENAME)

    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True) # Creates the directory if it doesn't exist, does nothing if it does

        enriched_museum_data.to_csv(output_path, index=False)
        logger.info(f"Successfully saved enriched data to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save data to CSV at {output_path}: {e}")
        sys.exit(1)

    logger.info("Museum Data ETL Process Completed Successfully")

if __name__ == "__main__":
    main() 
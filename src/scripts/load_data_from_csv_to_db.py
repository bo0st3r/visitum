"""
This script handles the loading of processed data from a CSV file into the database.
It defines functions to:
- Read data from a specified CSV file.
- Populate the 'cities' and 'museums' tables in the database.
- Implements a caching mechanism for city entries to optimize database operations and avoid redundant queries.
- Ensures data integrity by checking for existing museum entries before insertion.

The main execution block initializes the database and invokes the data loading process.
"""
import pandas as pd
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from db.database import get_db, init_db
from db.models import City, Museum, Base
import config

def load_data_from_csv(db: Session, csv_path: str):
    """Loads museum and city data from a CSV file into the database."""
    logging.info(f"Loading data from {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        logging.error(f"Error: CSV file not found at {csv_path}")
        return
    except Exception as e:
        logging.error(f"Error reading CSV file: {e}")
        return

    cities_cache = {} # Cache to store city objects
    museums_added = 0
    cities_added = 0

    for _, row in df.iterrows():
        city_name = row['city']
        country_name = row['country']
        population = row.get('population')
        museum_name = row['name']
        visitors_count = row['visitors_count']
        visitors_year = row['visitors_year']

        db_population = int(population) if pd.notna(population) else None

        city_key = (city_name, country_name)
        db_city = cities_cache.get(city_key)

        # Insert city if it doesn't exist and cache it, otherwise use cached city
        if not db_city:
            db_city = db.query(City).filter_by(name=city_name, country=country_name).first()
            if not db_city:
                try:
                    db_city = City(name=city_name, country=country_name, population=db_population)
                    db.add(db_city)
                    db.flush() # Assign ID
                    cities_added += 1
                    logging.debug(f"Created new city: {city_name}, {country_name}")
                except IntegrityError: # Should be rare if filter_by is effective
                    db.rollback()
                    logging.warning(f"Integrity error for city {city_name}, {country_name}. Fetching again.")
                    db_city = db.query(City).filter_by(name=city_name, country=country_name).first()
                    if not db_city:
                        logging.error(f"Failed to create or find city {city_name}, {country_name} after integrity error.")
                        continue
                except Exception as e:
                    db.rollback()
                    logging.error(f"Error creating city {city_name}, {country_name}: {e}")
                    continue
            cities_cache[city_key] = db_city
        
        if not db_city or not db_city.id:
            logging.warning(f"Skipping museum '{museum_name}' as city '{city_name}' could not be processed.")
            continue

        # Check if museum already exists
        existing_museum = db.query(Museum).filter_by(
            name=museum_name,
            visitors_year=visitors_year,
            city_id=db_city.id
        ).first()

        if existing_museum:
            logging.debug(f"Museum '{museum_name}' for year {visitors_year} in city '{city_name}' already exists. Skipping.")
            continue
        
        try:
            db_museum = Museum(
                name=museum_name,
                visitors_count=int(visitors_count),
                visitors_year=int(visitors_year),
                city_id=db_city.id
            )
            db.add(db_museum)
            museums_added += 1
        except Exception as e: # Catch potential errors during museum creation/add
            logging.error(f"Error creating or adding museum {museum_name}: {e}")
            # Potentially rollback this specific museum addition if needed, or skip
            continue


    try:
        db.commit()
        logging.info(f"Successfully committed data: {cities_added} new cities, {museums_added} new museums.")
    except Exception as e:
        db.rollback()
        logging.error(f"Failed to commit transaction: {e}")

def main():
    init_db()
    
    with get_db() as db:
        load_data_from_csv(db, config.ENRICHED_DATA_CSV)
    logging.info("Database session closed.")

# Keep this pattern for executable scripts
if __name__ == "__main__":
    main() 
"""Database query functions."""
import logging
import pandas as pd
from sqlalchemy.orm import Session, joinedload

from .models import Museum, City

logger = logging.getLogger(__name__)

def get_museums_with_city_population(db: Session) -> list[tuple[str, int, str | None, int | None]]:
    """
    Fetches all museums along with their associated city's name and population.

    Args:
        db: The database session.

    Returns:
        A list of tuples, where each tuple contains:
        (museum_name, museum_visitors_count, city_name, city_population).
        Returns an empty list if no museums are found or in case of an error.
    """
    try:
        results = (
            db.query(
                Museum.name,
                Museum.visitors_count,
                City.name,
                City.population
            )
            .join(City, Museum.city_id == City.id)
            .all()
        )
        
        logging.info(f"Fetched {len(results)} museums with city population data.")
        
        # Type hint expects specific tuple structure
        # Ensure the query results match the return type hint. 
        # SQLAlchemy query results for specific columns are often tuples.
        # Let's cast just to be safe, although direct selection usually returns tuples.
        typed_results: list[tuple[str, int, str | None, int | None]] = [
             (str(m_name), int(m_visitors), str(c_name) if c_name else None, int(c_pop) if c_pop is not None else None) 
             for m_name, m_visitors, c_name, c_pop in results
        ]

        return typed_results

    except Exception as e:
        logging.error(f"Error fetching museum and city data: {e}", exc_info=True)
        return []

def fetch_model_features(db: Session) -> pd.DataFrame:
    """
    Fetches features required for the regression model (city population and museum visitors).

    Args:
        db: The database session.

    Returns:
        A Pandas DataFrame with 'population' and 'visitors_count' columns.
        Filters out entries where city population is NULL.
        Returns an empty DataFrame in case of errors or no data.
    """
    logging.info("Fetching features for model training (population vs visitors).")
    try:
        query = (
            db.query(
                City.population.label('population'), # setting alias for column
                Museum.visitors_count.label('visitors_count') # setting alias for column
            )
            .join(City, Museum.city_id == City.id)
            .filter(City.population.isnot(None)) # Ensure population is not null
            .filter(Museum.visitors_count.isnot(None)) # Ensure visitors_count is not null (implicitly done by schema, but good practice)
        )
        
        df = pd.read_sql(query.statement, db.bind) #TODO: possibly need to use chunks/pagination? this probably loads it all into memory and might be a problem for larger datasets

        if df.empty:
            logging.warning("No valid data found for model training (check population data).")
        else:
            logging.info(f"Successfully fetched {len(df)} records for model training.")
            
        return df

    except Exception as e:
        logging.error(f"Error fetching model features: {e}", exc_info=True)
        return pd.DataFrame() # Return empty DataFrame on error

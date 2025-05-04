# visitum

The backbone of the estimator of visitors for museums in a city using linear regression with Python.

## Mission

Build and containerize a Python application that extracts museum visitor data (Wikipedia) and city population data, stores it, trains a simple linear regression model (`visitor_count ~ city_population`), and exposes insights via a Jupyter notebook. This serves as an MVP for correlating museum attendance with city size for a new world organization.

## Assignment clarifications

- **Visitor Count**: the initial assignment description said to focus on museums with >2 million visitors, but the source seems to have changed since the creation of this assignment and now lists museums with 1.25 million visitors and more. After asking Simon for clarification, it was said that "Fine to explore or just to make a judgement call here". I went with >1.25 million visitors because it allows more variety in the dataset which is already quite small.
- **Visitor Year**: the source also says that the data is for the year 2024, however for some entities the year is 2023 or even 2022. After asking Simon for clarification, it was said to use the year 2024 only, therefore remove some entities from the dataset.
- **Regression Input**: being unsure of the expected model input: (1) Museum Visitors or (2) Total Museum Visitors For The City, I asked for clarification and was told "would go for something simpler that fits in the time and keep the broader for discussion". I went with option 1 which is simpler and probably more relevant for the end goal.

## Implementation Status

### Current Implementation

The project currently implements the Extract and Transform (ET) phases of the data pipeline within the `src/visitum/data` package. 

Key components include:
*   **`extraction.py`**: Fetches raw museum data from Wikipedia and city population data using the `geocoder` library.
*   **`transformation.py`**: Cleans, filters (Year 2024, >1.25M visitors), and enriches the museum data with corresponding city populations, handling parallel processing and edge cases like compound city names.
*   **`config.py`**: Stores configuration parameters (API endpoints, filtering thresholds, etc.).
*   **`models.py`**: Defines data structures like `FetchFailureReason`.

A script (`etl_exploration.py`) orchestrates these modules, running the ET steps and saving the resulting DataFrame to a CSV file (`data/enriched_museum_data.csv`). The next phase involves loading this data into a database.

## ETL Pipeline

### Extraction

#### Museum Visitors Source

Museums with over 1,250,000 annual visitors [(Wikipedia)](https://en.wikipedia.org/wiki/List_of_most-visited_museums)

Logic resides in `src/visitum/data/extraction.py`:
- Uses `requests` and the MediaWiki API (`config.WIKIPEDIA_API_URL`) to fetch HTML.
- Uses `pandas.read_html` with matching (`config.MUSEUMS_VISITORS_MATCH_PATTERN`) and fallback logic to extract the table.

#### City Population Source

Logic resides in `src/visitum/data/extraction.py`:
- Uses the `geocoder` library with the `geonames` provider (`config.GEONAMES_USERNAME`).
- Implements retry logic (`config.MAX_GEOCODER_RETRIES`).
- Fetches city proper population.

**Improvement idea:** Metropolitan population is a better proxy, but Geonames primarily provides city proper data. Exploring alternative providers or data sources for metropolitan area population remains a future improvement.

**Special cases:** Handled in `src/visitum/data/transformation.py` (`handle_compound_city` function). Specific rules (e.g., Vatican City -> Rome) are currently hardcoded; moving these to config or a database lookup table would be more flexible. The general approach splits comma-separated city strings and uses the population of the largest identified part.

### Transformation

Logic resides in `src/visitum/data/transformation.py`:

- **Data Cleaning (`clean_museum_data`)**: Standardizes column names, parses/cleans visitor counts and years using regex, filters by year (2024) and visitor count (>1.25M), selects and renames final columns, cleans city name strings.
- **Data Enrichment (`enrich_museums_with_city_population`)**: Uses `concurrent.futures` to fetch population data in parallel for unique city/country pairs, maps results back to the DataFrame, handles fetch failures gracefully (logging and using `pd.NA`).

### Loading

- **Target**: A database (initially SQLite) to store the processed data, suitable for containerized deployment.
- **Module**: Logic resides in `src/visitum/data/loading.py`.
- **Process**: Takes the final DataFrame produced by the transformation step and inserts it into the database according to the defined schema.

## Project Structure

```
visitum/
│
├── .dockerignore
├── .gitignore
├── docker-compose.yml
├── Dockerfile           # Main application Dockerfile
├── Dockerfile.jupyter   # Jupyter notebook Dockerfile (if separate service)
├── README.md
├── requirements.txt     # Python dependencies
├── setup.py             # Packaging script (optional but good practice)
├── src/
│   ├── __init__.py
│   ├── config.py        # Configuration settings
│   ├── data/            # Data processing modules (ETL)
│   │   ├── __init__.py
│   │   ├── models.py      # Data enums/models (FetchFailureReason)
│   │   ├── extraction.py  # Data extraction logic (Wikipedia, Population)
│   │   ├── transformation.py # Data cleaning and transformation
│   │   └── loading.py     # Database loading logic
│   ├── db/              # Database interaction modules
│   │   ├── __init__.py
│   │   └── models.py    # Database models (e.g., SQLAlchemy)
│   │   └── operations.py # CRUD operations
│   ├── ml/              # Machine Learning modules
│   │   ├── __init__.py
│   │   ├── model.py     # Linear Regression model training/prediction
│   │   └── utils.py     # ML utilities
│   ├── api/             # API exposure (e.g., FastAPI)
│   │   ├── __init__.py
│   │   ├── main.py      # API entry point
│   │   └── endpoints.py # API routes
│   └── utils/           # Shared utilities
│       └── __init__.py
│
├── notebooks/
│   └── analysis.ipynb     # Jupyter notebook for visualization
│
└── tests/
    ├── __init__.py
    ├── conftest.py        # Pytest configuration
    ├── data/              # Tests for data modules
    ├── db/                # Tests for database modules
    ├── ml/                # Tests for ML modules
    └── api/               # Tests for API endpoints
```

## Technology Stack

- **Programming Language**: Python 3.11+
- **Museum Visitors Data Extraction**: `requests`, `pandas.read_html` (`src/visitum/data/extraction.py`)
- **City Population Data Extraction**: `geocoder` library (`src/visitum/data/extraction.py`)
- **Data Manipulation**: `Pandas` (`src/visitum/data/transformation.py`)
- **Data Storage**: CSV output (`etl_exploration.py`), Database (`SQLite` via `src/visitum/db`)
- **Configuration**: Python file (`src/visitum/config.py`)
- **ML Library**: `scikit-learn`
- **Containerization**: `Docker`, `Docker Compose`
- **Notebook Environment**: `JupyterLab` or `Jupyter Notebook`
- **Testing**: `pytest`

## Machine Learning Model

- **Algorithm**: Linear Regression (`scikit-learn.linear_model.LinearRegression`)
- **Features (X)**: City Metropolitan Population
- **Target (Y)**: Museum Visitor Count (for 2024, >1.25M)
- **Evaluation**: Standard regression metrics (e.g., R-squared, MAE, MSE). Visualizations in the Jupyter notebook.

## Setup & Usage

1.  **Prerequisites**: Docker and Docker Compose installed.
2.  **Build**: `docker-compose build`
3.  **Run**: `docker-compose up -d`
4.  **Access**:
    - API: `http://localhost:8000` (or configured port)
    - Jupyter Notebook: `http://localhost:8888` (or configured port)

## Testing Strategy

- **Unit Tests**: Test individual functions and classes (e.g., data extraction logic, transformation steps, database operations, API endpoint logic) using `pytest`. Mock external dependencies like API calls and database interactions.
- **Integration Tests**: Test the interaction between components (e.g., data extraction -> transformation -> loading). Potentially test against a test database instance.
- **End-to-End Tests**: Test the full flow (e.g., calling the API to trigger training/prediction, querying results).

## Design Choices & Future Considerations

- **Population Data Source**: Currently using geocoder with Geonames provider. This provides city proper populations but may not always reflect metropolitan areas accurately. Future improvements needed.
- **Scalability**:
  - **Database**: Implement proper database storage (SQLite for development, PostgreSQL for production)
  - **API**: Develop FastAPI endpoints to expose data and predictions
  - **ETL**: Refactor for better modularity and potentially use workflow orchestrators
- **ML Model Improvement**:
  - **More Features**: Incorporating additional features (e.g., museum type, city GDP, tourism statistics, plane tickets prices and arrivals, etc.) could improve model accuracy.
  - **Different Models**: Exploring other regression models (e.g., Polynomial Regression, Gradient Boosting) might yield better results.
  - **Regularization**: Apply regularization techniques if overfitting is observed.
- **Error Handling & Monitoring**: Implement comprehensive error handling, logging, and monitoring for production deployment.
- **CI/CD**: Set up a Continuous Integration/Continuous Deployment pipeline (e.g., using GitHub Actions, GitLab CI) to automate testing and deployment.
- **Museum Location Coordinates**: A significant improvement would be to use the museum's geographic coordinates to determine the appropriate city and metropolitan area. Currently, we match based on city name strings, which can be ambiguous. Using geocoder with the museum's coordinates would provide a more accurate association between museums and their metropolitan areas, leading to better population data and model accuracy.

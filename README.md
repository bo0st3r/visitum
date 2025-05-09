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

The project currently implements the Extract, Transform, and Load (ETL) phases of the data pipeline, along with initial model training.

Key components include:
*   **`extraction.py`** (`src/data/extraction.py`): Fetches raw museum data from Wikipedia and city population data using the `geocoder` library.
*   **`transformation.py`** (`src/data/transformation.py`): Cleans, filters (Year 2024, >1.25M visitors), and enriches the museum data with corresponding city populations.
*   **`config.py`** (`src/config.py`): Stores configuration parameters.
*   **`models.py`** (`src/data/models.py`): Defines data structures for the ET process.
*   **Database Loading**: The script `src/scripts/load_data_from_csv_to_db.py` loads the transformed data from `data/enriched_museum_data.csv` into an SQLite database (`data/visitum.db`).
*   **Model Training**: The script `src/scripts/train_model.py` trains a linear regression model using the data from the database and saves the model to `data/trained_regression_model.joblib`.

The ET steps are orchestrated by `src/scripts/run_etl.py`, which produces `data/enriched_museum_data.csv` and `data/visitum.db` as outputs. Subsequent scripts handle database loading and model training, which outputs `data/trained_regression_model.joblib`.

## ETL Pipeline

### Extraction

#### Museum Visitors Source

Museums with over 1,250,000 annual visitors [(Wikipedia)](https://en.wikipedia.org/wiki/List_of_most-visited_museums)

Logic resides in `src/data/extraction.py`:
- Uses `requests` and the MediaWiki API (`config.WIKIPEDIA_API_URL`) to fetch HTML.
- Uses `pandas.read_html` with matching (`config.MUSEUMS_VISITORS_MATCH_PATTERN`) and fallback logic to extract the table.

#### City Population Source

Logic resides in `src/data/extraction.py`:
- Uses the `geocoder` library with the `geonames` provider (it takes a `geonames` account to use the API).
- Implements retry logic (`config.MAX_GEOCODER_RETRIES`).
- Fetches city proper population.



**Special cases:** Handled in `src/data/transformation.py` (`handle_compound_city` function). Specific rules (e.g., Vatican City -> Rome) are currently hardcoded; moving these to config or a database lookup table would be more flexible. The general approach splits comma-separated city strings and uses the population of the largest identified part.

### Transformation

Logic resides in `src/data/transformation.py`:

- **Data Cleaning (`clean_museum_data`)**: Standardizes column names, parses/cleans visitor counts and years using regex, filters by year (2024) and visitor count (>1.25M), selects and renames final columns, cleans city name strings.
- **Data Enrichment (`enrich_museums_with_city_population`)**: Uses `concurrent.futures` to fetch population data in parallel for unique city/country pairs, maps results back to the DataFrame, handles fetch failures gracefully (logging and using `pd.NA`).

### Loading

- **Target**: A database (initially SQLite, e.g., `data/visitum.db`) to store the processed data.
- **Module**: Logic resides in `src/scripts/load_data_from_csv_to_db.py`.
- **Process**: Takes the final DataFrame produced by the transformation step (e.g., `data/enriched_museum_data.csv`) and inserts it into the database according to the defined schema.

## Project Structure

```
visitum/
│
├── .gitignore
├── .python-version
├── pyproject.toml       # Python package definition and dependencies
├── README.md
├── data/                # Output directory for generated data, models, and DB
│   ├── enriched_museum_data.csv
│   ├── visitum.db
│   └── ...              # Other generated files like model.joblib, plots
│
├── src/
│   ├── __init__.py
│   ├── config.py        # Configuration settings
│   ├── data/            # Data processing modules (ETL)
│   │   ├── __init__.py
│   │   ├── models.py      # Data enums/models (FetchFailureReason)
│   │   ├── extraction.py  # Data extraction logic (Wikipedia, Population)
│   │   └── transformation.py # Data cleaning and transformation
│   ├── db/              # Database interaction modules
│   │   ├── __init__.py
│   │   ├── database.py  # Database connection and session management
│   │   ├── models.py    # Database models (e.g., SQLAlchemy)
│   │   └── queries.py   # CRUD operations and data querying logic
│   ├── ml/              # Machine Learning modules
│   │   ├── __init__.py
│   │   ├── model.py     # Linear Regression model definition
│   │   └── training.py  # Model training and evaluation logic
│   └── scripts/         # Utility scripts for running pipeline stages
│       ├── __init__.py
│       ├── run_etl.py
│       ├── load_data_from_csv_to_db.py
│       ├── train_model.py
│
├── notebooks/
│   └── analysis.ipynb # Jupyter notebook for model evaluation and visualization of results
│   └── etl_and_training.ipynb # Jupyter notebook for exploration and visualization
│
├── .dockerignore        # (Planned for Dockerization)
├── docker-compose.yml   # (Planned for Dockerization)
├── Dockerfile           # (Planned for Dockerization)
├── Dockerfile.jupyter   # (Planned for Dockerization)
│
└── tests/               # (Planned: Pytest tests)
    ├── __init__.py
    ├── conftest.py
    ├── data/
    ├── db/
    └── ml/
```

## Technology Stack

- **Programming Language**: Python 3.11+
- **Dependency Management**: `pyproject.toml` (with PDM or Poetry implicitly, or setuptools)
- **Museum Visitors Data Extraction**: `requests`, `pandas.read_html` (`src/data/extraction.py`)
- **City Population Data Extraction**: `geocoder` library (`src/data/extraction.py`)
- **Data Manipulation**: `Pandas`, `Numpy` (`src/data/transformation.py`, `notebooks/`)
- **Data Storage**: CSV output (`data/enriched_museum_data.csv`), Database (`SQLite` via `src/db`, stored at `data/visitum.db`)
- **Configuration**: Python file (`src/config.py`)
- **ML Library**: `scikit-learn`
- **Containerization**: `Docker`, `Docker Compose`
- **Notebook Environment**: `JupyterLab` or `Jupyter Notebook`
- **Testing**: `pytest`

## Machine Learning Model

- **Algorithm**: Linear Regression (`scikit-learn.linear_model.LinearRegression`)
- **Features (X)**: City Metropolitan Population
- **Target (Y)**: Museum Visitor Count (for 2024, >1.25M)
- **Evaluation**: Standard regression metrics (e.g., R-squared, MAE, MSE). Visualizations in the Jupyter notebook (`notebooks/analysis.ipynb`). Initial results with simple linear regression indicate a weak correlation between city population and museum visitor count, suggesting that population alone is not a strong predictor and other factors or more complex models should be considered for better performance.

## Setup & Usage

(Note: Docker setup is planned. The following steps are for a future Dockerized version.)

1.  **Prerequisites**: Docker and Docker Compose installed.
2.  **Build**: `docker-compose build`
3.  **Run**: `docker-compose up -d`
4.  **Access**:
    - Jupyter Notebook: `http://localhost:8888` (or configured port)

Currently, to run the project, you would typically execute scripts from `src/scripts/` in sequence, after setting up your Python environment and installing dependencies from `pyproject.toml`.

## Testing Strategy

- **Unit Tests**: Test individual functions and classes (e.g., data extraction logic, transformation steps, database operations) using `pytest`. Mock external dependencies like API calls and database interactions.
- **Integration Tests**: Test the interaction between components (e.g., data extraction -> transformation -> loading -> training). Potentially test against a test database instance.

## Design Choices & Future Considerations

- **Population Data Source**: Currently using geocoder with Geonames provider. This provides city proper populations but may not always reflect metropolitan areas accurately. Future improvements needed.
- **Dependency Management**: The project uses `pyproject.toml` for managing dependencies. Adopting a specific tool like Poetry or PDM explicitly could further enhance dependency resolution and environment management.
- **Scalability**:
  - **Database**: Implement proper database storage (SQLite for development, PostgreSQL for production). The current SQLite DB is stored at `data/visitum.db`.
  - **Caching**: Cache the wikipedia results, geocoder results, the model, its predictions, etc.
  - **API (Future)**: As a future enhancement, develop FastAPI endpoints to expose data and predictions, with horizontal scaling in mind.
  - **ETL**: Refactor for better modularity and potentially use workflow orchestrators
- **ML Model Improvement**:
  - **More Features**: Incorporating additional features (e.g., museum type, city GDP, tourism statistics, plane tickets prices and arrivals, etc.) could improve model accuracy.
  - **Different Models**: Exploring other regression models (e.g., Polynomial Regression, Gradient Boosting) might yield better results.
  - **Regularization**: Apply regularization techniques if overfitting is observed.
- **Error Handling & Monitoring**: Implement comprehensive error handling, logging, and monitoring for production deployment.
- **CI/CD**: Set up a Continuous Integration/Continuous Deployment pipeline (e.g., using GitHub Actions, GitLab CI) to automate testing and deployment.
- **Museum Location Coordinates**: A significant improvement would be to use the museum's geographic coordinates to determine the appropriate city and metropolitan area. Currently, we match based on city name strings, which can be ambiguous. Using geocoder with the museum's coordinates would provide a more accurate association between museums and their metropolitan areas, leading to better population data and model accuracy.

## Future Improvements
- **City Population**:
  - Use the museum's geographic coordinates to determine the appropriate city and metropolitan area.
  - Metropolitan population is a better proxy, but Geonames primarily provides city proper data. Exploring alternative providers or data sources for metropolitan area population remains a future improvement.
- **Configuration**:
  - Move the configuration to a database/config file.
  - Use environment variables to configure the project, load them from a Secrets Manager for sensitive data and the rest through CI/CD pipeline.
- **Type Safety**:
  - Add typing to models such as Museum, City, etc for the Extraction and Transformation steps. Currently, the data is only typed for the Loading and ML steps.
- **Scaling**:
  - Use a more scalable database like PostgreSQL for production, possibly managed through a managed service like AWS RDS.
  - Use a more scalable ML service like AWS SageMaker for production.
  - Use a more scalable ETL service like AWS Glue for production.
  - **Data Ingestion/Processing**: For very large datasets, implement chunked/paginated data loading from the database to avoid memory issues.
  - **Distributed Computing**: For large-scale data processing and ML, consider using distributed computing frameworks like Apache Spark (e.g., using Amazon EMR on AWS).
  - **Service**:
  - Implement a REST API to expose the model's predictions.
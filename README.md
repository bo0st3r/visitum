# visitum

The backbone of the estimator of visitors for museums in a city using linear regression with Python.

## Mission

Build and containerize a Python application that extracts museum visitor data (Wikipedia) and city population data, stores it, trains a simple linear regression model (`visitor_count ~ city_population`), and exposes insights via a Jupyter notebook. This serves as an MVP for correlating museum attendance with city size for a new world organization.

## Assignment clarifications

- **Visitor Count**: the initial assignment description said to focus on museums with >2 million visitors, but the source seems to have changed since the creation of this assignment and now lists museums with 1.25 million visitors and more. After asking Simon for clarification, it was said that "Fine to explore or just to make a judgement call here". I went with >1.25 million visitors because it allows more variety in the dataset which is already quite small.
- **Visitor Year**: the source also says that the data is for the year 2024, however for some entities the year is 2023 or even 2022. After asking Simon for clarification, it was said to use the year 2024 only, therefore remove some entities from the dataset.
- **Regression Input**: being unsure of the expected model input: (1) Museum Visitors or (2) Total Museum Visitors For The City, I asked for clarification and was told "would go for something simpler that fits in the time and keep the broader for discussion". I went with option 1 which is simpler and probably more relevant for the end goal.

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

The ET steps are orchestrated by `src/scripts/run_etl.py`, which produces `data/enriched_museum_data.csv` and `src/scripts/load_data_from_csv_to_db.py` loads it into the `data/visitum.db` database. 
Then, `src/scripts/train_model.py` trains a linear regression model using the data from the database and saves the model to `data/trained_regression_model.joblib`.

## Project Structure

```
visitum/
│
├── .gitignore
├── .python-version
├── pyproject.toml       # Python package definition and dependencies
├── README.md
├── Dockerfile           # Defines the Docker image for the application
├── docker-compose.yml   # Defines services, networks, and volumes for Docker
├── entrypoint.sh        # Script executed when Docker container starts
│
├── docker-data/         # Output directory for generated data (DB, model, CSVs) - mounted from host
│   ├── enriched_museum_data.csv # (Example output)
│   ├── visitum.db             # (Example output)
│   └── trained_regression_model.joblib # (Example output)
│
├── src/
│   ├── __init__.py
│   ├── config.py        # Configuration settings
│   ├── data/            # Data processing modules (ETL)
│   │   ├── __init__.py
│   │   ├── models.py      # Data enums/models (e.g., FetchFailureReason)
│   │   ├── extraction.py  # Data extraction logic (Wikipedia, Population)
│   │   └── transformation.py # Data cleaning and transformation
│   ├── db/              # Database interaction modules
│   │   ├── __init__.py
│   │   ├── database.py  # Database connection and session management
│   │   ├── models.py    # Database models (SQLAlchemy)
│   │   └── queries.py   # CRUD operations and data querying logic
│   ├── ml/              # Machine Learning modules
│   │   ├── __init__.py
│   │   └── model.py     # Core ML model definitions (e.g., Linear Regression)
│   └── scripts/         # Utility scripts for running pipeline stages
│       ├── __init__.py
│       ├── run_etl.py   # Orchestrates ETL, produces CSV
│       ├── load_data_from_csv_to_db.py # Loads CSV data into the database
│       └── train_model.py # Trains the ML model and saves it
│
├── notebooks/
│   └── analysis.ipynb # Main Jupyter notebook for model evaluation and visualization
│   └── etl_and_training.ipynb # Exploratory notebook (optional, not primary deliverable)
│
└── tests/              
    ├── __init__.py
    ├── conftest.py
    ├── data/
    ├── db/
    └── ml/
```

## Technology Stack

- **Programming Language**: Python 3.11+
- **Dependency Management**: `pyproject.toml`
- **Museum Visitors Data Extraction**: `requests`, `pandas.read_html` (`src/data/extraction.py`)
- **City Population Data Extraction**: `geocoder` library (`src/data/extraction.py`)
- **Data Manipulation**: `Pandas`, `Numpy` (`src/data/transformation.py`, `notebooks/`)
- **Data Storage**: CSV output (`data/enriched_museum_data.csv`), Database (`SQLite` via `src/db`, stored at `data/visitum.db`)
- **Configuration**: Python file (`src/config.py`)
- **ML Library**: `scikit-learn`
- **Containerization**: `Docker`, `Docker Compose`
- **Testing**: `pytest`

## Machine Learning Model

- **Algorithm**: Linear Regression (`scikit-learn.linear_model.LinearRegression`)
- **Features (X)**: City Metropolitan Population
- **Target (Y)**: Museum Visitor Count (for 2024, >1.25M)
- **Evaluation**: Standard regression metrics (e.g., R-squared, MAE, MSE). Visualizations in the Jupyter notebook (`notebooks/analysis.ipynb`). Initial results with simple linear regression indicate a weak correlation between city population and museum visitor count, suggesting that population alone is not a strong predictor and other factors or more complex models should be considered for better performance.

## Setup & Usage

This project is designed to be run using Docker and Docker Compose, which handles the setup of the Python environment, data generation, model training, and running the JupyterLab server.

### Prerequisites

1.  **Install Docker Desktop**: Ensure Docker Desktop (or Docker Engine and Docker Compose separately for Linux users) is installed and running on your system. You can download it from the [official Docker website](https://www.docker.com/products/docker-desktop/).

### Running the Application

1.  **Clone the Project** (if you haven't already):
    ```bash
    git clone https://github.com/bo0st3r/visitum.git
    cd visitum
    ```

2.  **Build and Start the Application**:
    In the root directory of the project run:
    ```bash
    docker-compose up --build
    ```

3.  **Access JupyterLab**:
    Once the build is complete and the container is running, you'll see log messages in your terminal. JupyterLab will be accessible in your web browser at:
    [http://localhost:8888](http://localhost:8888)

4.  **Open and Run the Notebook**:
    *   In the JupyterLab file browser (usually on the left), open the `analysis.ipynb` notebook
    *   You can now run the cells in the notebook. It will use the `visitum.db` database and the pre-trained model generated when the container started.

### Generated Data

*   A directory named `docker-data` will be created in your project's root directory on your host machine.
*   This `docker-data` directory is synchronized with the `/app/data` directory inside the Docker container.
*   When the application starts for the first time (or if `docker-data` is empty), the `entrypoint.sh` script will execute the data extraction, database loading, and model training scripts. The generated `visitum.db` and `trained_regression_model.joblib` will appear in this `docker-data` folder.

### Stopping the Application

1.  Go to the terminal where `docker-compose up` is running.
2.  Press `Ctrl+C` to stop the container(s).
3.  To remove the stopped containers (and free up resources), you can optionally run:
    ```bash
    docker-compose down
    ```
    This command does not remove the `docker-data` directory or the Docker image itself.

## Testing

The project includes a suite of unit and integration tests developed using `pytest`. These tests cover individual functions, classes, and the interactions between different components of the ETL pipeline and ML model training. External dependencies such as API calls and database interactions are mocked where appropriate to ensure isolated and reliable tests.

### Running Tests

To run the tests, navigate to the project's root directory and execute the following command:

```bash
pytest -n auto
```
This command will automatically discover and run all tests, utilizing multiple cores if available for faster execution (not really necessary atm but good practice).

## Design Choices & Future Enhancements

This section outlines potential areas for future improvement and scaling.

### Data Sources & Enrichment
- **Museum Visitors Data Source**:
    - Currently, Wikipedia is used to fetch museum visitors data.
    - **Improvement**: Explore alternative data sources for museum visitors data that are more reliable and up-to-date. Wikipedia is not always up to date and relies on manual updates from users.
    
- **Population Data Source & Museum Geolocation**:
    - Currently, `geocoder` with Geonames provides city proper populations. Museum-to-city association is based on city name strings.
    - **Improvement**: Explore alternative data providers or sources specifically for metropolitan area populations, as this is often a better correlate for visitor numbers than city proper population.
    - **Improvement**: A significant enhancement is to use precise museum geographic coordinates for geocoding. This would more accurately determine the relevant city and its metropolitan area, leading to better population data for the model. 

### ETL Process
- **Loading to Database**: Currently, data is saved to a CSV before being loaded into the database. This was a shortcut during prototyping.
    - **Improvement**: Load data directly into the database from the ETL script for efficiency.
- **Modularity & Orchestration**:
    - **Improvement**: Refactor ETL for better modularity. For more complex workflows, consider using a workflow orchestrator (e.g. AWS Step Functions).

### Configuration Management
- **Current**: Configuration is managed via `src/config.py`.
    - **Improvement**: For more complex or sensitive configurations, move settings to a dedicated configuration file (e.g., YAML, TOML), environment variables (especially for secrets, potentially managed via a secrets manager), or a configuration database.

### Scalability
- **Database**:
    - SQLite is used for development (`data/visitum.db`).
    - **Improvement**: For production, migrate to a more robust and scalable database like PostgreSQL, potentially a managed service (e.g., AWS RDS).
- **Caching**:
    - **Improvement**: Implement caching for Wikipedia API results, geocoder results, the trained model, and potentially model predictions to reduce redundant computations and API calls.
- **API & Service Endpoints**:
    - **Improvement**: Develop FastAPI (or similar) endpoints to expose data, model predictions, and potentially trigger ETL/training processes. Design for horizontal scaling.
- **Data Ingestion/Processing (Large Scale)**:
    - **Improvement**: For very large datasets, implement chunked/paginated data loading and processing to manage memory effectively.
- **Distributed Computing**:
    - **Improvement**: For large-scale data processing and ML model training, consider frameworks like Apache Spark (e.g., via Amazon EMR on AWS).
- **ML Serving**:
    - **Improvement**: Deploy the ML model using a dedicated serving solution (e.g. AWS SageMaker) for better scalability, monitoring, and versioning.

### Machine Learning Model
- **Feature Engineering**:
    - **Improvement**: Incorporate additional features (e.g., museum type, city GDP, tourism statistics, flight arrivals, hotel occupancy rates) to potentially improve model accuracy.
- **Model Selection**:
    - **Improvement**: Explore more advanced models.
- **Preventing Overfitting**:
    - **Improvement**: If we explore more complex models in the future, we would also incorporate techniques to prevent overfitting. This ensures the model learns general patterns from the data rather than memorizing the training set, leading to better performance on new, unseen data.

#### Research
Some [research on time series forecasting for museum visitors](https://github.com/Di40/Time-Series-Forecasting-Museum-Visitors?tab=readme-ov-file).

### Development & Operations
- **Dependency Management**: The project uses `pyproject.toml`.
    - **Consideration**: Adopting a tool like Poetry could further streamline dependency resolution and environment management.
- **Type Safety**:
    - **Improvement**: Extend type hinting (e.g., using Pydantic models) to data structures used in the extraction and transformation steps, not just for database and ML components.
- **Error Handling & Monitoring**:
    - **Improvement**: Implement comprehensive error handling, structured logging, and monitoring dashboards (e.g., using Prometheus, Grafana, or cloud-native solutions) for production deployment.
- **CI/CD**:
    - **Improvement**: Set up a Continuous Integration/Continuous Deployment (CI/CD) pipeline (e.g., GitHub Actions, GitLab CI, Jenkins) to automate testing, building, and deployment processes.
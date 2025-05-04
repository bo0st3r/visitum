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

The exploratory ETL pipeline is now implemented in `etl_exploration.py`. It:

1. Extracts museum visitor data from Wikipedia using the MediaWiki API
2. Cleans and transforms data, filtering museums with >1.25M visitors in 2024
3. Uses the geocoder library to fetch city population data in parallel
4. Handles special cases like compound cities ("Vatican City, Rome")
5. Saves the enriched data to CSV for subsequent analysis

The initial dataset is created and stored in `enriched_museum_data.csv` including museum names, cities, countries, visitor counts, and metropolitan populations.
Later, it is saved to the database (SQLite).

## ETL Pipeline

### Extraction

#### Museum Visitors Source

Museums with over 1,250,000 annual visitors [(Wikipedia)](https://en.wikipedia.org/wiki/List_of_most-visited_museums)

Using the MediaWiki API with direct `requests` to fetch HTML content, then extracting tables using pandas' read_html functionality. This approach is more flexible than using BeautifulSoup and allows for better error handling.

#### City Population Source

The city population is retrieved using the `geocoder` library, which provides access to geographic data including city population from different providers, currently using the Geonames provider. It allows us to reliably retrieve the population of a city, and without the need for standardizing the city name and country name (e.g. USA | US | United States | United States of America).

**Improvement idea:** Metropolitan population is a better proxy for the number of people that will visit the museums, but it is not always available with public APIs. Therefore, the implementation currently uses city proper populations from Geonames which is the only geocoder provider that provides population data reliably. Using the metropolitan population would be a good improvement to make.

**Special cases:** For museums located in "multiple cities" (e.g., "Vatican City, Rome", "London, South Kensington"), we either (1) have a special case in the code to handle it or (2) we retrieve the population of each city separately by splitting the city name on commas and using the maximum population value rather than summing them to prevent double-counting when locations are within the same metropolitan area. This is not a perfect solution, but it is a good compromise for now that allows for new edge cases to be added without having to change the code.

### Transformation

- **Data Cleaning**:
  - **Visitor Count Column**: Parse various formats (e.g., "8,700,000", "6.3 million"), remove references (e.g., `[1]`), strip extra text (e.g., "(as of...)"), handle commas, and convert to a numeric type. Handle potential missing values.
  - **Year Extraction**: Extract the year associated with the visitor count (often in parentheses) and filter data to include only entries explicitly marked as 2024.
  - **City Name Standardization**: Clean city names (e.g., removing state/district info like in "Washington, D.C." or handling multi-city entries like "Vatican City, Rome") to ensure consistent matching with population data sources.
  - **General**: Handle potential missing values in other relevant columns (Name, City, Country).
- **Data Structuring**: Organize the cleaned data into a structured format (Pandas DataFrame) suitable for storage and analysis.
- **Feature Engineering**: Create the final features for the ML model (Standardized City Name/ID, Metropolitan Population, 2024 Visitor Count).

### Loading

- **Database Choice**: Use a lightweight database suitable for rapid prototyping and potential scalability. SQLite is a good initial choice, deployable within the Docker container. For greater scalability, PostgreSQL could be considered later.
- **Schema Design**: Define a simple schema to store museum details (Name, City, Country, 2024 Visitor Count) and city population data (City, Country, Metropolitan Population).
- **Data Insertion**: Load the transformed data into the chosen database.

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
│   ├── visitum/
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration settings
│   │   ├── data/            # Data processing modules (ETL)
│   │   │   ├── __init__.py
│   │   │   ├── extraction.py  # Data extraction logic (Wikipedia, Population)
│   │   │   ├── transformation.py # Data cleaning and transformation
│   │   │   └── loading.py     # Database loading logic
│   │   ├── db/              # Database interaction modules
│   │   │   ├── __init__.py
│   │   │   └── models.py    # Database models (e.g., SQLAlchemy)
│   │   │   └── operations.py # CRUD operations
│   │   ├── ml/              # Machine Learning modules
│   │   │   ├── __init__.py
│   │   │   ├── model.py     # Linear Regression model training/prediction
│   │   │   └── utils.py     # ML utilities
│   │   ├── api/             # API exposure (e.g., FastAPI)
│   │   │   ├── __init__.py
│   │   │   ├── main.py      # API entry point
│   │   │   └── endpoints.py # API routes
│   │   └── utils/           # Shared utilities
│   │       └── __init__.py
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
- **Museum Visitors Data Extraction**: `requests` for API calls, `pandas.read_html` for table extraction
- **City Population Data Extraction**: `geocoder` library with Geonames provider
- **Data Manipulation**: `Pandas`
- **Parallel Processing**: `concurrent.futures` for parallel population data fetching
- **Data Storage**: Currently CSV, planned database integration
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

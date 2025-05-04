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

Using [Wikipedia-API](https://pypi.org/project/Wikipedia-API/#files) rather than BeautifulSoup because it's too brittle and takes more time to implement, while the Wikipedia-API is actively maintained by the Wikipedia community and is more reliable.

#### City Population Source
The city population is the metropolitan area population, which is the sum of the city proper and the surrounding areas.

Decided to use the metropolitan area population rather than the city proper population because it's more likely to be a good proxy for the number of people that will visit the museums.

### Transformation
- **Data Cleaning**: 
  - **Visitor Count Column**: Parse various formats (e.g., "8,700,000", "6.3 million"), remove references (e.g., `[1]`), strip extra text (e.g., "(as of...)"), handle commas, and convert to a numeric type. Handle potential missing values.
  - **Year Extraction**: Extract the year associated with the visitor count (often in parentheses) and filter data to include only entries explicitly marked as 2024.
  - **City Name Standardization**: Clean city names (e.g., removing state/district info like in "Washington, D.C." or handling multi-city entries like "Vatican City, Rome") to ensure consistent matching with population data sources.
  - **General**: Handle potential missing values in other relevant columns (Name, City, Country).
- **Data Structuring**: Organize the cleaned data into a structured format (e.g., Pandas DataFrame) suitable for storage and analysis.
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
- **Data Extraction**: `Wikipedia-API`, potentially web scraping libraries like `requests` and `BeautifulSoup4` for population data if no suitable API is found.
- **Data Manipulation**: `Pandas`
- **Database**: `SQLite` (initially for rapid development), `PostgreSQL` (preferred for scalability, aligning with common enterprise relational database requirements). `SQLAlchemy` as ORM.
- **API Framework**: `FastAPI` (modern, high-performance, suitable for cloud-native applications)
- **ML Library**: `scikit-learn`
- **Containerization**: `Docker`, `Docker Compose` (ensures consistent environment and simplifies deployment to cloud platforms like AWS, Azure, or GCP)
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
    *   API: `http://localhost:8000` (or configured port)
    *   Jupyter Notebook: `http://localhost:8888` (or configured port)

## Testing Strategy
- **Unit Tests**: Test individual functions and classes (e.g., data extraction logic, transformation steps, database operations, API endpoint logic) using `pytest`. Mock external dependencies like API calls and database interactions.
- **Integration Tests**: Test the interaction between components (e.g., data extraction -> transformation -> loading). Potentially test against a test database instance.
- **End-to-End Tests**: Test the full flow (e.g., calling the API to trigger training/prediction, querying results).

## Design Choices & Future Considerations
- **Population Data Source**: The choice of population data source needs careful consideration for reliability and coverage. Options include dedicated APIs (if available), scraping reputable sources (e.g., census bureaus, Wikipedia tables), or using pre-compiled datasets. Using Wikipedia tables might be fastest initially but could be less reliable long-term. We need to clearly document the chosen source and its limitations.
- **Scalability**:
    - **Database**: Transitioning from SQLite to a managed `PostgreSQL` instance (e.g., AWS RDS, Azure Database for PostgreSQL, Google Cloud SQL) is the clear path for production and scaling.
    - **API**: FastAPI is inherently scalable. Deployment via container orchestration (Kubernetes on AWS/Azure/GCP) or serverless platforms (AWS Lambda+API Gateway, Google Cloud Run) would handle increased load.
    - **ETL**: For significantly larger datasets or near real-time updates, the ETL process could be refactored using workflow orchestrators (e.g., Airflow, Dagster) and potentially leverage `Apache Spark` for distributed processing (e.g., on Databricks, AWS EMR, Azure Synapse, Google Dataproc), aligning with common Big Data technologies.
- **ML Model Improvement**:
    - **More Features**: Incorporating additional features (e.g., museum type, city GDP, tourism statistics, time-series data if available) could improve model accuracy.
    - **Different Models**: Exploring other regression models (e.g., Polynomial Regression, Gradient Boosting) might yield better results.
    - **Regularization**: Apply regularization techniques if overfitting is observed.
- **Error Handling & Monitoring**: Implement comprehensive error handling, logging, and monitoring for production deployment.
- **CI/CD**: Set up a Continuous Integration/Continuous Deployment pipeline (e.g., using GitHub Actions, GitLab CI) to automate testing and deployment.





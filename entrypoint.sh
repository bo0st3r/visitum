#!/bin/sh
# entrypoint.sh

# Exit immediately if a command exits with a non-zero status.
set -e

DB_FILE="/app/data/visitum.db"
MODEL_FILE="/app/data/trained_regression_model.joblib" 

# Check if the database file already exists in the mounted volume
if [ ! -f "$DB_FILE" ]; then
  echo "Database not found at $DB_FILE. Running data generation and model training scripts..."
  
  # Create the data directory if it doesn't exist (though volume mount should handle it)
  mkdir -p /app/data
  
  echo "Running ETL script (run_etl.py)..."
  python /app/src/scripts/run_etl.py
  
  echo "Loading data into database (load_data_from_csv_to_db.py)..."
  python /app/src/scripts/load_data_from_csv_to_db.py
  
  echo "Training model (train_model.py)..."
  python /app/src/scripts/train_model.py
  
  echo "Data generation and model training complete."
else
  echo "Database found at $DB_FILE. Skipping data generation and model training."
  # Optionally, we could also check for model_file and run only training if it's missing
fi

# Execute the command passed as arguments to this script (e.g., CMD from Dockerfile)
echo "Executing command: $@"
exec "$@" 
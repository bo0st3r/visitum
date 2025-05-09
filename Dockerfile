# Base Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# # Install build essentials for some python packages, and git for VCS installs if any
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     git \
#     && rm -rf /var/lib/apt/lists/*

# Copy project configuration and source code needed for installation
COPY pyproject.toml /app/
COPY src /app/src/

# Install dependencies AND the local project
RUN pip install --no-cache-dir .

# Copy the rest of the application code
# This includes the entrypoint.sh script
COPY . /app/

# Set PYTHONPATH to include the src directory, so imports like 'config' work from scripts
ENV PYTHONPATH="/app/src:${PYTHONPATH}"

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# The entrypoint script will handle data generation and then execute the CMD
ENTRYPOINT ["/app/entrypoint.sh"]

# Create the data directory - entrypoint also does mkdir -p, but this is good practice
# The actual data generation RUN commands are removed from here
RUN mkdir -p /app/data

# Expose the Jupyter Notebook port
EXPOSE 8888

# Default command to be executed by the entrypoint script
# Allows access from any IP, no token, specifies notebook directory
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--notebook-dir=/app/notebooks", "--LabApp.token", ""] 
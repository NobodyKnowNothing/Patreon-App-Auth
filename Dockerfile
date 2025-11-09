# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
# Prevent python from writing pyc files to disc (optional)
ENV PYTHONDONTWRITEBYTECODE 1
# Prevent python from buffering stdout and stderr (important for logging)
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (if any were needed)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user and group
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy the application code into the container at /app
# This should be done AFTER pip install to leverage Docker cache
COPY main.py .
COPY fastapi_app/ ./fastapi_app/
COPY Models/ ./Models/

# Change ownership of the /app directory to the new user
# This is good practice, though the app primarily uses Google Sheets for patron data.
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Make port 8080 available to the world outside this container (or port specified by $PORT env var)
EXPOSE 8080

# Define the command to run your app
# Using uvicorn as specified in main.py
CMD ["python", "main.py"]

# ---
# For production, you might prefer gunicorn:
# Ensure gunicorn is in requirements.txt (e.g., RUN pip install --no-cache-dir gunicorn)
# CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
#
# IMPORTANT RUNTIME CONFIGURATION:
# Ensure PATREON_WEBHOOK_SECRET is passed as an environment variable at runtime.
# Ensure GOOGLE_APPLICATION_CREDENTIALS_JSON (containing the service account key JSON string)
# is passed as an environment variable at runtime.
# The PORT environment variable can also be set (defaults to 8080 if not set).
# Patron data is stored in Google Sheets, so no volume for "patrons.json" is required for data persistence.
# ---
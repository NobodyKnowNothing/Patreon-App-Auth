# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
# Prevent python from writing pyc files to disc (optional)
ENV PYTHONDONTWRITEBYTECODE 1
# Prevent python from buffering stdout and stderr (important for logging)
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (if any were needed, e.g., for psycopg2 you'd need libpq-dev)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user and group
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy the current directory contents into the container at /app
# This should be done AFTER pip install to leverage Docker cache
COPY app.py .
# If you had other local modules, you'd copy them here e.g. COPY my_module/ ./my_module/

# Change ownership of the /app directory to the new user
# This ensures the app can write patrons.json if it's not mounted as a volume
# or if the volume has correct permissions.
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define the command to run your app
# Using gunicorn is recommended for production, but for simplicity, direct python execution:
CMD ["python", "app.py"]

# ---
# For production, you might prefer gunicorn:
# RUN pip install --no-cache-dir gunicorn
# CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
# Ensure PATREON_WEBHOOK_SECRET is passed as an environment variable at runtime
# Ensure patrons.json is handled via a volume for persistence
# ---
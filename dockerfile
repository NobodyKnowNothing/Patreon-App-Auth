# 1. Choose a base image
# Using a slim Python image to keep the size down
FROM python:3.10-slim

# 2. Set the working directory in the container
WORKDIR /app

# 3. Copy your application's code into the container
COPY reroute.py .

# 4. (Optional) Install dependencies if you had any (not needed for this script)
# For example, if you had a requirements.txt:
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# 5. Expose the default local port your application will listen on
# This is for documentation and can be used by Docker networking.
# The actual port mapping is done during `docker run`.
EXPOSE 8080

# 6. Define the command to run your application
# This will execute `python forwarder.py` when the container starts.
# You can override the default script arguments when running the container.
ENTRYPOINT ["python", "forwarder.py"]

# (Optional) You can provide default arguments for the ENTRYPOINT using CMD
# If you run `docker run <image_name>` without any further arguments, these CMD args will be used.
# If you run `docker run <image_name> --some-other-arg`, these CMD args are ignored.
# For this script, the internal defaults are quite specific, so it's often better
# to pass all arguments during `docker run`.
# However, you could set up a default forwarding scenario here:
# CMD ["--local-host", "0.0.0.0", "--local-port", "8080", "--remote-host", "example.com", "--remote-port", "80"]
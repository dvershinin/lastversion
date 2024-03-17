# Use a lightweight base image with Python and pip installed
FROM python:3.9-alpine

# Set the working directory to /app
WORKDIR /app

# Copy the source code into the container
COPY src setup.py setup.cfg MANIFEST.in README.md ./

# Install the application and its dependencies
RUN pip install -e .

# Set the entrypoint to the command that runs your application
ENTRYPOINT ["lastversion"]

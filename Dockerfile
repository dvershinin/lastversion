# Use a lightweight base image with Python and pip installed
FROM python:3.13-alpine

# Using "lastversion" user as provided by some linter was a mistake and causes issues with GitHub actions being ran as "runner"
# and lastversion running as a different user and being unable to work with workspace files for extracting to its directory
# USER root

# Set the working directory to /app
WORKDIR /app

# Copy the source code into the container
COPY src ./src/
COPY setup.py README.md ./

# Install the application and its dependencies
RUN pip install -e .

# Additionally install truststore package for SSL certificate verification via pip
RUN pip install truststore

# Set the entrypoint to the command that runs your application
ENTRYPOINT ["lastversion"]

FROM prefecthq/prefect:3-latest

COPY requirements.txt .
RUN pip install -r requirements.txt

# If you need any other system dependencies, install them here
# For example:
# RUN apt-get update && apt-get install -y some-package

# Set the working directory
WORKDIR /opt/prefect
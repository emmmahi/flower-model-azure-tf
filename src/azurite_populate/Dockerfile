# Use the official Python image as a base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy the local code to the container image
COPY populate.py .

COPY model_0.keras datasets/val_data.zip ./ 
#dataset.csv

# Run the Python script
ENTRYPOINT ["python", "populate.py"]

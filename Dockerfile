# Use an official Python runtime as the base image
FROM python:3.11-slim

# Set metadata
LABEL authors="mihir"

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot's code into the container
COPY . .

# Exclude environment variables from the image
# Do not define ENV TOKEN or OWNER_ID here

# Set the command to run the bot
CMD ["python", "main.py"]

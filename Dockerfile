# Use an official Python runtime as the base image
FROM python:3.9-slim

# Environment variables to improve performance and logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Set working directory to the source folder
WORKDIR /app/src

# Expose the port that the server listens on (default: 3142)
EXPOSE 3142

# Command to run the proxy caching server
CMD ["python", "server.py"]

FROM python:3.11-slim

WORKDIR /app

# Copy the controller-api requirements file
COPY controller-api/requirements.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the controller-api application files
COPY controller-api/ .

# Expose port expected by Render
EXPOSE 8080

# Start FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]




FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml README.md ./

# Copy the package directory
COPY expense_manager/ ./expense_manager/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy remaining application code
COPY . .

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Expose the port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Command to run the application
CMD ["python", "run_app.py", "--profile", "production"]

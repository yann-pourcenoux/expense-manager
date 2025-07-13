# Expense Manager

A Streamlit web application for managing personal expenses.

## Features

- **User Authentication**: Sign up and log in securely
- **Expense Tracking**: Add, edit, and delete expense records
- **Categorization**: Organize expenses by custom categories
- **Shared Expenses Dashboard**: View household shared expenses in a stacked bar chart by category for the last 6 months
- **Visualization**: View expense trends and breakdowns with interactive charts
- **Data Analysis**: Analyze spending patterns over time
- **Responsive Interface**: Built with Streamlit for a clean, responsive UI
- **Multiple Configurations**: Run development and production instances with different configuration profiles

## Requirements

- Python 3.12+
- Streamlit 1.27+
- Pandas 2.0+
- Plotly 5.14+
- PyYAML 6.0+
- SQLite (included in Python standard library)

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd expense-manager
   ```

2. Install dependencies:
   ```
   pip install -e .
   ```

## Configuration Profiles

The application uses YAML configuration files to customize settings like database path and server port. Configuration files are stored in the `config/` directory.

### Available Profiles

- `development.yaml`: Development configuration with port 8502
- `production.yaml`: Production configuration with port 8501

The app uses the development profile by default.

## Docker Deployment

The application can be deployed using Docker containers for easy distribution and deployment.

### Quick Start with Docker

1. **Using Docker Compose:**
   ```bash
   docker-compose up --build
   ```

2. **Access the application:**
   Open your browser and navigate to `http://localhost:8501`

3. **Stop the application:**
   ```bash
   docker-compose down
   ```

### Running in Background

To run the container in the background (detached mode):

1. **Start in background:**
   ```bash
   docker-compose up -d
   ```

2. **Start in background with rebuild:**
   ```bash
   docker-compose up -d --build
   ```

3. **Check container status:**
   ```bash
   docker-compose ps
   ```

4. **View logs:**
   ```bash
   docker-compose logs -f
   ```

5. **Stop the background container:**
   ```bash
   docker-compose down
   ```

6. **Restart the container:**
   ```bash
   docker-compose restart
   ```

**Note:** The container is configured with `restart: unless-stopped`, so it will automatically restart if it crashes.


## Running the Application

Run the Streamlit app with a simple command:

```
# Run with development profile (default)
run

# Run with development profile (explicitly)
run dev

# Run with production profile
run prod
```

Alternatively, you can use the run_app.py script:

```
# Run with development profile
./run_app.py --profile development

# Run with production profile
./run_app.py --profile production
```

You can run multiple instances simultaneously with different profiles:

```
# Terminal 1 - Development instance on port 8502
run

# Terminal 2 - Production instance on port 8501
run prod
```

## Development

For development, you can install the package in development mode:

```
pip install -e ".[dev]"
```

This will install development dependencies like pytest, black, etc.

To run tests:

```
pytest
```

## License

MIT License - See the LICENSE file for details.

## Screenshots

[Include screenshots here when available]

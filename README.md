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

## Requirements

- Python 3.12+
- Streamlit 1.27+
- Pandas 2.0+
- Plotly 5.14+
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

## Database Setup

The application uses SQLite for data storage, which requires no additional setup. The database file (`expense_manager.db`) will be created automatically when you first run the application.

## Running the Application

Run the Streamlit app:

```
streamlit run expense_manager/app.py
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

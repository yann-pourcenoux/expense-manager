# Expense Manager

A Streamlit web application for managing personal expenses with Supabase integration.

## Features

- **User Authentication**: Sign up and log in securely with Supabase authentication
- **Expense Tracking**: Add, edit, and delete expense records
- **Categorization**: Organize expenses by custom categories
- **Visualization**: View expense trends and breakdowns with interactive charts
- **Data Analysis**: Analyze spending patterns over time
- **Responsive Interface**: Built with Streamlit for a clean, responsive UI

## Requirements

- Python 3.12+
- Streamlit 1.27+
- Supabase Python SDK 1.0.3+
- Pandas 2.0+
- Plotly 5.14+

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

3. Create a `.env` file in the root directory with your Supabase credentials:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   SUPABASE_SERVICE_KEY=your_supabase_service_key
   ```

## Supabase Setup

1. Create a new project on [Supabase](https://supabase.com/)
2. Enable Auth with email/password provider
3. Create the following tables in the SQL editor:

```sql
-- Create expenses table
CREATE TABLE expenses (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  amount DECIMAL(10, 2) NOT NULL,
  category_id UUID NOT NULL REFERENCES categories(id),
  date TIMESTAMP WITH TIME ZONE NOT NULL,
  description TEXT,
  payment_method TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- Create categories table
CREATE TABLE categories (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  color TEXT NOT NULL DEFAULT '#000000',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- Initial categories
INSERT INTO categories (name, color) VALUES
  ('Food & Dining', '#FF9800'),
  ('Transportation', '#2196F3'),
  ('Housing', '#4CAF50'),
  ('Entertainment', '#9C27B0'),
  ('Shopping', '#F44336'),
  ('Utilities', '#607D8B'),
  ('Healthcare', '#E91E63'),
  ('Travel', '#3F51B5'),
  ('Education', '#009688'),
  ('Miscellaneous', '#795548');

-- Access policies for security
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access their own expenses" ON expenses
  FOR ALL USING (auth.uid() = user_id);

-- Allow public access to categories
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Categories are viewable by everyone" ON categories
  FOR SELECT USING (true);
```

4. Copy your Supabase URL and anon key to the `.env` file

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

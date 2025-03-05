"""Dashboard page for visualizing expense data.

This module provides a Streamlit page for visualizing expense data
with various charts and filters.
"""

import calendar
from datetime import date, datetime, timedelta

import streamlit as st

from expense_manager.db.db_manager import DatabaseManager
from expense_manager.utils.analytics import (
    create_category_pie_chart,
    create_income_vs_expenses_chart,
    create_time_series_chart,
    prepare_expense_data,
    summarize_expenses,
)
from expense_manager.utils.models import format_currency


def display_dashboard() -> None:
    """Display the expense dashboard with visualizations."""
    st.title("Expense Dashboard")

    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to view your expense dashboard.")
        return

    # Initialize database manager
    db_manager = DatabaseManager()

    # Get user ID from session
    user_id = (
        st.session_state.user.id
        if hasattr(st.session_state.user, "id")
        else st.session_state.user["id"]
    )

    # Month selector
    st.subheader("Select Month")

    # Create month and year selectors
    current_date = datetime.now()
    col1, col2 = st.columns(2)

    # Month selection with names
    month_names = list(calendar.month_name)[1:]  # Skip empty first item
    default_month_idx = current_date.month - 1  # Adjust for 0-based index

    with col1:
        selected_month_name = st.selectbox(
            "Month", options=month_names, index=default_month_idx
        )
        selected_month = month_names.index(selected_month_name) + 1  # Back to 1-based

    # Year selection (last 5 years and current year)
    years = list(range(current_date.year - 4, current_date.year + 1))
    with col2:
        selected_year = st.selectbox(
            "Year",
            options=years,
            index=len(years) - 1,  # Default to current year
        )

    # Calculate first and last day of selected month
    first_day = date(selected_year, selected_month, 1)
    # Last day is first day of next month - 1 day
    if selected_month == 12:
        last_day = date(selected_year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(selected_year, selected_month + 1, 1) - timedelta(days=1)

    # Convert to datetime for queries
    start_datetime = datetime.combine(first_day, datetime.min.time())
    end_datetime = datetime.combine(last_day, datetime.max.time())

    # Display selected date range info
    st.info(
        f"Showing data for: {selected_month_name} {selected_year} "
        f"({first_day.strftime('%d/%m/%Y')} - {last_day.strftime('%d/%m/%Y')})"
    )

    # Fetch categories for filtering and display
    categories_result = db_manager.get_categories()
    categories = categories_result.get("categories", [])

    # Category filter
    category_options = ["All Categories"] + [cat["name"] for cat in categories]
    selected_category = st.selectbox("Filter by Category", category_options)

    # Get category ID if a specific category is selected
    category_id = None
    if selected_category != "All Categories":
        category_id = next(
            (cat["id"] for cat in categories if cat["name"] == selected_category), None
        )

    # Add view options
    view_options = ["Regular", "Split View"]
    selected_view = st.radio("Expense View", view_options, horizontal=True)
    is_split_view = selected_view == "Split View"

    # Fetch expenses with filters
    expenses_result = db_manager.get_expenses(
        user_id=user_id,
        start_date=start_datetime,
        end_date=end_datetime,
        category_id=category_id,
    )
    expenses = expenses_result.get("expenses", [])

    # Create a DataFrame for analysis
    expenses_df = prepare_expense_data(expenses)

    if expenses_df.empty:
        st.info("No expenses found for the selected month.")
        return

    # If split view, add split count to expenses
    if is_split_view:
        # Get split information for each expense
        split_counts = {}
        for exp in expenses:
            if exp.get("is_shared", False):
                split_result = db_manager.get_expense_splits(exp["id"])
                split_users = split_result.get("user_ids", [])
                split_counts[exp["id"]] = len(split_users) if split_users else 1
            else:
                split_counts[exp["id"]] = 1

        # Add split count to the DataFrame
        if "id" in expenses_df.columns:
            expenses_df["split_count"] = expenses_df["id"].map(split_counts)

    # Generate summary statistics
    summary = summarize_expenses(expenses_df, categories, is_split_view)

    # Fetch income data for the period
    current_month = datetime.now().replace(day=1)
    income_result = db_manager.get_monthly_income(user_id, current_month)
    monthly_income = income_result.get("income", {"amount": 0})

    # Get income history
    income_history = db_manager.get_income_history(user_id, limit=12)
    income_data = income_history.get("income_history", [])

    # Display total expenses and income
    col1, col2, col3 = st.columns(3)

    with col1:
        # Display total expenses
        st.metric("Total Expenses", format_currency(summary["total"]))

    with col2:
        # Display monthly income
        income_amount = monthly_income.get("amount", 0) if monthly_income else 0
        st.metric("Monthly Income", format_currency(income_amount))

    with col3:
        # Display balance
        balance = income_amount - summary["total"]
        delta = format_currency(abs(balance))
        if balance >= 0:
            st.metric(
                "Balance", format_currency(balance), delta=f"✅ {delta} under budget"
            )
        else:
            st.metric(
                "Balance",
                format_currency(balance),
                delta=f"⚠️ {delta} over budget",
                delta_color="inverse",
            )

    # Display visualizations
    st.subheader("Expense Analysis")

    # Category breakdown
    st.subheader("Expense Categories")
    pie_chart = create_category_pie_chart(summary)
    st.plotly_chart(pie_chart, use_container_width=True)

    # Time series chart
    st.subheader("Expenses Over Time")
    time_chart = create_time_series_chart(summary)
    st.plotly_chart(time_chart, use_container_width=True)

    # Income vs Expenses chart
    if income_data:
        st.subheader("Income vs Expenses")
        income_vs_expenses = create_income_vs_expenses_chart(summary, income_data)
        st.plotly_chart(income_vs_expenses, use_container_width=True)

    # Expense table
    st.subheader("Expense Details")

    if not expenses_df.empty:
        # Format the DataFrame for display
        display_df = expenses_df.copy()

        # Add category names
        if "category_id" in display_df.columns:
            category_map = {cat["id"]: cat["name"] for cat in categories}
            display_df["category"] = display_df["category_id"].map(category_map)

        # Format date
        if "date" in display_df.columns:
            display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")

        # Format amount
        if "amount" in display_df.columns:
            # Initialize amount_column with default value
            amount_column = "amount"

            if is_split_view and "split_amount" in display_df.columns:
                display_df["split_amount"] = display_df["split_amount"].map(
                    format_currency
                )
                display_df["original_amount"] = display_df["amount"].map(
                    format_currency
                )
                amount_column = "split_amount"
            else:
                display_df["amount"] = display_df["amount"].map(format_currency)

        # Select and order columns for display
        if is_split_view and "split_amount" in display_df.columns:
            display_columns = [
                "date",
                "category",
                "name",
                amount_column,
                "original_amount",
                "description",
                "is_shared",
                "split_count",
            ]
        else:
            display_columns = [
                "date",
                "category",
                "name",
                amount_column,
                "description",
                "is_shared",
            ]
        display_columns = [col for col in display_columns if col in display_df.columns]

        st.dataframe(display_df[display_columns], use_container_width=True)
    else:
        st.info("No expenses to display.")

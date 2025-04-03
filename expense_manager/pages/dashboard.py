"""Dashboard page for shared expenses.

This module provides a Streamlit page for visualizing shared expenses
across categories and months using a stacked bar chart.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from expense_manager.db.db_manager import DatabaseManager
from expense_manager.utils.analytics import (
    create_individual_expense_chart,
    prepare_expense_data,
)


def get_profile_id(db_manager: DatabaseManager, user_uuid: str) -> int | None:
    """Get profile ID from user UUID.

    Args:
        db_manager (DatabaseManager): Database manager instance
        user_uuid (str): User UUID from auth.users

    Returns:
        int | None: Profile ID if found, None otherwise
    """
    profile_result = db_manager.get_profile(user_uuid)
    if "error" in profile_result:
        st.error(f"Error getting profile: {profile_result['error']}")
        return None
    return profile_result.get("profile", {}).get("id")


def create_monthly_category_chart(
    expenses_df: pd.DataFrame, categories: List[Dict[str, Any]]
) -> go.Figure:
    """Create a stacked bar chart of shared expenses by category per month.

    Args:
        expenses_df (pd.DataFrame): DataFrame of expenses
        categories (List[Dict[str, Any]]): List of categories

    Returns:
        go.Figure: Plotly figure with stacked bar chart
    """
    if expenses_df.empty:
        # Create empty chart with message
        fig = go.Figure()
        fig.update_layout(title="No shared expense data available")
        return fig

    # Filter for shared expenses only - compare is_shared with 1 (true)
    shared_expenses = expenses_df[expenses_df["is_shared"] == 1].copy()

    if shared_expenses.empty:
        # Create empty chart with message
        fig = go.Figure()
        fig.update_layout(title="No shared expense data available")
        return fig

    # Add month column for underlying data (YYYY-MM format)
    shared_expenses["month"] = shared_expenses["date"].dt.strftime("%Y-%m")

    # Add a display month column for better readability (e.g., Jan 2023)
    shared_expenses["display_month"] = shared_expenses["date"].dt.strftime("%b %Y")

    # Group by month and category
    monthly_category_expenses = (
        shared_expenses.groupby(["month", "category_id"])["amount"].sum().reset_index()
    )

    # Get unique months and sort them
    months = sorted(monthly_category_expenses["month"].unique())

    # Create a mapping from YYYY-MM to display format (Month Year)
    month_display_mapping = {}
    for _, row in shared_expenses.drop_duplicates("month").iterrows():
        month_display_mapping[row["month"]] = row["display_month"]

    # Limit to last 6 months if there are more than 6
    if len(months) > 6:
        months = months[-6:]
        monthly_category_expenses = monthly_category_expenses[
            monthly_category_expenses["month"].isin(months)
        ]

    # Create the figure
    fig = go.Figure()

    # Generate a color palette
    default_colors = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]

    # Add a trace for each category
    for i, cat in enumerate(categories):
        cat_id = cat["id"]
        cat_name = cat["name"]
        # Use a default color if 'color' is not in the category
        cat_color = cat.get("color", default_colors[i % len(default_colors)])

        # Filter data for this category
        cat_data = monthly_category_expenses[
            monthly_category_expenses["category_id"] == cat_id
        ]

        # Create a DataFrame with all months for this category
        all_months_df = pd.DataFrame({"month": months})
        cat_data_complete = all_months_df.merge(
            cat_data, on="month", how="left"
        ).fillna(0)

        # Sort by month to ensure chronological order
        cat_data_complete = cat_data_complete.sort_values("month")

        # Map the months to their display format
        display_months = [
            month_display_mapping.get(m, m) for m in cat_data_complete["month"]
        ]

        # Add the trace with display months on x-axis
        fig.add_trace(
            go.Bar(
                x=display_months,
                y=cat_data_complete["amount"],
                name=cat_name,
                marker_color=cat_color,
            )
        )

    # Configure the layout
    fig.update_layout(
        title="Last 6 Months of Shared Expenses by Category",
        xaxis_title="Month",
        yaxis_title="Amount",
        barmode="stack",
        hovermode="x unified",
        legend_title="Categories",
    )

    return fig


def display_shared_dashboard() -> None:
    """Display the shared expenses dashboard."""
    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to view the dashboard.")
        return

    # Initialize database manager
    db_manager = DatabaseManager()

    # Calculate date range for whole months
    today = datetime.now()
    # Set end_date to the last day of the current month
    if today.month == 12:
        end_date = datetime(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(today.year, today.month + 1, 1) - timedelta(days=1)

    # Set start_date to the first day of the month that's 6 months back
    if today.month <= 6:
        start_month = today.month + 6
        start_year = today.year - 1
    else:
        start_month = today.month - 6
        start_year = today.year

    start_date = datetime(start_year, start_month, 1).date()
    end_date = end_date.date()

    # Fetch all shared expenses using the new function
    expenses = db_manager.get_shared_expenses_for_dashboard(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )

    # Fetch categories
    categories_result = db_manager.get_categories()
    categories = categories_result.get("categories", [])

    if not categories:
        st.warning("No categories found. Please create categories first.")
        return

    # Create category map for prepare_expense_data
    category_map = {cat["id"]: cat["name"] for cat in categories}

    # Get profile information
    profiles_result = db_manager.get_all_profiles()
    profiles = profiles_result.get("profiles", [])
    profile_names = {p["id"]: p["display_name"] for p in profiles}

    # Process expenses data with enhanced function
    expenses_df = prepare_expense_data(expenses, profile_names, category_map)

    if expenses_df.empty:
        st.info("No shared expenses found for the last 6 months.")
        return

    # Display stacked bar chart
    fig = create_monthly_category_chart(expenses_df, categories)
    st.plotly_chart(fig, use_container_width=True)


def display_individual_dashboard() -> None:
    """Display the individual expenses dashboard."""
    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to view the dashboard.")
        return

    # Initialize database manager
    db_manager = DatabaseManager()

    # Get user profile ID
    user_id = (
        st.session_state.user.id
        if hasattr(st.session_state.user, "id")
        else st.session_state.user["id"]
    )

    profile_result = db_manager.get_profile(user_id)
    if "error" in profile_result or not profile_result.get("profile"):
        st.error("Error getting profile information.")
        return

    profile_id = profile_result["profile"]["id"]

    # Calculate date range for whole months
    today = datetime.now()
    # Set end_date to the last day of the current month
    if today.month == 12:
        end_date = datetime(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(today.year, today.month + 1, 1) - timedelta(days=1)

    # Set start_date to the first day of the month that's 6 months back
    if today.month <= 6:
        start_month = today.month + 6
        start_year = today.year - 1
    else:
        start_month = today.month - 6
        start_year = today.year

    start_date = datetime(start_year, start_month, 1).date()
    end_date = end_date.date()

    # Fetch individual expenses from the expenses_split table
    individual_expenses = db_manager.get_individual_expenses_for_dashboard(
        user_id=profile_id,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )

    # Fetch categories
    categories_result = db_manager.get_categories()
    categories = categories_result.get("categories", [])

    if not categories:
        st.warning("No categories found. Please create categories first.")
        return

    # Process expenses data with DataFrame
    if not individual_expenses:
        st.info("No individual expenses found for the last 6 months.")
        return

    expenses_df = pd.DataFrame(individual_expenses)

    # Ensure date is in datetime format
    if "date" in expenses_df.columns:
        expenses_df["date"] = pd.to_datetime(expenses_df["date"])

    # Display stacked bar chart
    fig = create_individual_expense_chart(expenses_df, categories)
    st.plotly_chart(fig, use_container_width=True)


def display_dashboard() -> None:
    """Display the expenses dashboard with tabs for shared and individual expenses."""
    st.title("Expenses Dashboard")

    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to view the dashboard.")
        return

    # Create tabs for shared and individual dashboards
    tab1, tab2 = st.tabs(["Shared Expenses", "Individual Expenses"])

    # Display shared dashboard in first tab
    with tab1:
        st.header("Shared Expenses")
        st.write(
            "This chart shows expenses shared among all users by category over time."
        )
        display_shared_dashboard()

    # Display individual dashboard in second tab
    with tab2:
        st.header("Individual Expenses")
        st.write("This chart shows your personal expenses by category over time.")
        display_individual_dashboard()

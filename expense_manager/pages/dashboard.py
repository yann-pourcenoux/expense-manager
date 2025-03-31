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
from expense_manager.utils.analytics import prepare_expense_data
from expense_manager.utils.models import format_currency


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

    # Filter for shared expenses only
    shared_expenses = expenses_df[expenses_df["is_shared"]].copy()

    if shared_expenses.empty:
        # Create empty chart with message
        fig = go.Figure()
        fig.update_layout(title="No shared expense data available")
        return fig

    # Add month column
    shared_expenses["month"] = shared_expenses["date"].dt.strftime("%Y-%m")

    # Group by month and category
    monthly_category_expenses = (
        shared_expenses.groupby(["month", "category_id"])["amount"].sum().reset_index()
    )

    # Get unique months and sort them
    months = sorted(monthly_category_expenses["month"].unique())

    # Limit to last 6 months if there are more than 6
    if len(months) > 6:
        months = months[-6:]
        monthly_category_expenses = monthly_category_expenses[
            monthly_category_expenses["month"].isin(months)
        ]

    # Create the figure
    fig = go.Figure()

    # Add a trace for each category
    for cat in categories:
        cat_id = cat["id"]
        cat_name = cat["name"]
        cat_color = cat["color"]

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

        # Add the trace
        fig.add_trace(
            go.Bar(
                x=cat_data_complete["month"],
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


def display_dashboard() -> None:
    """Display the shared expenses dashboard."""
    st.title("Shared Expenses Dashboard")

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
    expenses_result = db_manager.get_shared_expenses_for_dashboard(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )

    if "error" in expenses_result:
        st.error(f"Error fetching expenses: {expenses_result['error']}")
        return

    expenses = expenses_result.get("expenses", [])

    # Fetch categories
    categories_result = db_manager.get_categories()
    categories = categories_result.get("categories", [])

    if not categories:
        st.warning("No categories found. Please create categories first.")
        return

    # Process expenses data
    expenses_df = prepare_expense_data(expenses)

    if expenses_df.empty:
        st.info("No shared expenses found for the last 6 months.")
        return

    # Display summary metrics
    st.subheader("Shared Expenses Summary (Last 6 Months)")

    total_shared = expenses_df["amount"].sum()

    # Calculate total by household member
    if "payer_id" in expenses_df.columns:
        payer_totals = expenses_df.groupby("payer_id")["amount"].sum()

        # Get profile names for payers
        payer_names = {}
        for payer_id in payer_totals.index:
            profile_result = db_manager.get_profile(str(payer_id))
            if "profile" in profile_result:
                payer_names[payer_id] = profile_result["profile"]["display_name"]
            else:
                payer_names[payer_id] = f"User {payer_id}"

    # Display metrics
    metrics_cols = st.columns(3)

    with metrics_cols[0]:
        st.metric("Total Shared Expenses", format_currency(total_shared))

    with metrics_cols[1]:
        avg_monthly = total_shared / max(
            1, len(expenses_df["date"].dt.strftime("%Y-%m").unique())
        )
        st.metric("Avg. Monthly Shared Expenses", format_currency(avg_monthly))

    with metrics_cols[2]:
        avg_per_expense = total_shared / len(expenses_df)
        st.metric("Avg. Shared Expense Amount", format_currency(avg_per_expense))

    # Display stacked bar chart
    st.subheader("Last 6 Months of Shared Expenses by Category")
    fig = create_monthly_category_chart(expenses_df, categories)
    st.plotly_chart(fig, use_container_width=True)

    # Display detailed breakdown by household member
    st.subheader("Expenses by Household Member")
    member_cols = st.columns(len(payer_totals))

    for i, (payer_id, total) in enumerate(payer_totals.items()):
        with member_cols[i % len(member_cols)]:
            st.metric(
                payer_names.get(payer_id, f"User {payer_id}"), format_currency(total)
            )
            percentage = (total / total_shared) * 100
            st.caption(f"{percentage:.1f}% of shared expenses")

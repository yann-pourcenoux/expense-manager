"""Flow visualization page for expense manager.

This module provides a Streamlit page for visualizing money flow
from income sources through categories to individual expenses using a Sankey diagram.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from expense_manager.db.db_manager import DatabaseManager
from expense_manager.utils.models import format_currency


def create_sankey_diagram(
    income_df: pd.DataFrame, expenses_df: pd.DataFrame, categories: List[Dict[str, Any]]
) -> go.Figure:
    """Create a Sankey diagram showing flow from income to categories to expenses.

    Args:
        income_df (pd.DataFrame): DataFrame of monthly income
        expenses_df (pd.DataFrame): DataFrame of individual expenses
        categories (List[Dict[str, Any]]): List of categories

    Returns:
        go.Figure: Plotly figure with Sankey diagram
    """
    if income_df.empty or expenses_df.empty:
        # Create empty figure with message
        fig = go.Figure()
        fig.update_layout(title="No data available for flow visualization")
        return fig

    # Create category mapping
    category_map = {cat["id"]: cat["name"] for cat in categories}

    # Prepare data for Sankey diagram
    # We need: source indices, target indices, and values for each flow

    # Start with empty lists
    source_indices = []
    target_indices = []
    values = []
    labels = []

    # Define color palette for categories
    # Vibrant colors with good contrast
    color_palette = [
        "#1f77b4",  # Blue
        "#ff7f0e",  # Orange
        "#2ca02c",  # Green
        "#d62728",  # Red
        "#9467bd",  # Purple
        "#8c564b",  # Brown
        "#e377c2",  # Pink
        "#7f7f7f",  # Gray
        "#bcbd22",  # Olive
        "#17becf",  # Cyan
    ]

    # Node colors will be assigned based on category
    node_colors = []
    link_colors = []

    # Add income node (will be index 0)
    income_total = income_df["amount"].sum()
    labels.append(f"Income (Total: {format_currency(income_total)})")
    node_colors.append("#3366cc")  # Blue for income

    # Calculate expenses total
    expenses_total = expenses_df["split_amount"].sum() if not expenses_df.empty else 0

    # Calculate money left
    money_left = income_total - expenses_total

    # Add category nodes (starting from index 1)
    category_indices = {}
    category_colors = {}

    for i, cat_id in enumerate(expenses_df["category_id"].unique()):
        if pd.isna(cat_id):
            cat_name = "Uncategorized"
        else:
            cat_name = category_map.get(cat_id, f"Category {cat_id}")

        label_index = i + 1
        category_indices[cat_id] = label_index

        # Assign color from palette (cycling if needed)
        cat_color = color_palette[i % len(color_palette)]
        category_colors[cat_id] = cat_color
        node_colors.append(cat_color)

        # Calculate total for this category
        cat_total = expenses_df[expenses_df["category_id"] == cat_id][
            "split_amount"
        ].sum()
        labels.append(f"{cat_name} ({format_currency(cat_total)})")

        # Add flow from income to this category
        source_indices.append(0)  # Income is always source 0
        target_indices.append(label_index)
        values.append(cat_total)

        # Add link color (semi-transparent category color)
        link_colors.append(
            cat_color.replace(")", ", 0.7)").replace("rgb", "rgba")
            if "rgb" in cat_color
            else _hex_to_rgba(cat_color, 0.7)
        )  # Add 70% opacity

    # Add "Money Left" node if there's money left
    if money_left > 0:
        money_left_idx = len(labels)
        labels.append(f"Money Left ({format_currency(money_left)})")
        node_colors.append("#66cc99")  # Green for money left

        # Add flow from income to money left
        source_indices.append(0)  # Income is source 0
        target_indices.append(money_left_idx)
        values.append(money_left)
        link_colors.append("rgba(102, 204, 153, 0.7)")  # Semi-transparent green

    # Add expense nodes and flows from categories to expenses
    # Group expenses with the same name to simplify diagram
    grouped_expenses = (
        expenses_df.groupby(["name", "category_id"])["split_amount"].sum().reset_index()
    )

    # Add expense nodes (after categories)
    expense_start_idx = len(labels)
    for i, row in grouped_expenses.iterrows():
        exp_name = row["name"]
        cat_id = row["category_id"]
        amount = row["split_amount"]

        # Add expense node
        expense_idx = expense_start_idx + i
        labels.append(f"{exp_name} ({format_currency(amount)})")

        # Use a lighter shade of the parent category color
        if pd.isna(cat_id):
            node_colors.append("#cccccc")  # Gray for uncategorized
        else:
            cat_color = category_colors.get(cat_id, "#cccccc")
            # Create a lighter version of the category color
            if cat_color.startswith("#"):
                # Convert hex to rgba with opacity for a lighter shade
                node_colors.append(cat_color)
            else:
                node_colors.append(cat_color)

        # Add flow from category to expense
        source_indices.append(category_indices[cat_id])
        target_indices.append(expense_idx)
        values.append(amount)

        # Use the same color as the category-to-income link
        if pd.isna(cat_id):
            link_colors.append("rgba(204, 204, 204, 0.7)")  # Semi-transparent gray
        else:
            cat_color = category_colors.get(cat_id, "#cccccc")
            if cat_color.startswith("#"):
                # Convert hex to rgba with transparency
                link_colors.append(_hex_to_rgba(cat_color, 0.7))
            else:
                # Add transparency to rgb color
                link_colors.append(
                    cat_color.replace(")", ", 0.7)").replace("rgb", "rgba")
                )

    # Create the Sankey diagram
    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=20,
                    thickness=30,
                    line=dict(color="black", width=0.5),
                    label=labels,
                    color=node_colors,
                ),
                link=dict(
                    source=source_indices,
                    target=target_indices,
                    value=values,
                    color=link_colors,
                ),
                arrangement="snap",  # Use snap arrangement for better spacing
                textfont=dict(family="Arial, sans-serif", size=14, color="black"),
            )
        ]
    )

    fig.update_layout(
        title="Money Flow: Income → Categories → Expenses",
        font=dict(family="Arial, sans-serif", size=14, color="black"),
        height=800,
        margin=dict(l=25, r=25, b=25, t=50),
    )

    return fig


def display_flow_page() -> None:
    """Display the flow visualization page."""
    st.title("Money Flow Visualization")

    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to view the flow visualization.")
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

    # Calculate date range for the current month
    today = datetime.now()

    # Default to current month
    datetime(today.year, today.month, 1).date()
    if today.month == 12:
        last_day = datetime(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(today.year, today.month + 1, 1) - timedelta(days=1)
    last_day = last_day.date()

    # Allow user to select month
    st.subheader("Select Month")

    # Create past 12 months options
    months = []
    for i in range(12):
        month_date = today.replace(day=1) - timedelta(days=i * 30)  # Approximate
        months.append(
            (
                datetime(month_date.year, month_date.month, 1).date(),
                datetime(
                    month_date.year + (1 if month_date.month == 12 else 0),
                    1 if month_date.month == 12 else month_date.month + 1,
                    1,
                ).date()
                - timedelta(days=1),
            )
        )

    # Format month options for selection
    month_options = [f"{m[0].strftime('%B %Y')}" for m in months]

    selected_month_idx = st.selectbox(
        "Month",
        range(len(month_options)),
        format_func=lambda x: month_options[x],
        index=0,
    )

    # Set date range based on selection
    start_date = months[selected_month_idx][0]
    end_date = months[selected_month_idx][1]

    st.info(f"Showing data for: {start_date.strftime('%B %Y')}")

    # Fetch income data
    income_data = db_manager.get_monthly_income(
        user_id=profile_id, month_date=datetime(start_date.year, start_date.month, 1)
    )

    # Fetch individual expenses
    individual_expenses = db_manager.get_individual_expenses_for_dashboard(
        user_id=profile_id,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )

    # Fetch categories
    categories_result = db_manager.get_categories()
    categories = categories_result.get("categories", [])

    # Process data
    income_df = (
        pd.DataFrame([income_data.get("income")])
        if income_data.get("income")
        else pd.DataFrame(
            {"amount": [0], "month_date": [start_date.strftime("%Y-%m-01")]}
        )
    )

    if not individual_expenses:
        st.info("No expense data found for the selected month.")
        expenses_df = pd.DataFrame()
    else:
        expenses_df = pd.DataFrame(individual_expenses)

    # Create the Sankey diagram
    fig = create_sankey_diagram(income_df, expenses_df, categories)

    # Display the diagram
    st.plotly_chart(fig, use_container_width=True)

    # Display data tables for reference
    with st.expander("View Data"):
        if not income_df.empty:
            st.subheader("Income Data")
            st.dataframe(income_df)

        if not expenses_df.empty:
            st.subheader("Expense Data")
            expenses_display = expenses_df[
                ["name", "date", "split_amount", "category_name"]
            ].copy()
            expenses_display["date"] = pd.to_datetime(
                expenses_display["date"]
            ).dt.strftime("%Y-%m-%d")
            expenses_display["split_amount"] = expenses_display["split_amount"].apply(
                format_currency
            )
            st.dataframe(expenses_display)


def _hex_to_rgba(hex_color: str, alpha: float = 0.7) -> str:
    """Convert hex color to rgba format with transparency.

    Args:
        hex_color: Hex color code (e.g. '#FF0000')
        alpha: Alpha transparency value (0-1)

    Returns:
        RGBA color string
    """
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"

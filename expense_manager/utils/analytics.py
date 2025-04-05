"""Analytics utilities for expense data.

This module provides utilities for analyzing and visualizing expense data.
It includes functions for summarizing expenses and generating visualizations.
"""

from typing import Any, Dict, List, Set

import pandas as pd
import plotly.graph_objects as go

from expense_manager.utils.models import format_currency


def prepare_expense_data(
    expenses: List[Dict[str, Any]],
    profile_names: Dict[int, str] = None,
    category_map: Dict[str, str] = None,
) -> pd.DataFrame:
    """Convert expenses list to pandas DataFrame with proper data types and formatting.

    Args:
        expenses (List[Dict[str, Any]]): List of expense records
        profile_names (Dict[int, str], optional): Mapping of profile IDs to display
            names. Defaults to None.
        category_map (Dict[str, str], optional): Mapping of category IDs to names.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame with expenses data and formatting applied
    """
    if not expenses:
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(expenses)

    # Convert date strings to datetime objects
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])

    # Ensure amount is float
    if "amount" in df.columns:
        df["amount"] = df["amount"].astype(float)

    # Format data for display if mappings are provided
    display_df = df.copy()

    # Add category names if category map is provided
    if category_map and "category_id" in display_df.columns:
        display_df["category"] = display_df["category_id"].map(category_map)

    # Format amount
    if "amount" in display_df.columns:
        display_df["amount_formatted"] = display_df["amount"].map(format_currency)

    # Add shared indicator
    if "is_shared" in display_df.columns:
        display_df["shared"] = display_df["is_shared"].map({1: "Yes", 0: "No"})

    # Add profile information if profile names are provided
    if profile_names:
        # Add payer information
        if "payer_id" in display_df.columns:
            display_df["payer"] = display_df["payer_id"].map(profile_names)
            display_df["payer"] = display_df["payer"].fillna("Unknown")

        # Add reporter information
        if "reporter_id" in display_df.columns:
            display_df["reporter"] = display_df["reporter_id"].map(profile_names)
            display_df["reporter"] = display_df["reporter"].fillna("Unknown")

        # Add beneficiary information
        if "beneficiary_id" in display_df.columns:
            display_df["beneficiary"] = display_df["beneficiary_id"].map(profile_names)
            # For shared expenses or when beneficiary is not set, show appropriate text
            if "is_shared" in display_df.columns:
                display_df.loc[display_df["is_shared"] == 1, "beneficiary"] = "Shared"
            display_df["beneficiary"] = display_df["beneficiary"].fillna(
                "Same as payer"
            )

    return display_df


def summarize_expenses(
    expenses_df: pd.DataFrame,
    categories: List[Dict[str, Any]],
    is_split_view: bool = False,
) -> Dict[str, Any]:
    """Summarize expenses for visualization.

    Args:
        expenses_df (pd.DataFrame): DataFrame of expenses
        categories (List[Dict[str, Any]]): List of categories
        is_split_view (bool, optional): Whether to use the split amount.
            Defaults to False.

    Returns:
        Dict[str, Any]: Summary dictionary with total and breakdowns
    """
    if expenses_df.empty:
        return {"total": 0.0, "by_category": [], "by_date": []}

    # Determine the amount column to use
    amount_column = "split_amount" if is_split_view else "amount"

    # If the split_amount doesn't exist, fallback to amount
    if is_split_view and "split_amount" not in expenses_df.columns:
        amount_column = "amount"

    # Calculate total
    total = expenses_df[amount_column].sum()

    # Category breakdown
    by_category = []
    if "category_id" in expenses_df.columns:
        category_map = {cat["id"]: cat for cat in categories}
        category_data = (
            expenses_df.groupby("category_id")[amount_column].sum().reset_index()
        )

        for _, row in category_data.iterrows():
            category = category_map.get(row["category_id"], {})
            if category:
                by_category.append(
                    {
                        "id": row["category_id"],
                        "name": category.get("name", "Unknown"),
                        "color": category.get("color", "#000000"),
                        "amount": float(row[amount_column]),
                        "percentage": float(row[amount_column] / total * 100),
                    }
                )

    # Date breakdown
    by_date = []
    if "date" in expenses_df.columns:
        date_data = expenses_df.groupby(expenses_df["date"].dt.date)[
            amount_column
        ].sum()
        date_data = date_data.sort_index()  # Sort by date

        for date, amount in date_data.items():
            by_date.append(
                {
                    "date": (
                        str(date)
                        if not hasattr(date, "strftime")
                        else date.strftime("%Y-%m-%d")
                    ),
                    "amount": float(amount),
                }
            )

    return {
        "total": float(total),
        "by_category": by_category,
        "by_date": by_date,
    }


def create_category_pie_chart(summary: Dict[str, Any]) -> go.Figure:
    """Create a pie chart of expenses by category.

    Args:
        summary (Dict[str, Any]): Expense summary dictionary

    Returns:
        go.Figure: Plotly figure object containing the pie chart
    """
    by_category = summary.get("by_category", [])

    if not by_category:
        # Create empty chart with message
        fig = go.Figure(go.Pie(labels=["No data"], values=[1]))
        fig.update_traces(textinfo="none")
        fig.update_layout(title="No expense data available")
        return fig

    labels = [item["name"] for item in by_category]
    values = [item["amount"] for item in by_category]

    # Use category colors if available, otherwise let Plotly handle the colors
    colors = [item.get("color", None) for item in by_category]
    # Filter out None values
    colors_list: List[Any] = []
    if colors and all(colors):
        colors_list = colors

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            # Use explicit colors if available
            marker=dict(colors=colors_list) if colors_list else None,
            textinfo="label+percent",
            hoverinfo="label+value",
            hole=0.4,
        )
    )

    fig.update_layout(
        title="Expenses by Category",
        showlegend=True,
    )

    return fig


def create_time_series_chart(summary: Dict[str, Any]) -> go.Figure:
    """Create a time series chart of expenses over time.

    Args:
        summary (Dict[str, Any]): Expense summary dictionary

    Returns:
        go.Figure: Plotly figure object containing the time series chart
    """
    by_date = summary.get("by_date", [])

    if not by_date:
        # Create empty chart with message
        fig = go.Figure()
        fig.update_layout(title="No expense data available")
        return fig

    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(by_date)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["amount"],
            mode="lines+markers",
            name="Daily Expenses",
            line=dict(width=2, color="#1f77b4"),
            marker=dict(size=6, color="#1f77b4"),
        )
    )

    # Add 7-day moving average if enough data
    if len(df) >= 7:
        df["7_day_avg"] = df["amount"].rolling(window=7, min_periods=1).mean()
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["7_day_avg"],
                mode="lines",
                name="7-day Average",
                line=dict(width=2, color="#ff7f0e", dash="dash"),
            )
        )

    fig.update_layout(
        title="Expenses Over Time",
        xaxis_title="Date",
        yaxis_title="Amount",
        hovermode="x unified",
    )

    return fig


def create_income_vs_expenses_chart(
    expense_summary: Dict[str, Any], income_data: List[Dict[str, Any]]
) -> go.Figure:
    """Create a bar chart comparing income and expenses by month.

    Args:
        expense_summary (Dict[str, Any]): Expense summary with by_date data
        income_data (List[Dict[str, Any]]): Monthly income data

    Returns:
        go.Figure: Plotly figure with income vs expenses chart
    """
    # Create a blank figure if no data
    if not expense_summary.get("by_date") and not income_data:
        fig = go.Figure()
        fig.update_layout(title="No income or expense data available")
        return fig

    # Convert expense data by date to monthly totals
    expense_dates = expense_summary.get("by_date", [])

    # Create DataFrame for expenses
    if expense_dates:
        expense_df = pd.DataFrame(expense_dates)
        expense_df["date"] = pd.to_datetime(expense_df["date"])
        expense_df["month"] = expense_df["date"].dt.strftime("%Y-%m")
        monthly_expenses = expense_df.groupby("month")["amount"].sum().reset_index()
    else:
        # Create empty DataFrame if no expenses
        monthly_expenses = pd.DataFrame(columns=["month", "amount"])

    # Create DataFrame for income
    if income_data:
        income_df = pd.DataFrame(income_data)
        income_df["month_date"] = pd.to_datetime(income_df["month_date"])
        income_df["month"] = income_df["month_date"].dt.strftime("%Y-%m")
        monthly_income = income_df[["month", "amount"]]
    else:
        # Create empty DataFrame if no income
        monthly_income = pd.DataFrame(columns=["month", "amount"])

    # Combine all months from both datasets
    all_months: Set[str] = set(
        monthly_expenses["month"].tolist() + monthly_income["month"].tolist()
    )
    all_months_list = sorted(list(all_months))

    # Create complete DataFrames with all months
    complete_months_df = pd.DataFrame({"month": all_months_list})

    # Merge with actual data
    expenses_complete = complete_months_df.merge(
        monthly_expenses, on="month", how="left"
    ).fillna(0)
    income_complete = complete_months_df.merge(
        monthly_income, on="month", how="left"
    ).fillna(0)

    # Create the figure
    fig = go.Figure()

    # Add expense bars
    fig.add_trace(
        go.Bar(
            x=expenses_complete["month"],
            y=expenses_complete["amount"],
            name="Expenses",
            marker_color="#ff7f0e",
        )
    )

    # Add income bars
    fig.add_trace(
        go.Bar(
            x=income_complete["month"],
            y=income_complete["amount"],
            name="Income",
            marker_color="#2ca02c",
        )
    )

    # Add savings line (income - expenses)
    savings = income_complete["amount"] - expenses_complete["amount"]
    fig.add_trace(
        go.Scatter(
            x=complete_months_df["month"],
            y=savings,
            mode="lines+markers",
            name="Savings",
            line=dict(width=3, color="#1f77b4"),
            marker=dict(size=8),
        )
    )

    fig.update_layout(
        title="Monthly Income vs Expenses",
        xaxis_title="Month",
        yaxis_title="Amount",
        barmode="group",
        hovermode="x unified",
    )

    return fig


def create_split_expenses_summary(
    expenses_df: pd.DataFrame,
    current_user_id: int,
) -> dict:
    """Create a summary of split and beneficiary expenses.

    Args:
        expenses_df (pd.DataFrame): DataFrame containing expense records
        current_user_id (int): ID of the current user

    Returns:
        dict: Summary of expenses including:
            - total_shared: Total amount of shared expenses
            - total_paid: Total amount paid by current user
            - total_owed: Total amount owed by current user
            - by_user: List of balances per user
    """
    if expenses_df.empty:
        return {
            "total_shared": 0,
            "total_paid": 0,
            "total_owed": 0,
            "by_user": [],
        }

    # Initialize summary
    summary = {
        "total_shared": 0,
        "total_paid": 0,
        "total_owed": 0,
        "by_user": [],
    }

    # Create a user balance dictionary to track amounts
    user_balances = {}

    # Process shared expenses
    shared_expenses = expenses_df[expenses_df["is_shared"] is True].copy()
    if not shared_expenses.empty:
        # Calculate total shared expenses
        summary["total_shared"] = shared_expenses["amount"].sum()

        # Calculate amounts for shared expenses
        for _, expense in shared_expenses.iterrows():
            amount = expense["amount"]
            payer_id = expense["payer_id"]

            # Check if we have the new split_amounts structure
            if "split_amounts" in expense and isinstance(
                expense["split_amounts"], dict
            ):
                # The new structure provides a dictionary of user_id -> amount
                split_amounts = expense["split_amounts"]

                # If current user is the payer
                if payer_id == current_user_id:
                    summary["total_paid"] += amount

                    # Each participant owes their split amount
                    for participant_id, split_amount in split_amounts.items():
                        # Convert keys from string to int if needed (JSON conversion
                        # issue)
                        user_id = (
                            int(participant_id)
                            if isinstance(participant_id, str)
                            else participant_id
                        )

                        if user_id != current_user_id:
                            user_balances.setdefault(
                                user_id,
                                {
                                    "paid_for_you": 0,
                                    "you_paid_for_them": 0,
                                },
                            )
                            user_balances[user_id]["you_paid_for_them"] += float(
                                split_amount
                            )

                # If current user is a participant but not the payer
                elif (
                    str(current_user_id) in split_amounts
                    or current_user_id in split_amounts
                ):
                    # Get current user's split amount
                    user_key = (
                        str(current_user_id)
                        if str(current_user_id) in split_amounts
                        else current_user_id
                    )
                    user_split = float(split_amounts[user_key])
                    summary["total_owed"] += user_split

                    # Record what the payer paid for the current user
                    user_balances.setdefault(
                        payer_id,
                        {
                            "paid_for_you": 0,
                            "you_paid_for_them": 0,
                        },
                    )
                    user_balances[payer_id]["paid_for_you"] += user_split

            # Fallback to the old method if split_amounts is not available
            else:
                # Determine the number of participants - fallback to hardcoded 2
                # if not available
                split_count = expense.get("split_count", 2)
                split_amount = amount / split_count

                # If current user is the payer
                if payer_id == current_user_id:
                    summary["total_paid"] += amount
                    # Each other participant owes the split amount
                    for participant_id in range(split_count):
                        if participant_id != current_user_id:
                            user_balances.setdefault(
                                participant_id,
                                {
                                    "paid_for_you": 0,
                                    "you_paid_for_them": 0,
                                },
                            )
                            user_balances[participant_id]["you_paid_for_them"] += (
                                split_amount
                            )
                # If current user is a participant but not the payer
                elif current_user_id in range(split_count):
                    summary["total_owed"] += split_amount
                    user_balances.setdefault(
                        payer_id,
                        {
                            "paid_for_you": 0,
                            "you_paid_for_them": 0,
                        },
                    )
                    user_balances[payer_id]["paid_for_you"] += split_amount

    # Process non-shared expenses with different beneficiary and payer
    non_shared_expenses = expenses_df[
        (expenses_df["is_shared"] is False)
        & (expenses_df["beneficiary_id"] != expenses_df["payer_id"])
    ].copy()

    if not non_shared_expenses.empty:
        for _, expense in non_shared_expenses.iterrows():
            amount = expense["amount"]
            payer_id = expense["payer_id"]
            beneficiary_id = expense["beneficiary_id"]

            # Skip if either payer or beneficiary is None
            if pd.isna(payer_id) or pd.isna(beneficiary_id):
                continue

            # If current user paid for someone else
            if payer_id == current_user_id:
                summary["total_paid"] += amount
                user_balances.setdefault(
                    beneficiary_id,
                    {
                        "paid_for_you": 0,
                        "you_paid_for_them": 0,
                    },
                )
                user_balances[beneficiary_id]["you_paid_for_them"] += amount

            # If someone else paid for current user
            elif beneficiary_id == current_user_id:
                summary["total_owed"] += amount
                user_balances.setdefault(
                    payer_id,
                    {
                        "paid_for_you": 0,
                        "you_paid_for_them": 0,
                    },
                )
                user_balances[payer_id]["paid_for_you"] += amount

    # Calculate net balances for each user
    for user_id, balance in user_balances.items():
        net_balance = balance["paid_for_you"] - balance["you_paid_for_them"]
        summary["by_user"].append(
            {
                "user_id": user_id,
                "paid_for_you": balance["paid_for_you"],
                "you_paid_for_them": balance["you_paid_for_them"],
                "net_balance": net_balance,
            }
        )

    return summary


def create_income_bar_chart(income_data: List[Dict[str, Any]]) -> go.Figure:
    """Create a bar chart of monthly income."""
    if not income_data:
        # Create empty chart with message
        fig = go.Figure()
        fig.update_layout(title="No income data available")
        return fig

    # Convert to DataFrame
    df = pd.DataFrame(income_data)
    df["month_date"] = pd.to_datetime(df["month_date"])
    df = df.sort_values("month_date")

    # Format dates for display
    df["month_display"] = df["month_date"].dt.strftime("%b %Y")

    # Create the chart
    fig = go.Figure(
        go.Bar(
            x=df["month_display"],
            y=df["amount"],
            marker_color="#2ca02c",
            name="Monthly Income",
        )
    )

    fig.update_layout(
        title="Monthly Income History",
        xaxis_title="Month",
        yaxis_title="Amount",
        hovermode="x unified",
    )

    return fig


def create_individual_expense_chart(
    expenses_df: pd.DataFrame, categories: List[Dict[str, Any]]
) -> go.Figure:
    """Create a stacked bar chart of individual expenses by category per month.

    This function takes expenses data from the expenses_split table and creates a
    stacked bar chart showing how much was spent in each category per month.

    Args:
        expenses_df (pd.DataFrame): DataFrame of expenses with split_amount
        categories (List[Dict[str, Any]]): List of categories

    Returns:
        go.Figure: Plotly figure with stacked bar chart
    """
    if expenses_df.empty:
        # Create empty chart with message
        fig = go.Figure()
        fig.update_layout(title="No individual expense data available")
        return fig

    # Make a copy to avoid modifying the original
    expenses = expenses_df.copy()

    # Add month column for underlying data (YYYY-MM format)
    expenses["month"] = pd.to_datetime(expenses["date"]).dt.strftime("%Y-%m")

    # Add a display month column for better readability (e.g., Jan 2023)
    expenses["display_month"] = pd.to_datetime(expenses["date"]).dt.strftime("%b %Y")

    # Group by month and category
    monthly_category_expenses = (
        expenses.groupby(["month", "category_id"])["split_amount"].sum().reset_index()
    )

    # Get unique months and sort them
    months = sorted(monthly_category_expenses["month"].unique())

    # Create a mapping from YYYY-MM to display format (Month Year)
    month_display_mapping = {}
    for _, row in expenses.drop_duplicates("month").iterrows():
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

    # Create a category ID to name mapping
    {cat["id"]: cat["name"] for cat in categories}

    # Add a trace for each category
    for i, cat_id in enumerate(monthly_category_expenses["category_id"].unique()):
        # Find the category object
        cat_info = next((c for c in categories if c["id"] == cat_id), None)

        if cat_info:
            cat_name = cat_info["name"]
            cat_color = cat_info.get("color", default_colors[i % len(default_colors)])
        else:
            cat_name = f"Category {cat_id}"
            cat_color = default_colors[i % len(default_colors)]

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
                y=cat_data_complete["split_amount"],
                name=cat_name,
                marker_color=cat_color,
            )
        )

    # Configure the layout
    fig.update_layout(
        title="Last 6 Months of Individual Expenses by Category",
        xaxis_title="Month",
        yaxis_title="Amount",
        barmode="stack",
        hovermode="x unified",
        legend_title="Categories",
    )

    return fig

"""Analytics utilities for expense data.

This module provides utilities for analyzing and visualizing expense data.
It includes functions for summarizing expenses and generating visualizations.
"""

from typing import Any, Dict, List, Set

import pandas as pd
import plotly.graph_objects as go


def prepare_expense_data(expenses: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert expenses list to pandas DataFrame with proper data types.

    Args:
        expenses (List[Dict[str, Any]]): List of expense records

    Returns:
        pd.DataFrame: DataFrame with expenses data
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

    return df


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
                    "date": date.strftime("%Y-%m-%d"),
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
    colors = colors if all(colors) else None

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            # Use explicit colors if available
            marker=dict(colors=colors) if colors else None,
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
    split_expenses_df: pd.DataFrame, user_id: str, users_map: Dict[str, str]
) -> Dict[str, Any]:
    """Generate summary statistics for split expenses.

    Args:
        split_expenses_df (pd.DataFrame): DataFrame with split expenses
        user_id (str): Current user ID
        users_map (Dict[str, str]): Map of user IDs to emails/names

    Returns:
        Dict[str, Any]: Dictionary with summary data
    """
    if split_expenses_df.empty:
        return {
            "total_shared": 0.0,
            "total_paid": 0.0,
            "total_owed": 0.0,
            "by_user": [],
        }

    # Filter to shared expenses only
    shared_df = split_expenses_df[split_expenses_df["is_shared"] is True].copy()

    if shared_df.empty:
        return {
            "total_shared": 0.0,
            "total_paid": 0.0,
            "total_owed": 0.0,
            "by_user": [],
        }

    # Calculate the per-person share for each expense
    shared_df["per_person_amount"] = shared_df["amount"] / shared_df["split_count"]

    # Total of all shared expenses
    total_shared = shared_df["amount"].sum()

    # Total paid by current user (expenses where user is payer)
    paid_df = shared_df[shared_df["payer_id"] == user_id]
    total_paid = paid_df["amount"].sum()

    # Total owed by current user
    # (sum of per-person amounts for expenses where user is not payer)
    owed_df = shared_df[shared_df["payer_id"] != user_id]
    total_owed = owed_df["per_person_amount"].sum()

    # Breakdown by user
    by_user = []
    for payer_id, payer_expenses in shared_df.groupby("payer_id"):
        if payer_id == user_id:
            continue  # Skip self

        # Calculate how much this user paid for the current user
        paid_for_current_user = payer_expenses["per_person_amount"].sum()

        # Find expenses where current user paid for this user
        current_paid_for_user = shared_df[
            (shared_df["payer_id"] == user_id) & (shared_df["is_shared"] is True)
        ]["per_person_amount"].sum()

        # Net balance
        # (positive means current user owes, negative means user owes current user)
        net_balance = paid_for_current_user - current_paid_for_user

        by_user.append(
            {
                "user_id": payer_id,
                "email": users_map.get(str(payer_id), "Unknown User"),
                "paid_for_you": float(paid_for_current_user),
                "you_paid_for_them": float(current_paid_for_user),
                "net_balance": float(net_balance),
            }
        )

    return {
        "total_shared": float(total_shared),
        "total_paid": float(total_paid),
        "total_owed": float(total_owed),
        "by_user": by_user,
    }

"""Income management page.

This module provides a Streamlit page for managing income records, including
adding, updating, and viewing monthly income.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from expense_manager.db.db_manager import DatabaseManager
from expense_manager.pages.expenses import get_profile_id
from expense_manager.utils.analytics import create_income_bar_chart
from expense_manager.utils.models import format_currency


def display_income_manager() -> None:
    """Display the income management interface."""
    st.title("Income Management")

    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to manage your income.")
        return

    # Initialize database manager
    db_manager = DatabaseManager()

    # Get user UUID from session
    user_uuid = (
        st.session_state.user.id
        if hasattr(st.session_state.user, "id")
        else st.session_state.user["id"]
    )

    # Get profile ID from user UUID
    profile_id = get_profile_id(db_manager, user_uuid)
    if profile_id is None:
        st.error("Could not find your profile. Please try logging in again.")
        return

    # Tabs for different actions
    tab1, tab2 = st.tabs(["Set Monthly Income", "Income History"])

    with tab1:
        display_set_income_form(db_manager, profile_id)

    with tab2:
        display_income_history(db_manager, profile_id)


def display_set_income_form(db_manager: DatabaseManager, profile_id: int) -> None:
    """Display form for setting or updating monthly income.

    Args:
        db_manager (DatabaseManager): Database manager instance
        profile_id (int): ID of the current user's profile
    """
    st.header("Set Monthly Income")

    # Get the current month as default
    current_month = datetime.now().replace(day=1)

    # Let user select month
    selected_month = st.date_input(
        "Select Month",
        value=current_month,
        help="Income will be recorded for the selected month",
    )

    # Ensure the day is set to the 1st of the month
    selected_month = selected_month.replace(day=1)

    # Check if there's already income for this month
    income_result = db_manager.get_monthly_income(profile_id, selected_month)
    existing_income = income_result.get("income")

    if "error" in income_result:
        st.error(f"Error retrieving income data: {income_result['error']}")

    # Create form for setting income
    with st.form("set_income_form"):
        # Income amount
        default_amount = float(existing_income["amount"]) if existing_income else 0.0
        income_amount = st.number_input(
            "Monthly Income",
            min_value=0.0,
            value=default_amount,
            format="%.2f",
            help="Set your total income for the selected month",
        )

        # Submit button
        submitted = st.form_submit_button("Save Income")

        if submitted:
            # Process the form submission
            success = db_manager.set_monthly_income(
                user_id=profile_id,
                amount=income_amount,
                month_date=selected_month,
            )

            if "error" in success:
                st.error(f"Error saving income: {success['error']}")
            else:
                if existing_income:
                    st.success("Income updated successfully!")
                else:
                    st.success("Income saved successfully!")
                st.rerun()


def display_income_history(db_manager: DatabaseManager, profile_id: int) -> None:
    """Display income history and visualizations.

    Args:
        db_manager (DatabaseManager): Database manager instance
        profile_id (int): ID of the current user's profile
    """
    st.header("Income History")

    # Get income history
    history_result = db_manager.get_income_history(profile_id)

    if "error" in history_result:
        st.error(f"Error retrieving income history: {history_result['error']}")
        return

    income_data = history_result.get("income_history", [])

    if not income_data:
        st.info("No income history found. Set your monthly income to get started!")
        return

    # Create DataFrame for display
    income_df = pd.DataFrame(income_data)

    # Format for display
    display_df = income_df.copy()

    # Format date
    if "month_date" in display_df.columns:
        display_df["month"] = pd.to_datetime(display_df["month_date"]).dt.strftime(
            "%Y-%m"
        )

    # Format amount
    if "amount" in display_df.columns:
        display_df["amount"] = display_df["amount"].map(format_currency)

    # Select columns for display
    display_columns = ["month", "amount"]
    display_columns = [col for col in display_columns if col in display_df.columns]

    # Display the income history
    st.dataframe(display_df[display_columns], use_container_width=True)

    # Create and display the income bar chart
    chart = create_income_bar_chart(income_data)
    st.plotly_chart(chart, use_container_width=True)

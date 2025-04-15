"""User balances page.

This module provides a Streamlit page for viewing user balances, including
shared expenses, non-shared expenses, and transfers between users.
"""

import streamlit as st

from expense_manager.db.db_manager import DatabaseManager
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


def display_user_balances() -> None:
    """Display the user balances interface."""
    st.title("User Balances")

    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to view your balances.")
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

    # Get expenses for balance calculation
    expenses = db_manager.get_expenses_for_balance()

    # Compute the amount of shared expenses and how much each shared
    shared_paid_by_you = sum(
        [
            expense["amount"]
            for expense in expenses
            if expense["is_shared"] == 1 and expense["payer_id"] == profile_id
        ]
    )
    total_shared = sum(
        [expense["amount"] for expense in expenses if expense["is_shared"] == 1]
    )

    due_per_person = total_shared / 2
    shared_you_owe = due_per_person - shared_paid_by_you

    # Compute the balance for the non shared expenses
    paid_by_you = sum(
        [
            expense["amount"]
            for expense in expenses
            if expense["is_shared"] == 0 and expense["payer_id"] == profile_id
        ]
    )
    you_owe = sum(
        [
            expense["amount"]
            for expense in expenses
            if expense["is_shared"] == 0 and expense["beneficiary_id"] == profile_id
        ]
    )
    non_shared_you_owe = you_owe - paid_by_you

    # Get transfers
    transfers_result = db_manager.get_transfers()
    if "error" in transfers_result:
        st.error(f"Error getting transfers: {transfers_result['error']}")
        return

    transfers = transfers_result.get("transfers", [])

    # Calculate transfer amounts
    transfers_sent = sum(
        [
            transfer["amount"]
            for transfer in transfers
            if transfer["source_id"] == profile_id
        ]
    )
    transfers_received = sum(
        [
            transfer["amount"]
            for transfer in transfers
            if transfer["beneficiary_id"] == profile_id
        ]
    )
    transfer_balance = transfers_received - transfers_sent

    # Calculate total balance including transfers
    total_you_owe = shared_you_owe + non_shared_you_owe + transfer_balance

    # Display summary statistics
    # Row 1: Total shared expenses and your contribution
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        st.metric(
            "Total Shared Expenses",
            format_currency(total_shared),
        )
    with row1_col2:
        st.metric("Your contribution", format_currency(shared_paid_by_you))

    # Row 2: Payments between household partners
    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        st.metric("You paid for your household partner", format_currency(paid_by_you))
    with row2_col2:
        st.metric("Your household partner paid for you", format_currency(you_owe))

    # Row 3: Transfers
    row3_col1, row3_col2 = st.columns(2)
    with row3_col1:
        st.metric("Transfers you sent", format_currency(transfers_sent))
    with row3_col2:
        st.metric("Transfers you received", format_currency(transfers_received))

    # Row 4: Summary of who owes whom
    st.write("")  # Add some space between rows
    if total_you_owe > 0:
        st.metric("🔴 You owe your household partner", format_currency(total_you_owe))
    elif total_you_owe < 0:
        st.metric(
            "🟢 Your household partner owes you",
            format_currency(abs(total_you_owe)),
        )
    else:
        st.write("✅ Settled")

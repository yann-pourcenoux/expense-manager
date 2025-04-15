"""Expense management page.

This module provides a Streamlit page for managing expenses, including
adding, editing, and deleting expense records.
"""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from expense_manager.db.db_manager import DatabaseManager
from expense_manager.utils.analytics import (
    prepare_expense_data,
)
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


def display_expense_manager() -> None:
    """Display the expense management interface."""
    st.title("Manage Expenses")

    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to manage your expenses.")
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

    # Initialize session state if not exists
    if "expense_filter_start_date" not in st.session_state:
        st.session_state.expense_filter_start_date = (
            datetime.now() - timedelta(days=30)
        ).date()
    if "expense_filter_end_date" not in st.session_state:
        st.session_state.expense_filter_end_date = datetime.now().date()

    # Display expenses interface
    st.subheader("Expenses")
    tabs = st.tabs(["Add Expense", "View Expenses"])

    # Add Expense tab
    with tabs[0]:
        display_add_expense_form(db_manager, profile_id)

    # View Expenses tab
    with tabs[1]:
        display_expense_list(db_manager, profile_id)


def display_add_expense_form(db_manager: DatabaseManager, profile_id: int) -> None:
    """Display form for adding a new expense.

    Args:
        db_manager (DatabaseManager): Database manager instance
        profile_id (int): ID of the current user's profile
    """
    st.header("Add New Expense")

    # Get categories for dropdown
    categories_result = db_manager.get_categories()
    categories = categories_result.get("categories", [])

    # Get payment sources for dropdown
    payment_sources_result = db_manager.get_payment_sources(
        st.session_state.user.id
        if hasattr(st.session_state.user, "id")
        else st.session_state.user["id"]
    )
    payment_sources = payment_sources_result.get("payment_sources", [])

    if not categories:
        st.warning("No categories found. Please create categories first.")

        # Simple form to add a category
        with st.expander("Add Category"):
            category_name = st.text_input("Category Name")
            category_color = st.color_picker("Category Color", "#1f77b4")

            if st.button("Add Category"):
                if category_name:
                    result = db_manager.create_category(category_name, category_color)
                    if "error" in result:
                        st.error(f"Error creating category: {result['error']}")
                    else:
                        st.success(f"Category '{category_name}' created!")
                        st.rerun()  # Refresh to show the new category
                else:
                    st.warning("Please enter a category name")

        return

    if not payment_sources:
        st.warning("No payment sources found. Please add payment sources first.")
        return

    # Get category names for the dropdown
    category_options = {cat["name"]: cat["id"] for cat in categories}

    # Get payment source names for the dropdown
    payment_source_options = {ps["name"]: ps["id"] for ps in payment_sources}

    # Get user's profile to check favorite payment source
    profile_result = db_manager.get_profile(
        st.session_state.user.id
        if hasattr(st.session_state.user, "id")
        else st.session_state.user["id"]
    )
    profile = profile_result.get("profile", {})

    # Find default payment source name
    default_payment_source_name = None
    if profile.get("favorite_payment_source_id"):
        default_source = next(
            (
                ps
                for ps in payment_sources
                if ps["id"] == profile["favorite_payment_source_id"]
            ),
            None,
        )
        if default_source:
            default_payment_source_name = default_source["name"]

    # Get all profiles for payer selection
    profiles_result = db_manager.get_all_profiles()
    profiles = profiles_result.get("profiles", [])

    # Create a mapping of profile IDs to their details including display names
    profile_details = {}
    for p in profiles:
        profile_details[p["id"]] = {
            "profile_id": p["id"],
            "display_name": p["display_name"],
        }

    # Create options for the payer dropdown with display name
    payer_options = {}
    for profile_detail in profile_details.values():
        display_name = profile_detail["display_name"]
        profile_id_value = profile_detail["profile_id"]
        payer_options[display_name] = profile_id_value

    # Find the display option for current user
    current_user_option = next(
        (
            option
            for option, id_value in payer_options.items()
            if id_value == profile_id
        ),
        None,
    )

    # Default index for payer dropdown
    default_index = 0
    if current_user_option:
        default_index = list(payer_options.keys()).index(current_user_option)

    # Payer selection
    payer_option_list = (
        list(payer_options.keys()) if payer_options else ["No profiles available"]
    )

    # Create beneficiary dropdown options (reusing payer_options)
    beneficiary_option_list = (
        list(payer_options.keys()) if payer_options else ["No profiles available"]
    )

    # Default to the current user for beneficiary (as is common)
    beneficiary_default_index = default_index if current_user_option else 0

    with st.form("add_expense_form", clear_on_submit=True):
        # Name - now required
        name = st.text_input("Name", value="", help="What is this expense for?")

        col1, col2 = st.columns(2)
        with col1:
            # Date
            date = st.date_input(
                "Date", value=datetime.now(), help="When did this expense happen?"
            )

        with col2:
            # Category
            category_name = st.selectbox(
                "Category",
                options=list(category_options.keys()),
                index=0,
                help="What category does this expense belong to?",
            )
            category_id = category_options[category_name]

        col1, col2 = st.columns(2)
        with col1:
            # Amount
            amount = st.number_input(
                "Amount",
                min_value=1.0,
                format="%.2f",
                value=1.0,
                help="How much did this expense cost?",
            )

        with col2:
            # Payment source
            payment_source = st.selectbox(
                "Payment Source",
                options=list(payment_source_options.keys()),
                index=list(payment_source_options.keys()).index(
                    default_payment_source_name
                )
                if default_payment_source_name
                else 0,
                help="How was this expense paid?",
            )

        # Description
        description = st.text_area(
            "Description (Optional)",
            value="",
            help="Any additional information about this expense?",
        )

        col1, col2 = st.columns(2)
        with col1:
            selected_payer = st.selectbox(
                "Payer",
                options=payer_option_list,
                index=default_index,
                help="Who paid for this expense?",
            )
            payer_id = payer_options[selected_payer]

        with col2:
            # Beneficiary selection (always shown)
            selected_beneficiary = st.selectbox(
                "Beneficiary",
                options=beneficiary_option_list,
                index=beneficiary_default_index,
                help=(
                    "Who this expense is for (who benefits from it). "
                    "Does not matter if the expense is shared."
                ),
            )
            beneficiary_id = payer_options[selected_beneficiary]

        # Expense sharing
        is_shared = st.checkbox(
            "Split this expense with others",
            value=False,
            help="Is the expense to be shared with the household members?",
        )

        # Submit button
        submitted = st.form_submit_button("Add Expense")

        if submitted:
            # Validate required fields
            if not name:
                st.error("Please provide a name for the expense.")
                st.stop()

            # Convert date input to datetime
            expense_date = datetime.combine(date, datetime.min.time())

            # Create expense record
            result = db_manager.add_expense(
                reporter_id=profile_id,
                amount=amount,
                category_id=str(category_id),
                payment_source_id=payment_source_options[payment_source],
                date=expense_date,
                name=name,
                payer_id=payer_id,
                description=description,
                is_shared=is_shared,
                beneficiary_id=beneficiary_id if not is_shared else None,
            )

            st.success("Expense added successfully!")


def display_expense_list(db_manager: DatabaseManager, profile_id: int) -> None:
    """Display a list of expenses with filtering options.

    Args:
        db_manager (DatabaseManager): Database manager instance
        profile_id (int): ID of the current user's profile
    """
    st.header("Your Expenses")

    # Date filter controls
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "From", value=datetime.now() - timedelta(days=30), max_value=datetime.now()
        )
    with col2:
        end_date = st.date_input(
            "To", value=datetime.now(), min_value=start_date, max_value=datetime.now()
        )

    # Convert to datetime for filtering
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Get all expenses related to the user:
    # - Expenses where the user is the payer
    # - Shared expenses
    # - Expenses where user is the beneficiary
    # - (User as reporter is included by default)
    expenses = db_manager.get_expenses_for_list(
        user_id=profile_id,
        start_date=start_datetime,
        end_date=end_datetime,
    )

    if not expenses:
        st.info(
            "No expenses found for the selected date range. Add some expenses to get "
            "started!"
        )
        return

    # Get categories for display and editing
    categories_result = db_manager.get_categories()
    categories = categories_result.get("categories", [])
    category_map = {cat["id"]: cat["name"] for cat in categories}

    # Get payment sources for display
    payment_sources_result = db_manager.get_payment_sources(
        st.session_state.user.id
        if hasattr(st.session_state.user, "id")
        else st.session_state.user["id"]
    )
    payment_sources = payment_sources_result.get("payment_sources", [])
    payment_source_map = {ps["id"]: ps["name"] for ps in payment_sources}

    # Get all profiles for display in expense list
    profiles_result = db_manager.get_all_profiles()
    profiles = profiles_result.get("profiles", [])

    # Create a mapping of profile IDs to display names
    profile_names = {p["id"]: p["display_name"] for p in profiles}

    # Create a DataFrame with all formatting applied
    display_df = prepare_expense_data(expenses, profile_names, category_map)

    # Add payment source column
    display_df["payment_source"] = [
        payment_source_map.get(exp.get("payment_source_id"), "Not specified")
        for exp in expenses
    ]

    # Format date for display (keep this here as it's specific to the display
    # in this view)
    if "date" in display_df.columns:
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")

    # Use the formatted amount for display
    if "amount_formatted" in display_df.columns:
        display_df["amount"] = display_df["amount_formatted"]
        display_df = display_df.drop(columns=["amount_formatted"])

    # Select columns for display
    display_columns = [
        "date",
        "category",
        "name",
        "amount",
        "payment_source",
        "description",
        "shared",
        "payer",
        "beneficiary",
        "reporter",
    ]
    display_columns = [col for col in display_columns if col in display_df.columns]

    # Display the expenses
    st.dataframe(display_df[display_columns], use_container_width=True)

    # Delete functionality
    st.subheader("Delete Expense")

    # Select expense to delete
    expense_options = {}

    # Create descriptive labels for each expense
    for i, exp in enumerate(expenses):
        date_str = pd.to_datetime(exp["date"]).strftime("%Y-%m-%d")
        category_name = category_map.get(exp["category_id"], "Unknown")
        amount_str = format_currency(exp["amount"])
        payment_source_name = payment_source_map.get(
            exp.get("payment_source_id"), "Not specified"
        )

        # Create a descriptive label
        label = f"{date_str} - {category_name} - {amount_str}"

        # Add name if available
        if exp.get("name"):
            label = f"{label} - {exp['name']}"
        elif exp.get("description"):
            label += f" - {exp['description'][:20]}..."

        # Add payment source
        label += f" (Paid with: {payment_source_name})"

        if exp.get("is_shared") == 1:
            label += " (Shared)"
        elif exp.get("beneficiary_id") and exp.get("beneficiary_id") != profile_id:
            # If expense has a beneficiary and it's not the current user, show it
            beneficiary_name = profile_names.get(exp.get("beneficiary_id"), "Unknown")
            label += f" (For: {beneficiary_name})"
        elif exp.get("payer_id") != profile_id:
            # If someone else paid for it, highlight that
            payer_name = profile_names.get(exp.get("payer_id"), "Unknown")
            label += f" (Paid by: {payer_name})"

        expense_options[label] = exp["id"]

    selected_expense_label = st.selectbox(
        "Select Expense", options=list(expense_options.keys())
    )
    selected_expense_id = expense_options[selected_expense_label]

    # Find the selected expense data
    selected_expense = next(
        (exp for exp in expenses if exp["id"] == selected_expense_id), None
    )

    if selected_expense:
        if st.button(
            "Delete Expense", type="primary", help="This action cannot be undone"
        ):
            result = db_manager.delete_expense(
                expense_id=selected_expense_id, user_id=profile_id
            )
            if "error" in result:
                st.error(f"Error deleting expense: {result['error']}")
            else:
                st.success("Expense deleted successfully!")
                # Refresh
                st.rerun()

"""Expense management page.

This module provides a Streamlit page for managing expenses, including
adding, editing, and deleting expense records.
"""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from expense_manager.db.db_manager import DatabaseManager
from expense_manager.utils.analytics import (
    create_split_expenses_summary,
    prepare_expense_data,
)
from expense_manager.utils.models import format_currency


def display_expense_manager() -> None:
    """Display the expense management interface."""
    st.title("Manage Expenses")

    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to manage your expenses.")
        return

    # Initialize database manager
    db_manager = DatabaseManager()

    # Get user ID from session
    user_id = (
        st.session_state.user.id
        if hasattr(st.session_state.user, "id")
        else st.session_state.user["id"]
    )

    # Initialize session state if not exists
    if "expense_filter_start_date" not in st.session_state:
        st.session_state.expense_filter_start_date = (
            datetime.now() - timedelta(days=30)
        ).date()
    if "expense_filter_end_date" not in st.session_state:
        st.session_state.expense_filter_end_date = datetime.now().date()

    # Display expenses interface
    st.subheader("Expenses")
    tabs = st.tabs(["Add Expense", "View Expenses", "Split Expenses"])

    # Add Expense tab
    with tabs[0]:
        display_add_expense_form(db_manager, user_id)

    # View Expenses tab
    with tabs[1]:
        display_expense_list(db_manager, user_id)

    # Split Expenses tab
    with tabs[2]:
        display_split_expenses(db_manager, user_id)


def display_add_expense_form(db_manager: DatabaseManager, user_id: str) -> None:
    """Display form for adding a new expense.

    Args:
        db_manager (DatabaseManager): Database manager instance
        user_id (str): ID of the current user
    """
    st.header("Add New Expense")

    # Get categories for dropdown
    categories_result = db_manager.get_categories()
    categories = categories_result.get("categories", [])

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

    # Get category names for the dropdown
    category_options = {cat["name"]: cat["id"] for cat in categories}

    # Create the expense form
    with st.form("add_expense_form"):
        # Amount
        amount = st.number_input("Amount", min_value=1, format="%.2f", value=None)

        # Category
        category_name = st.selectbox("Category", options=list(category_options.keys()))
        category_id = category_options[category_name]

        # Date
        date = st.date_input("Date", value=datetime.now())

        # Name - now required
        name = st.text_input("Name", "")

        # Description
        description = st.text_area("Description (Optional)", "")

        # Get all profiles for payer selection
        profiles_result = db_manager.get_all_profiles()
        profiles = profiles_result.get("profiles", [])

        # Create a mapping of user IDs to their details including display names
        user_details = {}
        for u in profiles:
            user_id_value = u["user_id"]
            user_details[user_id_value] = {
                "user_id": user_id_value,
                "display_name": u["display_name"],
            }

        # Create options for the payer dropdown with display name
        payer_options = {}
        for user_detail in user_details.values():
            display_name = user_detail["display_name"]
            user_id_value = user_detail["user_id"]
            payer_options[display_name] = user_id_value

        # If no users found, provide a fallback option
        if not payer_options:
            st.warning("No users found in the system. Using current user as payer.")
            payer_id = user_id
        else:
            # Find the display option for current user
            current_user_option = next(
                (
                    option
                    for option, id_value in payer_options.items()
                    if id_value == user_id
                ),
                None,
            )

            # Default index for payer dropdown
            default_index = 0
            if current_user_option:
                default_index = list(payer_options.keys()).index(current_user_option)

            # Payer selection
            payer_option_list = (
                list(payer_options.keys()) if payer_options else ["No users available"]
            )
            selected_payer = st.selectbox(
                "Payer",
                options=payer_option_list,
                index=default_index,
                help="Select who paid for this expense",
            )

            # Get the payer ID safely
            if selected_payer and selected_payer in payer_options:
                payer_id = payer_options[selected_payer]
            else:
                # Use current user as fallback if there's an issue
                payer_id = user_id

        # Expense sharing
        is_shared = st.checkbox("Split this expense with others")

        # If sharing is enabled, show user selection
        split_with_users = []
        if is_shared:
            # Create user options for the multiselect (using the same user_details mapping)
            split_user_options = {}
            for user_id_key, user_detail in user_details.items():
                # Skip the current user as they'll be added automatically
                if user_id_key != user_id:
                    display_name = user_detail["display_name"]

                    # Use display name if available, otherwise use a default label
                    display_text = (
                        display_name if display_name else f"User {user_id_key}"
                    )

                    split_user_options[display_text] = user_id_key

            # Only show the user selection if there are other users
            if split_user_options:
                selected_users = st.multiselect(
                    "Split with",
                    options=list(split_user_options.keys()),
                    help="Select users to split this expense with",
                )
                # Get the user IDs for selected users
                split_with_users = [
                    split_user_options[selected] for selected in selected_users
                ]
            else:
                st.info("No other users to split expenses with.")

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
            result = db_manager.create_expense(
                user_id=user_id,
                amount=amount,
                category_id=category_id,
                date=expense_date,
                name=name,
                payer_id=payer_id,
                description=description,
                is_shared=is_shared,
                split_with_users=split_with_users,
            )

            if "error" in result:
                st.error(f"Error creating expense: {result['error']}")
            elif "warning" in result:
                st.warning(f"Expense created but with warning: {result['warning']}")
                st.success("Expense added!")
                st.rerun()
            else:
                st.success("Expense added successfully!")
                # Clear the form (by forcing a rerun)
                st.rerun()


def display_expense_list(db_manager: DatabaseManager, user_id: str) -> None:
    """Display a list of expenses with filtering options.

    Args:
        db_manager (DatabaseManager): Database manager instance
        user_id (str): ID of the current user
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

    # Get all expenses for the user with date filtering
    expenses_result = db_manager.get_expenses(
        user_id=user_id, start_date=start_datetime, end_date=end_datetime
    )
    expenses = expenses_result.get("expenses", [])

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

    # Create a DataFrame for display
    expenses_df = prepare_expense_data(expenses)

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

    # Get all profiles for display in expense list
    profiles_result = db_manager.get_all_profiles()
    profiles = profiles_result.get("profiles", [])

    users_map = {u["user_id"]: u["display_name"] for u in profiles}

    # Format for display
    display_df = expenses_df.copy()

    # Add category names
    if "category_id" in display_df.columns:
        display_df["category"] = display_df["category_id"].map(category_map)

    # Format date
    if "date" in display_df.columns:
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")

    # Format amount
    if "amount" in display_df.columns:
        display_df["amount"] = display_df["amount"].map(format_currency)

    # Add shared indicator
    if "is_shared" in display_df.columns:
        display_df["shared"] = display_df["is_shared"].map({True: "Yes", False: "No"})

    # Add payer information
    if "payer_id" in display_df.columns:
        display_df["payer"] = display_df["payer_id"].map(users_map)
        # Ensure the mapping worked correctly
        display_df["payer"] = display_df["payer"].fillna("Unknown")

    # Select columns for display
    display_columns = [
        "date",
        "category",
        "name",
        "amount",
        "description",
        "shared",
        "payer",
    ]
    display_columns = [col for col in display_columns if col in display_df.columns]

    # Display the expenses
    st.dataframe(display_df[display_columns], use_container_width=True)

    # Show shared expenses analysis if there are any shared expenses
    if "is_shared" in expenses_df.columns and expenses_df["is_shared"].any():
        with st.expander("Shared Expenses Analysis"):
            # Calculate splitting summaries
            split_summary = create_split_expenses_summary(
                expenses_df, user_id, users_map
            )

            if split_summary["total_shared"] > 0:
                st.subheader("Shared Expenses Summary")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "Total Shared Expenses",
                        format_currency(split_summary["total_shared"]),
                    )
                with col2:
                    st.metric("You Paid", format_currency(split_summary["total_paid"]))
                with col3:
                    st.metric("You Owe", format_currency(split_summary["total_owed"]))

                if split_summary["by_user"]:
                    st.subheader("Balance by User")
                    for user_balance in split_summary["by_user"]:
                        with st.container():
                            cols = st.columns([3, 2, 2, 2])
                            with cols[0]:
                                st.write(f"**{user_balance['display_name']}**")
                            with cols[1]:
                                st.write(
                                    f"Paid for you: {format_currency(user_balance['paid_for_you'])}"
                                )
                            with cols[2]:
                                st.write(
                                    "You paid: "
                                    f"{format_currency(user_balance['you_paid_for_them'])}"
                                )
                            with cols[3]:
                                net = user_balance["net_balance"]
                                if net > 0:
                                    st.write(f"🔴 You owe: {format_currency(abs(net))}")
                                elif net < 0:
                                    st.write(
                                        f"🟢 Owes you: {format_currency(abs(net))}"
                                    )
                                else:
                                    st.write("✅ Settled")
            else:
                st.info("No shared expenses found.")

    # Edit/Delete functionality
    st.subheader("Edit or Delete Expense")

    # Select expense to edit/delete
    expense_options = {}
    for i, exp in enumerate(expenses):
        date_str = pd.to_datetime(exp["date"]).strftime("%Y-%m-%d")
        category_name = category_map.get(exp["category_id"], "Unknown")
        amount_str = format_currency(exp["amount"])

        # Create a descriptive label
        label = f"{date_str} - {category_name} - {amount_str}"

        # Add name if available
        if exp.get("name"):
            label = f"{label} - {exp['name']}"
        elif exp.get("description"):
            label += f" - {exp['description'][:20]}..."

        if exp.get("is_shared", False):
            label += " (Shared)"

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
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Edit Expense"):
                # Store the selected expense ID in session state
                st.session_state.editing_expense_id = selected_expense_id
                st.session_state.editing_expense = selected_expense

        with col2:
            if st.button(
                "Delete Expense", type="primary", help="This action cannot be undone"
            ):
                result = db_manager.delete_expense(selected_expense_id, user_id)
                if "error" in result:
                    st.error(f"Error deleting expense: {result['error']}")
                else:
                    st.success("Expense deleted successfully!")
                    # Clear the selected expense and refresh
                    st.rerun()

    # Check if an expense is selected for editing
    if (
        hasattr(st.session_state, "editing_expense_id")
        and st.session_state.editing_expense_id
    ):
        editing_expense = st.session_state.editing_expense

        st.subheader("Edit Expense")

        with st.form("edit_expense_form"):
            # Amount
            amount = st.number_input(
                "Amount",
                min_value=0.01,
                value=float(editing_expense["amount"]),
                format="%.2f",
            )

            # Category
            current_category_name = category_map.get(
                editing_expense["category_id"], list(category_map.values())[0]
            )
            category_name = st.selectbox(
                "Category",
                options=list(category_map.values()),
                index=list(category_map.values()).index(current_category_name),
            )
            category_id = next(
                cat_id for cat_id, name in category_map.items() if name == category_name
            )

            # Date
            current_date = pd.to_datetime(editing_expense["date"]).date()
            date = st.date_input("Date", value=current_date)

            # Name - required
            name = st.text_input("Name", editing_expense.get("name", ""))

            # Get all profiles
            profiles_result = db_manager.get_all_profiles()
            profiles = profiles_result.get("profiles", [])

            # Ensure user_details is initialized with the right structure
            user_details = {}
            for u in profiles:
                profile_id_value = u["id"]
                user_details[profile_id_value] = {
                    "id": profile_id_value,
                    "display_name": u["display_name"],
                }

            # Get current payer ID
            current_payer_id = editing_expense.get("payer_id", user_id)

            # Create options for the payer dropdown with display name + email
            payer_options = {}
            for user_detail in user_details.values():
                display_name = user_detail["display_name"]
                profile_id_value = user_detail["id"]
                payer_options[display_name] = profile_id_value

            # Find the display option for current payer
            current_payer_option = next(
                (
                    option
                    for option, id_value in payer_options.items()
                    if id_value == current_payer_id
                ),
                None,
            )

            # Default index for payer dropdown
            default_index = 0
            if current_payer_option:
                default_index = list(payer_options.keys()).index(current_payer_option)

            # Ensure we have at least one option
            payer_option_list = (
                list(payer_options.keys()) if payer_options else ["No users available"]
            )

            # Payer selection dropdown
            selected_payer = st.selectbox(
                "Payer",
                options=payer_option_list,
                index=default_index if default_index < len(payer_option_list) else 0,
                help="Select who paid for this expense",
            )

            # Get the payer ID safely
            if selected_payer and selected_payer in payer_options:
                payer_id = payer_options[selected_payer]
            else:
                # Use current payer ID as fallback if there's an issue
                payer_id = current_payer_id

            # Description
            description = st.text_area(
                "Description (Optional)", editing_expense.get("description", "")
            )

            # Expense sharing
            is_shared = st.checkbox(
                "Split this expense with others",
                value=editing_expense.get("is_shared", False),
            )

            # If sharing is enabled, show user selection
            split_with_users = []
            if is_shared:
                # Get all profiles
                profiles_result = db_manager.get_all_profiles()
                profiles = profiles_result.get("profiles", [])

                # Ensure user_details is initialized with the right structure
                user_details = {}
                for u in profiles:
                    profile_id_value = u["id"]
                    user_details[profile_id_value] = {
                        "id": profile_id_value,
                        "display_name": u["display_name"],
                    }

                # Get current split users if any
                if editing_expense.get("is_shared", False):
                    split_result = db_manager.get_expense_splits(editing_expense["id"])
                    current_split_users = split_result.get("user_ids", [])
                else:
                    current_split_users = []

                # Create user options for the multiselect (using the same user_details mapping)
                split_user_options = {}
                for user_id_key, user_detail in user_details.items():
                    # Skip the current user as they'll be added automatically
                    if user_id_key != user_id:
                        display_name = user_detail["display_name"]

                        # Use display name if available, otherwise use a default label
                        display_text = (
                            display_name if display_name else f"User {user_id_key}"
                        )

                        split_user_options[display_text] = user_id_key

                # Only show the user selection if there are other users
                if split_user_options:
                    selected_users = st.multiselect(
                        "Split with",
                        options=list(split_user_options.keys()),
                        help="Select users to split this expense with",
                    )
                    # Get the user IDs for selected users
                    split_with_users = [
                        split_user_options[selected] for selected in selected_users
                    ]
                else:
                    st.info("No other users to split expenses with.")

            # Submit button
            submitted = st.form_submit_button("Update Expense")

            if submitted:
                # Convert date input to datetime
                expense_date = datetime.combine(date, datetime.min.time())

                # Create update data
                updates = {
                    "amount": amount,
                    "category_id": category_id,
                    "date": expense_date,
                    "name": name,
                    "payer_id": payer_id,
                    "description": description,
                    "is_shared": is_shared,
                }

                # Validate required fields before submitting
                if not name:
                    st.error("Please provide a name for the expense.")
                    st.stop()

                # Update expense record
                result = db_manager.update_expense(
                    expense_id=st.session_state.editing_expense_id,
                    user_id=user_id,
                    updates=updates,
                )

                if "error" in result:
                    st.error(f"Error updating expense: {result['error']}")
                else:
                    st.success("Expense updated successfully!")

                    # Update splits if needed
                    if is_shared:
                        # Update the splits
                        split_result = db_manager.update_expense_splits(
                            st.session_state.editing_expense_id,
                            user_id,
                            split_with_users,
                        )

                        if "error" in split_result:
                            st.warning(
                                f"Expense updated but splits could not be updated: "
                                f"{split_result['error']}"
                            )

                    # Clear editing state and refresh
                    del st.session_state.editing_expense_id
                    del st.session_state.editing_expense
                    st.rerun()


def display_split_expenses(db_manager: DatabaseManager, user_id: str) -> None:
    """Display interface for viewing and managing split expenses.

    Args:
        db_manager (DatabaseManager): Database manager instance
        user_id (str): ID of the current user
    """
    st.header("Split Expenses")

    # Get all shared expenses for the user
    expenses_result = db_manager.get_expenses(user_id=user_id, include_shared=True)
    expenses = expenses_result.get("expenses", [])

    # Filter to only shared expenses
    shared_expenses = [exp for exp in expenses if exp.get("is_shared", False)]

    if not shared_expenses:
        st.info("No shared expenses found. Create a shared expense to get started!")
        return

    # Get all profiles for display in expense list
    profiles_result = db_manager.get_all_profiles()
    profiles = profiles_result.get("profiles", [])

    users_map = {u["id"]: u["display_name"] for u in profiles}

    # Get categories for display
    categories_result = db_manager.get_categories()
    categories = categories_result.get("categories", [])
    category_map = {cat["id"]: cat["name"] for cat in categories}

    # Create a DataFrame for analysis
    expenses_df = prepare_expense_data(shared_expenses)

    # Get split information for each expense
    split_counts = {}
    for exp in shared_expenses:
        split_result = db_manager.get_expense_splits(exp["id"])
        split_users = split_result.get("user_ids", [])
        split_counts[exp["id"]] = len(split_users) if split_users else 1

    # Add split count to the DataFrame
    if "id" in expenses_df.columns:
        expenses_df["split_count"] = expenses_df["id"].map(split_counts)

    # Calculate splitting summaries
    split_summary = create_split_expenses_summary(expenses_df, user_id, users_map)

    # Display summary metrics
    st.subheader("Split Expenses Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Total Shared Expenses", format_currency(split_summary["total_shared"])
        )
    with col2:
        st.metric("You Paid", format_currency(split_summary["total_paid"]))
    with col3:
        st.metric("You Owe", format_currency(split_summary["total_owed"]))

    # Display balance by user
    if split_summary["by_user"]:
        st.subheader("Balance by User")
        for user_balance in split_summary["by_user"]:
            with st.container(border=True):
                cols = st.columns([3, 2, 2, 2])
                with cols[0]:
                    st.write(f"**{user_balance['display_name']}**")
                with cols[1]:
                    st.write(
                        f"Paid for you: {format_currency(user_balance['paid_for_you'])}"
                    )
                with cols[2]:
                    st.write(
                        f"You paid: {format_currency(user_balance['you_paid_for_them'])}"
                    )
                with cols[3]:
                    net = user_balance["net_balance"]
                    if net > 0:
                        st.write(f"🔴 You owe: {format_currency(abs(net))}")
                    elif net < 0:
                        st.write(f"🟢 Owes you: {format_currency(abs(net))}")
                    else:
                        st.write("✅ Settled")

    # Display list of shared expenses
    st.subheader("Shared Expenses List")

    # Format for display
    display_df = expenses_df.copy()

    # Add category names
    if "category_id" in display_df.columns:
        display_df["category"] = display_df["category_id"].map(category_map)

    # Format date
    if "date" in display_df.columns:
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")

    # Format amount
    if "amount" in display_df.columns:
        display_df["amount"] = display_df["amount"].map(format_currency)
        display_df["per_person"] = (
            display_df["amount"]
            .str.replace(" kr", "")
            .str.replace(",", ".")
            .str.replace(" ", "")
            .astype(float)
            / display_df["split_count"]
        ).map(format_currency)

    # Add payer information
    if "payer_id" in display_df.columns:
        display_df["payer"] = display_df["payer_id"].map(users_map)

    # Select columns for display
    display_columns = [
        "date",
        "category",
        "amount",
        "per_person",
        "description",
        "split_count",
        "payer",
    ]
    display_columns = [col for col in display_columns if col in display_df.columns]

    # Display the expenses
    st.dataframe(display_df[display_columns], use_container_width=True)

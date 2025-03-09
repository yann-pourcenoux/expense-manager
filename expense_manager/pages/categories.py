"""Category management page.

This module provides a Streamlit page for managing expense categories, including
adding, editing, and deleting categories.
"""

from typing import Any, Dict

import streamlit as st

from expense_manager.db.db_manager import DatabaseManager


def display_category_manager() -> None:
    """Display the category management interface."""
    st.title("Manage Categories")

    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to manage categories.")
        return

    # Initialize database manager
    db_manager = DatabaseManager()

    # Get user ID from session - not used but keeping for future use
    # (would be needed for per-user categories)
    # user_id = (
    #     st.session_state.user.id
    #     if hasattr(st.session_state.user, "id")
    #     else st.session_state.user["id"]
    # )

    # Initialize session state variables if not exist
    if "editing_category_id" not in st.session_state:
        st.session_state.editing_category_id = None
    if "editing_category" not in st.session_state:
        st.session_state.editing_category = None
    if "deleting_category_id" not in st.session_state:
        st.session_state.deleting_category_id = None
    if "deleting_category_name" not in st.session_state:
        st.session_state.deleting_category_name = None
    if "category_added" not in st.session_state:
        st.session_state.category_added = False

    # Show success message if category was added
    if st.session_state.category_added:
        st.success("Category created successfully!")
        st.session_state.category_added = False

    # Display add category form
    display_add_category_form(db_manager)

    # Add a separator between sections
    st.markdown("---")

    # Display category list below
    display_category_list(db_manager)


def set_edit_category(category_id: str, category: Dict[str, Any]) -> None:
    """Set the category to edit in session state.

    Args:
        category_id (str): ID of the category to edit
        category (Dict[str, Any]): Category data
    """
    st.session_state.editing_category_id = category_id
    st.session_state.editing_category = category


def set_delete_category(category_id: str, category_name: str) -> None:
    """Set the category to delete in session state.

    Args:
        category_id (str): ID of the category to delete
        category_name (str): Name of the category
    """
    st.session_state.deleting_category_id = category_id
    st.session_state.deleting_category_name = category_name


def clear_edit_state() -> None:
    """Clear the edit state in session state."""
    st.session_state.editing_category_id = None
    st.session_state.editing_category = None


def clear_delete_state() -> None:
    """Clear the delete state in session state."""
    st.session_state.deleting_category_id = None
    st.session_state.deleting_category_name = None


def display_add_category_form(db_manager: DatabaseManager) -> None:
    """Display form for adding a new category.

    Args:
        db_manager (DatabaseManager): Database manager instance
    """
    st.header("Add New Category")

    with st.form("add_category_form"):
        # Category name
        category_name = st.text_input(
            "Category Name",
            help=(
                "Enter a descriptive name for the category (e.g., 'Groceries', "
                "'Rent', 'Entertainment')"
            ),
        )

        # Submit button
        submitted = st.form_submit_button("Add Category")

        if submitted:
            if not category_name:
                st.error("Category name is required.")
                return

            # Create category - color will be assigned automatically
            result = db_manager.create_category(category_name)

            if "error" in result:
                st.error(f"Error creating category: {result['error']}")
            else:
                # Set flag for success message on next rerun
                st.session_state.category_added = True
                # Clear the form
                st.session_state.add_category_name = ""


def display_category_list(db_manager: DatabaseManager) -> None:
    """Display a list of categories with edit/delete options.

    Args:
        db_manager (DatabaseManager): Database manager instance
    """
    st.header("Your Categories")

    # Get all categories
    categories_result = db_manager.get_categories()
    categories = categories_result.get("categories", [])

    if not categories:
        st.info("No categories found. Add some categories to get started!")
        return

    # Calculate columns based on number of categories (3 columns by default)
    num_columns = 3
    columns = st.columns(num_columns)

    # Display each category in card-like format
    for i, category in enumerate(categories):
        col_idx = i % num_columns
        with columns[col_idx]:
            with st.container(border=True):
                # Display in a simple format without color emphasis
                st.write(f"**{category['name']}**")

                # Edit button with callback
                if st.button("Edit", key=f"edit_{category['id']}"):
                    set_edit_category(category["id"], category)

                # Delete button with callback
                if st.button("Delete", key=f"delete_{category['id']}"):
                    set_delete_category(category["id"], category["name"])

    # Handle category editing
    if st.session_state.editing_category_id:
        display_edit_category_form(db_manager, st.session_state.editing_category)

    # Handle category deletion with confirmation
    if st.session_state.deleting_category_id:
        st.warning(
            f"Are you sure you want to delete the category "
            f"'{st.session_state.deleting_category_name}'? This cannot be undone."
        )
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Yes, Delete"):
                result = db_manager.delete_category(
                    st.session_state.deleting_category_id
                )

                if "error" in result:
                    st.error(f"Error deleting category: {result['error']}")
                else:
                    st.toast("Category deleted successfully!")
                    clear_delete_state()

        with col2:
            if st.button("Cancel"):
                clear_delete_state()


def display_edit_category_form(
    db_manager: DatabaseManager, category: Dict[str, Any]
) -> None:
    """Display form for editing an existing category.

    Args:
        db_manager (DatabaseManager): Database manager instance
        category (Dict[str, Any]): Category data to edit
    """
    st.subheader(f"Edit Category: {category['name']}")

    with st.form("edit_category_form"):
        # Category name
        category_name = st.text_input(
            "Category Name",
            value=category["name"],
            help="Enter a descriptive name for the category",
        )

        # Submit button
        submitted = st.form_submit_button("Update Category")

        if submitted:
            if not category_name:
                st.error("Category name is required.")
                return

            # Update category
            result = db_manager.update_category(
                category_id=category["id"], name=category_name
            )

            if "error" in result:
                st.error(f"Error updating category: {result['error']}")
            else:
                st.success("Category updated successfully!")
                clear_edit_state()

    # Cancel button outside the form
    if st.button("Cancel Editing"):
        clear_edit_state()

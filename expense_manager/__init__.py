"""Expense Manager package initialization.

This module initializes the Expense Manager package and imports key modules
to make imports easier from other modules.
"""

from expense_manager.auth.auth_manager import AuthManager
from expense_manager.db.db_manager import DatabaseManager
from expense_manager.utils.models import (
    Category,
    CategoryCreate,
    Expense,
    ExpenseCreate,
    ExpenseSummary,
    ExpenseUpdate,
    User,
)

# Create __all__ for explicit exports
__all__ = [
    "AuthManager",
    "DatabaseManager",
    "ExpenseCreate",
    "Expense",
    "ExpenseUpdate",
    "Category",
    "CategoryCreate",
    "User",
    "ExpenseSummary",
]

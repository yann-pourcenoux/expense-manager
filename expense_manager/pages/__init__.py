"""Pages package initialization."""

from expense_manager.pages.categories import display_category_manager
from expense_manager.pages.expenses import display_expense_manager
from expense_manager.pages.income import display_income_manager
from expense_manager.pages.profile import display_profile_manager, display_profile_setup

__all__ = [
    "display_expense_manager",
    "display_category_manager",
    "display_income_manager",
    "display_profile_manager",
    "display_profile_setup",
]

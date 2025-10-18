"""
API routes module.

This module contains all API route definitions for the application.
"""

from .monte_carlo import router as monte_carlo_router

__all__ = ["monte_carlo_router"]

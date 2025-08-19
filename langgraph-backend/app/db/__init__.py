"""
Database module for EspressoBot
Provides connection pooling and database utilities
"""

from .connection_pool import get_database_pool, get_database_connection

__all__ = ['get_database_pool', 'get_database_connection']
"""
Storage infrastructure module.

This module provides storage adapters for different backends including S3
for artifact storage and management.
"""

from .s3_adapter import S3StorageAdapter

__all__ = ["S3StorageAdapter"]
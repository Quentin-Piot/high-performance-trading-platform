"""Security utilities for the trading platform API.

This module provides IAM policy management, credential management, and security utilities."""

from .iam_policies import (
    IAMPolicy,
    IAMPolicyBuilder,
    generate_terraform_policies,
    validate_policy_permissions
)
from .credential_manager import (
    CredentialManager,
    AWSCredentials,
    CredentialSource
)

__all__ = [
    "IAMPolicy",
    "IAMPolicyBuilder", 
    "generate_terraform_policies",
    "validate_policy_permissions",
    "CredentialManager",
    "AWSCredentials",
    "CredentialSource"
]
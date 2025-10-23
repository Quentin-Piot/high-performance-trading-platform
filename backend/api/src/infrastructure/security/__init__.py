"""Security utilities for the trading platform API.
This module provides IAM policy management, credential management, and security utilities."""
from .credential_manager import AWSCredentials, CredentialManager, CredentialSource
from .iam_policies import (
    IAMPolicy,
    IAMPolicyBuilder,
    generate_terraform_policies,
    validate_policy_permissions,
)

__all__ = [
    "IAMPolicy",
    "IAMPolicyBuilder",
    "generate_terraform_policies",
    "validate_policy_permissions",
    "CredentialManager",
    "AWSCredentials",
    "CredentialSource",
]

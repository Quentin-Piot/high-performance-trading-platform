"""
Credential management utilities for secure handling of sensitive configuration.

This module provides utilities for managing AWS credentials, database connections,
and other sensitive configuration data with security best practices.
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CredentialSource(Enum):
    """Sources for credential resolution"""

    ENVIRONMENT = "environment"
    IAM_ROLE = "iam_role"
    AWS_PROFILE = "aws_profile"
    INSTANCE_METADATA = "instance_metadata"
    CONTAINER_METADATA = "container_metadata"


@dataclass
class AWSCredentials:
    """AWS credential configuration"""

    access_key_id: str | None = None
    secret_access_key: str | None = None
    session_token: str | None = None
    region: str = "us-east-1"
    profile: str | None = None
    role_arn: str | None = None
    source: CredentialSource = CredentialSource.ENVIRONMENT

    def is_valid(self) -> bool:
        """Check if credentials are valid for authentication"""
        if self.source == CredentialSource.IAM_ROLE:
            return self.role_arn is not None
        elif self.source == CredentialSource.AWS_PROFILE:
            return self.profile is not None
        elif self.source == CredentialSource.ENVIRONMENT:
            return self.access_key_id is not None and self.secret_access_key is not None
        else:
            # Instance/container metadata doesn't require explicit credentials
            return True

    def to_boto3_config(self) -> dict[str, Any]:
        """Convert to boto3 session configuration"""
        config = {"region_name": self.region}

        if self.source == CredentialSource.ENVIRONMENT and self.is_valid():
            config.update(
                {
                    "aws_access_key_id": self.access_key_id,
                    "aws_secret_access_key": self.secret_access_key,
                }
            )
            if self.session_token:
                config["aws_session_token"] = self.session_token
        elif self.source == CredentialSource.AWS_PROFILE and self.profile:
            config["profile_name"] = self.profile

        return config

    def mask_sensitive_data(self) -> dict[str, Any]:
        """Return credential info with sensitive data masked"""
        return {
            "source": self.source.value,
            "region": self.region,
            "profile": self.profile,
            "role_arn": self.role_arn,
            "has_access_key": bool(self.access_key_id),
            "has_secret_key": bool(self.secret_access_key),
            "has_session_token": bool(self.session_token),
        }


class CredentialManager:
    """Secure credential management with fallback strategies"""

    @staticmethod
    def resolve_aws_credentials(
        environment: str = "development", prefer_iam_role: bool = True
    ) -> AWSCredentials:
        """
        Resolve AWS credentials using secure fallback strategy.

        Priority order:
        1. IAM Role (if prefer_iam_role=True and in AWS environment)
        2. AWS Profile (if AWS_PROFILE is set)
        3. Environment variables
        4. Instance/Container metadata (if in AWS environment)

        Args:
            environment: Current environment (development, staging, production)
            prefer_iam_role: Whether to prefer IAM roles over explicit credentials

        Returns:
            AWSCredentials configuration
        """
        region = os.getenv("AWS_REGION", "us-east-1")

        # Check for IAM role configuration (preferred for production)
        role_arn = os.getenv("AWS_ROLE_ARN")
        if prefer_iam_role and role_arn:
            logger.info(
                "Using IAM role for AWS authentication",
                extra={
                    "credential_source": "iam_role",
                    "role_arn": role_arn[:50] + "..."
                    if len(role_arn) > 50
                    else role_arn,
                },
            )
            return AWSCredentials(
                region=region, role_arn=role_arn, source=CredentialSource.IAM_ROLE
            )

        # Check for AWS profile
        profile = os.getenv("AWS_PROFILE")
        if profile:
            logger.info(
                "Using AWS profile for authentication",
                extra={"credential_source": "aws_profile", "profile": profile},
            )
            return AWSCredentials(
                region=region, profile=profile, source=CredentialSource.AWS_PROFILE
            )

        # Check for explicit environment variables
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        session_token = os.getenv("AWS_SESSION_TOKEN")

        if access_key and secret_key:
            logger.info(
                "Using environment variables for AWS authentication",
                extra={
                    "credential_source": "environment",
                    "has_session_token": bool(session_token),
                },
            )
            return AWSCredentials(
                access_key_id=access_key,
                secret_access_key=secret_key,
                session_token=session_token,
                region=region,
                source=CredentialSource.ENVIRONMENT,
            )

        # Fallback to instance/container metadata (for EC2/ECS/Lambda)
        if environment in ("staging", "production"):
            logger.info(
                "Using instance/container metadata for AWS authentication",
                extra={"credential_source": "metadata"},
            )
            return AWSCredentials(
                region=region, source=CredentialSource.INSTANCE_METADATA
            )

        # No credentials found
        logger.warning(
            "No AWS credentials found",
            extra={
                "environment": environment,
                "checked_sources": [
                    "iam_role",
                    "aws_profile",
                    "environment",
                    "metadata",
                ],
            },
        )
        return AWSCredentials(region=region)

    @staticmethod
    def validate_credentials(credentials: AWSCredentials) -> bool:
        """
        Validate AWS credentials without exposing sensitive data.

        Args:
            credentials: AWS credentials to validate

        Returns:
            True if credentials appear valid
        """
        if not credentials:
            logger.error("No AWS credentials provided")
            return False

        # Debug logging for troubleshooting
        logger.debug(
            "Validating credentials",
            extra={
                "credential_info": credentials.mask_sensitive_data(),
                "is_valid": credentials.is_valid(),
            },
        )

        if not credentials.is_valid():
            logger.error(
                "Invalid AWS credentials configuration",
                extra={"credential_info": credentials.mask_sensitive_data()},
            )
            return False

        # For testing environment, allow mock credentials
        if (
            credentials.source == CredentialSource.ENVIRONMENT
            and credentials.access_key_id == "testing"
            and credentials.secret_access_key == "testing"
        ):
            logger.info(
                "Using mock AWS credentials for testing",
                extra={"credential_info": credentials.mask_sensitive_data()},
            )
            return True

        logger.info(
            "AWS credentials validated",
            extra={"credential_info": credentials.mask_sensitive_data()},
        )
        return True

    @staticmethod
    def get_database_url(mask_in_logs: bool = True) -> str | None:
        """
        Get database URL with optional masking for logs.

        Args:
            mask_in_logs: Whether to mask the URL in logs

        Returns:
            Database URL or None if not configured
        """
        db_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")

        if db_url and mask_in_logs:
            # Log presence without exposing credentials
            logger.info(
                "Database URL configured",
                extra={"has_database_url": True, "url_length": len(db_url)},
            )
        elif not db_url:
            logger.warning("No database URL configured")

        return db_url

    @staticmethod
    def mask_url(url: str) -> str:
        """
        Mask sensitive parts of a URL for logging.

        Args:
            url: URL to mask

        Returns:
            Masked URL safe for logging
        """
        if not url:
            return url

        # Basic URL masking - hide credentials but keep structure
        if "://" in url:
            scheme, rest = url.split("://", 1)
            if "@" in rest:
                credentials, host_part = rest.split("@", 1)
                return f"{scheme}://[REDACTED]@{host_part}"

        return url

    @staticmethod
    def get_secure_config() -> dict[str, Any]:
        """
        Get application configuration with sensitive data masked.

        Returns:
            Configuration dictionary safe for logging
        """
        config = {
            "environment": os.getenv("ENVIRONMENT", "development"),
            "aws_region": os.getenv("AWS_REGION", "us-east-1"),
            "has_database_url": bool(os.getenv("DATABASE_URL") or os.getenv("DB_URL")),
            "has_aws_credentials": bool(os.getenv("AWS_ACCESS_KEY_ID")),
            "has_aws_profile": bool(os.getenv("AWS_PROFILE")),
            "has_aws_role": bool(os.getenv("AWS_ROLE_ARN")),
            "sqs_endpoint": CredentialManager.mask_url(
                os.getenv("SQS_ENDPOINT_URL", "")
            ),
            "monitoring_enabled": os.getenv("MONITORING_ENABLED", "true").lower()
            == "true",
        }

        return config

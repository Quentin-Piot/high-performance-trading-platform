"""
Service for integrating Google OAuth with AWS Cognito Identity Provider.
"""
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from core.cognito import CognitoUser
from core.config import get_settings

logger = logging.getLogger(__name__)
class CognitoGoogleIntegrationService:
    """Service for managing Google OAuth integration with Cognito."""
    def __init__(
        self,
        cognito_idp_client: Any | None = None,
        cognito_identity_client: Any | None = None,
    ):
        self.settings = get_settings()
        self.region = self.settings.cognito_region
        self.user_pool_id = self.settings.cognito_user_pool_id
        self.identity_pool_id = self.settings.cognito_identity_pool_id
        self.is_development = (
            self.settings.env == "development"
            and hasattr(self.settings, "aws_endpoint_url")
            and self.settings.aws_endpoint_url == "http://localhost:4566"
        )
        if self.is_development:
            logger.info(
                "Running in development mode with LocalStack - using mock Cognito Google integration"
            )
            self.cognito_idp = cognito_idp_client
            self.cognito_identity = cognito_identity_client
        elif self.user_pool_id and self.identity_pool_id:
            self.cognito_idp = cognito_idp_client or boto3.client(
                "cognito-idp", region_name=self.region
            )
            self.cognito_identity = cognito_identity_client or boto3.client(
                "cognito-identity", region_name=self.region
            )
        else:
            logger.warning("Cognito configuration incomplete for Google integration")
            self.cognito_idp = None
            self.cognito_identity = None
    async def create_federated_user(
        self, google_user_info: dict[str, Any]
    ) -> CognitoUser | None:
        """
        Create or link a federated user in Cognito using Google identity.
        Args:
            google_user_info: User information from Google OAuth
        Returns:
            CognitoUser object if successful, None otherwise
        """
        if self.is_development:
            logger.info(
                f"Mock federated user creation for LocalStack development: {google_user_info.get('email', 'unknown')}"
            )
            return CognitoUser(
                sub=f"mock_google_{google_user_info.get('sub', 'test_sub')}",
                email=google_user_info.get("email", "test@example.com"),
                name=google_user_info.get("name", "Test User"),
                email_verified=True,
                cognito_username=google_user_info.get("email", "test@example.com"),
            )
        if not self.cognito_idp:
            logger.error("Cognito IDP client not initialized")
            return None
        try:
            email = google_user_info["email"]
            try:
                response = self.cognito_idp.list_users(
                    UserPoolId=self.user_pool_id, Filter=f'email = "{email}"'
                )
                if response["Users"]:
                    user = response["Users"][0]
                    user_attributes = {
                        attr["Name"]: attr["Value"] for attr in user["Attributes"]
                    }
                    if "identities" not in user_attributes:
                        await self._link_google_identity(
                            user["Username"], google_user_info
                        )
                    return CognitoUser(
                        sub=user_attributes.get(
                            "sub", f"google_{google_user_info['sub']}"
                        ),
                        email=email,
                        name=user_attributes.get(
                            "name", google_user_info.get("name", "")
                        ),
                        email_verified=user_attributes.get(
                            "email_verified", "false"
                        ).lower()
                        == "true",
                        cognito_username=user["Username"],
                    )
            except ClientError as e:
                logger.warning(f"Error searching for existing user: {e}")
            return await self._create_federated_user(google_user_info)
        except Exception as e:
            logger.error(f"Error creating federated user: {e}")
            return None
    async def _create_federated_user(
        self, user_info: dict[str, Any]
    ) -> CognitoUser | None:
        """
        Create or get federated user in Cognito using Google identity.
        Args:
            user_info: User information from Google OAuth
        Returns:
            CognitoUser instance or None if failed
        """
        logger.info(
            f"Creating federated user for email: {user_info.get('email', 'unknown')}"
        )
        logger.debug(f"User info received: {user_info}")
        if self.is_development:
            logger.info("Development mode: creating mock federated user")
            return CognitoUser(
                sub=f"google_{user_info['sub']}",
                email=user_info["email"],
                name=user_info.get("name", ""),
                email_verified=user_info.get("email_verified", False),
            )
        if not self.cognito_idp:
            logger.error("Cognito IDP client not initialized")
            return None
        try:
            self.cognito_idp.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=user_info["email"],
                UserAttributes=[
                    {"Name": "email", "Value": user_info["email"]},
                    {"Name": "email_verified", "Value": str(user_info.get("email_verified", False)).lower()},
                    {"Name": "name", "Value": user_info.get("name", "")},
                ],
                DesiredDeliveryMediums=["EMAIL"],
            )
            self.cognito_idp.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=user_info["email"],
                UserAttributes=[
                    {"Name": "custom:google_sub", "Value": user_info["sub"]},
                    {"Name": "custom:provider", "Value": "google"},
                ],
            )
            logger.info(
                f"Successfully created/retrieved federated user: {user_info['email']}"
            )
            return CognitoUser(
                sub=f"google_{user_info['sub']}",
                email=user_info["email"],
                name=user_info.get("name", ""),
                email_verified=user_info.get("email_verified", False),
                cognito_username=user_info["email"],
            )
        except ClientError as e:
            logger.error(f"Error creating federated user: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error creating federated user: {e}", exc_info=True
            )
            return None
    async def _link_google_identity(
        self, username: str, google_user_info: dict[str, Any]
    ) -> bool:
        """Link Google identity to existing Cognito user."""
        try:
            self.cognito_idp.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=username,
                UserAttributes=[
                    {"Name": "custom:google_sub", "Value": google_user_info["sub"]},
                    {"Name": "custom:provider", "Value": "google"},
                ],
            )
            logger.info(
                f"Linked Google identity for user: {username} with Google sub: {google_user_info['sub']}"
            )
            return True
        except ClientError as e:
            logger.error(f"Error linking Google identity: {e}")
            return False
    async def get_federated_credentials(self, id_token: str) -> dict[str, str] | None:
        """
        Get temporary AWS credentials for federated user.
        Args:
            id_token: Google ID token
        Returns:
            Dict with AWS credentials or None if failed
        """
        if self.is_development:
            logger.info("Mock federated credentials for LocalStack development")
            return {
                "identity_id": f"mock_identity_{id_token[:10]}",
                "access_key_id": "mock_access_key",
                "secret_key": "mock_secret_key",
                "session_token": "mock_session_token",
            }
        if not self.cognito_identity:
            logger.error("Cognito Identity client not initialized")
            return None
        try:
            identity_response = self.cognito_identity.get_id(
                IdentityPoolId=self.identity_pool_id,
                Logins={"accounts.google.com": id_token},
            )
            identity_id = identity_response["IdentityId"]
            credentials_response = self.cognito_identity.get_credentials_for_identity(
                IdentityId=identity_id, Logins={"accounts.google.com": id_token}
            )
            credentials = credentials_response["Credentials"]
            return {
                "identity_id": identity_id,
                "access_key_id": credentials["AccessKeyId"],
                "secret_key": credentials["SecretKey"],
                "session_token": credentials["SessionToken"],
            }
        except ClientError as e:
            logger.error(f"Error getting federated credentials: {e}")
            return None
_cognito_google_service: CognitoGoogleIntegrationService | None = None
def get_cognito_google_service() -> CognitoGoogleIntegrationService:
    """Get Cognito Google integration service instance."""
    global _cognito_google_service
    if _cognito_google_service is None:
        _cognito_google_service = CognitoGoogleIntegrationService()
    return _cognito_google_service

"""
AWS Cognito integration for authentication and JWT token validation.
"""
import json
import logging
from typing import Any
from urllib.request import urlopen

import boto3
from botocore.exceptions import ClientError
from jose import JWTError, jwt
from pydantic import BaseModel

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
class CognitoUser(BaseModel):
    """Cognito user information extracted from JWT token."""
    sub: str
    email: str
    name: str | None = None
    email_verified: bool = False
    cognito_username: str
class CognitoService:
    """Service for AWS Cognito operations."""
    def __init__(self):
        self.region = settings.cognito_region
        self.user_pool_id = settings.cognito_user_pool_id
        self.client_id = settings.cognito_client_id
        if self.user_pool_id and self.client_id:
            client_config = {"region_name": self.region}
            if settings.aws_endpoint_url:
                client_config["endpoint_url"] = settings.aws_endpoint_url
                logger.info(f"Using AWS endpoint URL: {settings.aws_endpoint_url}")
            self.cognito_client = boto3.client("cognito-idp", **client_config)
            self.cognito_identity_client = boto3.client(
                "cognito-identity", **client_config
            )
            logger.info(f"Cognito client configured for region {self.region}")
        else:
            self.cognito_client = None
            self.cognito_identity_client = None
            logger.warning(
                "Cognito configuration incomplete, some features may not work"
            )
        self._jwks = None
    def get_jwks(self) -> dict[str, Any]:
        """Get JSON Web Key Set from Cognito."""
        if not self.user_pool_id:
            logger.warning("Cannot fetch JWKS: User Pool ID not configured")
            return {"keys": []}
        if self._jwks is None:
            if settings.env == "development":
                logger.info("Using mock JWKS for LocalStack development")
                self._jwks = {"keys": []}
                return self._jwks
            jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
            try:
                with urlopen(jwks_url) as response:
                    self._jwks = json.loads(response.read())
            except Exception as e:
                logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")
                raise
        return self._jwks
    def get_public_key(self, token_header: dict[str, str]) -> str | None:
        """Get the public key for JWT verification."""
        jwks = self.get_jwks()
        kid = token_header.get("kid")
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        return None
    def verify_token(self, token: str) -> CognitoUser | None:
        """Verify and decode JWT token from Cognito."""
        try:
            if settings.env == "development":
                payload = jwt.get_unverified_claims(token)
                return CognitoUser(
                    sub=payload.get("sub", "test-user-id"),
                    email=payload.get("email", "test@example.com"),
                    name=payload.get("name", "Test User"),
                    email_verified=payload.get("email_verified", True),
                    cognito_username=payload.get(
                        "cognito:username", payload.get("sub", "test-user")
                    ),
                )
            header = jwt.get_unverified_header(token)
            public_key = self.get_public_key(header)
            if not public_key:
                logger.warning("Public key not found for token")
                return None
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}",
            )
            return CognitoUser(
                sub=payload["sub"],
                email=payload.get("email", ""),
                name=payload.get("name"),
                email_verified=payload.get("email_verified", False),
                cognito_username=payload.get("cognito:username", payload["sub"]),
            )
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    def get_user_info(self, access_token: str) -> dict[str, Any] | None:
        """Get user information from Cognito using access token."""
        if settings.env == "development":
            logger.info("Returning mock user info for LocalStack development")
            return {
                "username": "test-user",
                "user_status": "CONFIRMED",
                "attributes": {
                    "email": "test@example.com",
                    "email_verified": "true",
                    "name": "Test User",
                },
            }
        if not self.cognito_client:
            logger.warning("Cognito client not configured")
            return None
        try:
            response = self.cognito_client.get_user(AccessToken=access_token)
            user_attributes = {}
            for attr in response.get("UserAttributes", []):
                user_attributes[attr["Name"]] = attr["Value"]
            return {
                "username": response.get("Username"),
                "user_status": response.get("UserStatus"),
                "attributes": user_attributes,
            }
        except ClientError as e:
            logger.warning(f"Failed to get user info: {e}")
            return None
    def create_user(self, email: str, temporary_password: str) -> str | None:
        """Create a new user in Cognito (admin operation)."""
        if not self.cognito_client:
            logger.warning("Cognito client not configured")
            return None
        try:
            import uuid
            username = str(uuid.uuid4())
            response = self.cognito_client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=username,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                ],
                TemporaryPassword=temporary_password,
                MessageAction="SUPPRESS",
            )
            return response["User"]["Username"]
        except ClientError as e:
            logger.error(f"Failed to create user: {e}")
            return None
    def delete_user(self, username: str) -> bool:
        """Delete a user from Cognito (admin operation)."""
        if not self.cognito_client:
            logger.warning("Cognito client not configured")
            return False
        try:
            self.cognito_client.admin_delete_user(
                UserPoolId=self.user_pool_id, Username=username
            )
            return True
        except ClientError as e:
            logger.error(f"Failed to delete user: {e}")
            return False
    def set_user_password(self, username: str, password: str) -> bool:
        """Set a permanent password for a user in Cognito (admin operation)."""
        if not self.cognito_client:
            logger.warning("Cognito client not configured")
            return False
        try:
            self.cognito_client.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=username,
                Password=password,
                Permanent=True,
            )
            return True
        except ClientError as e:
            logger.error(f"Failed to set user password: {e}")
            return False
    def create_federated_user(self, user_info: dict[str, Any]) -> str | None:
        """Create or get federated user in Cognito for Google OAuth."""
        if settings.env == "development":
            logger.info(
                f"Mock federated user creation for LocalStack development: {user_info.get('email', 'unknown')}"
            )
            return user_info.get("email", "test@example.com")
        if not self.cognito_client:
            logger.warning("Cognito client not configured")
            return None
        try:
            try:
                response = self.cognito_client.list_users(
                    UserPoolId=self.user_pool_id,
                    Filter=f'email = "{user_info["email"]}"',
                )
                if response["Users"]:
                    logger.info(f"Found existing federated user: {user_info['email']}")
                    return response["Users"][0]["Username"]
            except ClientError as e:
                logger.warning(f"Error searching for existing user: {e}")
            import uuid
            username = str(uuid.uuid4())
            response = self.cognito_client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=username,
                UserAttributes=[
                    {"Name": "email", "Value": user_info["email"]},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "name", "Value": user_info.get("name", "")},
                    {"Name": "given_name", "Value": user_info.get("given_name", "")},
                    {"Name": "family_name", "Value": user_info.get("family_name", "")},
                ],
                MessageAction="SUPPRESS",
            )
            logger.info(f"Created new federated user: {user_info['email']}")
            return response["User"]["Username"]
        except ClientError as e:
            logger.error(f"Failed to create federated user: {e}")
            return None
    def get_federated_credentials(self, id_token: str) -> dict[str, Any] | None:
        """Get federated credentials for identity pool."""
        if settings.env == "development":
            logger.info(
                "Returning mock federated credentials for LocalStack development"
            )
            return {
                "identity_id": "test-identity-id",
                "credentials": {
                    "AccessKeyId": "test-access-key",
                    "SecretKey": "test-secret-key",
                    "SessionToken": "test-session-token",
                    "Expiration": "2025-12-31T23:59:59Z",
                },
            }
        if not self.cognito_identity_client:
            logger.warning("Cognito Identity client not configured")
            return None
        try:
            identity_response = self.cognito_identity_client.get_id(
                IdentityPoolId=settings.cognito_identity_pool_id,
                Logins={
                    f"cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}": id_token
                },
            )
            identity_id = identity_response["IdentityId"]
            credentials_response = self.cognito_identity_client.get_credentials_for_identity(
                IdentityId=identity_id,
                Logins={
                    f"cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}": id_token
                },
            )
            return {
                "identity_id": identity_id,
                "credentials": credentials_response["Credentials"],
            }
        except ClientError as e:
            logger.error(f"Failed to get federated credentials: {e}")
            return None
cognito_service = CognitoService()
def get_cognito_service() -> CognitoService:
    """Dependency to get Cognito service."""
    return cognito_service

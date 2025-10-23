"""
Repository for user management with Cognito integration.
"""
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.cognito import CognitoUser
from infrastructure.models import User

logger = logging.getLogger(__name__)
class UserRepository:
    """Repository for user operations."""
    def __init__(self, session: AsyncSession):
        self.session = session
    async def get_by_cognito_sub(self, cognito_sub: str) -> User | None:
        """Get user by Cognito sub (user ID)."""
        result = await self.session.execute(
            select(User).where(User.cognito_sub == cognito_sub)
        )
        return result.scalar_one_or_none()
    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    async def get_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    async def create_from_cognito(self, cognito_user: CognitoUser) -> User:
        """Create a new user from Cognito user data."""
        try:
            logger.debug(f"Creating user from Cognito data: {cognito_user.email}")
            user = User(
                email=cognito_user.email,
                hashed_password=None,
                cognito_sub=cognito_user.sub,
                name=cognito_user.name,
                auth_method="google",
            )
            logger.debug(f"User object before adding to session: {user.__dict__}")
            self.session.add(user)
            logger.debug("User added to session, attempting commit")
            await self.session.commit()
            logger.debug("Commit successful")
            await self.session.refresh(user)
            logger.debug(f"User created successfully with ID: {user.id}")
            return user
        except IntegrityError as e:
            logger.error(f"IntegrityError during user creation: {e}")
            await self.session.rollback()
            existing_user = await self.get_by_cognito_sub(cognito_user.sub)
            if existing_user:
                logger.debug(
                    f"Found existing user by cognito_sub after IntegrityError: {existing_user.id}"
                )
                return existing_user
            existing_user = await self.get_by_email(cognito_user.email)
            if existing_user:
                logger.debug(
                    f"Found existing user by email after IntegrityError: {existing_user.id}"
                )
                return existing_user
            logger.error("No existing user found after IntegrityError")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during user creation: {type(e).__name__}: {e}"
            )
            await self.session.rollback()
            raise
    async def update_user_info(self, user: User, cognito_user: CognitoUser) -> User:
        """Update user information from Cognito."""
        user.email = cognito_user.email
        user.name = cognito_user.name
        await self.session.commit()
        await self.session.refresh(user)
        return user
    async def get_or_create_from_cognito(self, cognito_user: CognitoUser) -> User:
        """Get existing user or create new one from Cognito user."""
        try:
            logger.debug(
                f"Starting get_or_create_from_cognito for user: {cognito_user.email}"
            )
            logger.debug(f"Searching by cognito_sub: {cognito_user.sub}")
            user = await self.get_by_cognito_sub(cognito_user.sub)
            if user:
                logger.debug(f"Found existing user by cognito_sub: {user.id}")
                return await self.update_user_info(user, cognito_user)
            logger.debug(f"Searching by email: {cognito_user.email}")
            user = await self.get_by_email(cognito_user.email)
            if user:
                if not user.cognito_sub:
                    logger.debug(
                        f"Found existing user by email without cognito_sub, linking to Cognito: {user.id}"
                    )
                    user.cognito_sub = cognito_user.sub
                    user.name = cognito_user.name
                    user.auth_method = (
                        "mixed"
                    )
                    await self.session.commit()
                    await self.session.refresh(user)
                    return user
                else:
                    logger.warning(
                        f"User with email {cognito_user.email} already exists with different cognito_sub. Current: {user.cognito_sub}, New: {cognito_user.sub}"
                    )
                    return user
            logger.debug("Creating new user from Cognito")
            return await self.create_from_cognito(cognito_user)
        except Exception as e:
            logger.error(
                f"Error in get_or_create_from_cognito for user {cognito_user.email}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise

"""
Repository for user management with Cognito integration.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.cognito import CognitoUser
from infrastructure.models import User


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
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_from_cognito(self, cognito_user: CognitoUser) -> User:
        """Create a new user from Cognito user information."""
        user = User(
            cognito_sub=cognito_user.sub,
            email=cognito_user.email,
            name=cognito_user.name
        )

        self.session.add(user)
        try:
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except IntegrityError:
            await self.session.rollback()
            # User might already exist, try to get it
            existing_user = await self.get_by_cognito_sub(cognito_user.sub)
            if existing_user:
                return existing_user
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
        # First try to find by Cognito sub
        user = await self.get_by_cognito_sub(cognito_user.sub)

        if user:
            # Update user info in case it changed in Cognito
            return await self.update_user_info(user, cognito_user)

        # Try to find by email (in case user was created before Cognito integration)
        user = await self.get_by_email(cognito_user.email)
        if user and not user.cognito_sub:
            # Link existing user to Cognito
            user.cognito_sub = cognito_user.sub
            user.name = cognito_user.name
            await self.session.commit()
            await self.session.refresh(user)
            return user

        # Create new user
        return await self.create_from_cognito(cognito_user)

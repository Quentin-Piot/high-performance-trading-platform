import logging
import secrets
import string
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.cognito import CognitoService, get_cognito_service
from core.security import create_access_token, verify_password
from domain.schemas.auth import Token, UserCreate
from infrastructure.db import get_session
from infrastructure.repositories.user_repository import UserRepository
from infrastructure.repositories.users import get_user_by_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session
def generate_temporary_password(length: int = 12) -> str:
    """Generate a secure temporary password for Cognito user creation."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))
@router.post("/register", response_model=Token)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    cognito_service: CognitoService = Depends(get_cognito_service),
):
    """Register a new user using Cognito authentication."""
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà enregistré")
    try:
        temp_password = generate_temporary_password()
        cognito_username = cognito_service.create_user(payload.email, temp_password)
        if not cognito_username:
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de la création du compte utilisateur",
            )
        success = cognito_service.set_user_password(payload.email, payload.password)
        if not success:
            cognito_service.delete_user(cognito_username)
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de la configuration du mot de passe",
            )
        from core.cognito import CognitoUser
        cognito_user = CognitoUser(
            sub=cognito_username,
            email=payload.email,
            name=payload.email.split("@")[0],
            email_verified=True,
            cognito_username=cognito_username,
        )
        user_repo = UserRepository(db)
        db_user = await user_repo.get_or_create_from_cognito(cognito_user)
        token = create_access_token(subject=str(db_user.id))
        logger.info(f"Successfully registered user: {payload.email}")
        return Token(access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed for {payload.email}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Erreur interne lors de l'inscription"
        ) from e
@router.post("/login", response_model=Token)
async def login(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    token = create_access_token(subject=str(user.id))
    return Token(access_token=token)

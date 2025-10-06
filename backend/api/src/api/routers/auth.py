from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token, get_password_hash, verify_password
from domain.schemas.auth import UserCreate, Token
from infrastructure.db import get_session
from infrastructure.repositories.users import create_user, get_user_by_email


router = APIRouter(prefix="/auth", tags=["auth"])


async def get_db():
    async for session in get_session():
        yield session


@router.post("/register", response_model=Token)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà enregistré")
    hashed = get_password_hash(payload.password)
    user = await create_user(db, payload.email, hashed)
    token = create_access_token(subject=str(user.id))
    return Token(access_token=token)


@router.post("/login", response_model=Token)
async def login(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    token = create_access_token(subject=str(user.id))
    return Token(access_token=token)
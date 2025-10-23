from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(
        ..., max_length=72, description="Password must be 72 characters or less"
    )


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

from pydantic import BaseModel, EmailStr, Field, field_validator

from services.password_validation_service import PasswordValidationService


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Password must be between 8 and 72 characters and meet security requirements"
    )
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Valide la force du mot de passe selon les règles de sécurité."""
        validation_result = PasswordValidationService.validate_password(v)
        if not validation_result.is_valid:
            error_messages = "; ".join(validation_result.failed_rules)
            raise ValueError(f"Mot de passe invalide: {error_messages}")
        return v
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

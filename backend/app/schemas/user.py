"""User schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """Schema for user profile response."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: EmailStr
    display_name: str
    display_name_ar: str | None
    avatar_url: str | None
    locale: str
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    display_name_ar: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)
    locale: str | None = Field(default=None, pattern="^(en|ar)$")

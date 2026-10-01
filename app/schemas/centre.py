import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.schemas.test import TestResponse


class CentreCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the diagnostic centre")
    location: str = Field(..., min_length=1, max_length=255, description="Location/Address of the centre")
    contact_email: EmailStr | None = Field(default=None, description="Contact email address")
    contact_phone: str | None = Field(default=None, max_length=50, description="Contact phone number")


class CentreResponse(BaseModel):
    id: uuid.UUID
    name: str
    location: str
    contact_email: str | None
    contact_phone: str | None
    is_active: bool
    created_at: datetime
    tests: list[TestResponse] = []

    model_config = ConfigDict(from_attributes=True)

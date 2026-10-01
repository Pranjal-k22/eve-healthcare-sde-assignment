import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class TestCreateRequest(BaseModel):
    __test__ = False

    name: str = Field(..., min_length=1, max_length=255, description="Name of the diagnostic test")
    description: str | None = Field(default=None, description="Detailed test description")
    price: Decimal = Field(..., gt=0, description="Price of the test in currency units (must be > 0)")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Test name cannot be empty or whitespace only")
        return v_stripped


class TestResponse(BaseModel):
    __test__ = False

    id: uuid.UUID
    centre_id: uuid.UUID
    name: str
    description: str | None
    price: Decimal
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

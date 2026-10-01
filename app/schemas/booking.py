import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.models.booking import BookingStatus
from app.schemas.centre import CentreResponse
from app.schemas.test import TestResponse


class BookingCreateRequest(BaseModel):
    __test__ = False

    centre_id: uuid.UUID
    test_id: uuid.UUID
    appointment_date: datetime = Field(..., description="Future date and time for the appointment")

    @field_validator("appointment_date")
    @classmethod
    def validate_appointment_date(cls, v: datetime) -> datetime:
        # If timezone-naive, treat as UTC
        if v.tzinfo is None:
            v_utc = v.replace(tzinfo=timezone.utc)
        else:
            v_utc = v

        if v_utc <= datetime.now(timezone.utc):
            raise ValueError("Appointment date must be scheduled in the future")
        return v_utc


class BookingResponse(BaseModel):
    __test__ = False

    id: uuid.UUID
    user_id: uuid.UUID
    centre_id: uuid.UUID
    test_id: uuid.UUID
    appointment_date: datetime
    amount: Decimal
    status: BookingStatus
    created_at: datetime
    updated_at: datetime
    centre: CentreResponse | None = None
    test: TestResponse | None = None

    model_config = ConfigDict(from_attributes=True)

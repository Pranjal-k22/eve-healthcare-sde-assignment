import uuid
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from app.models.payment import PaymentStatus
from app.models.booking import BookingStatus


class PaymentWebhookPayload(BaseModel):
    __test__ = False

    event_id: str = Field(..., min_length=1, max_length=255, description="Unique identifier for the webhook event")
    provider_payment_id: str = Field(..., min_length=1, max_length=255, description="Payment gateway transaction ID")
    booking_id: uuid.UUID = Field(..., description="ID of the target booking")
    status: PaymentStatus = Field(..., description="Payment outcome status: SUCCESS or FAILED")
    payment_method: str = Field(default="SIMULATED_WEBHOOK", description="Payment method used")
    amount: Decimal | None = Field(default=None, description="Optional payload amount (ignored for server calculation)")


class WebhookProcessResponse(BaseModel):
    __test__ = False

    status: str = Field(..., description="Processing status: 'processed' or 'already_processed'")
    event_id: str
    message: str
    booking_id: uuid.UUID
    booking_status: BookingStatus

    model_config = ConfigDict(from_attributes=True)

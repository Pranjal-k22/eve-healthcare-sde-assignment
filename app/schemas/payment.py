import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from app.models.payment import PaymentStatus
from app.models.booking import BookingStatus


class SimulatedPaymentRequest(BaseModel):
    __test__ = False

    booking_id: uuid.UUID = Field(..., description="ID of the pending booking to pay")
    payment_method: str = Field(default="CREDIT_CARD", description="Simulated payment method")
    simulate_outcome: PaymentStatus = Field(
        default=PaymentStatus.SUCCESS,
        description="Simulated outcome: SUCCESS or FAILED",
    )


class PaymentResponse(BaseModel):
    __test__ = False

    id: uuid.UUID
    booking_id: uuid.UUID
    transaction_id: str
    payment_method: str
    amount: Decimal
    status: PaymentStatus
    created_at: datetime
    booking_status: BookingStatus

    model_config = ConfigDict(from_attributes=True)

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.payment import SimulatedPaymentRequest, PaymentResponse
from app.schemas.webhook import PaymentWebhookPayload, WebhookProcessResponse
from app.services.payment_service import process_simulated_payment
from app.services.webhook_service import process_payment_webhook
from app.services.auth_service import get_current_user
from app.models.user import User

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
def create_simulated_payment(
    payment_in: SimulatedPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return process_simulated_payment(db=db, current_user_id=current_user.id, payment_in=payment_in)


@router.post("/webhook/", response_model=WebhookProcessResponse, status_code=status.HTTP_200_OK)
def handle_payment_webhook(
    webhook_in: PaymentWebhookPayload,
    db: Session = Depends(get_db),
):
    """Idempotent payment webhook endpoint receiving status updates from payment providers."""
    return process_payment_webhook(db=db, webhook_in=webhook_in)

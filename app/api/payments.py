import json
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import BadRequestException
from app.schemas.payment import SimulatedPaymentRequest, PaymentResponse
from app.schemas.webhook import PaymentWebhookPayload, WebhookProcessResponse
from app.services.payment_service import process_simulated_payment
from app.services.webhook_service import process_payment_webhook, verify_webhook_signature
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
async def handle_payment_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_signature: str | None = Header(None, alias="X-Signature"),
):
    """Idempotent payment webhook endpoint receiving status updates from payment providers."""
    raw_body = await request.body()
    verify_webhook_signature(payload_bytes=raw_body, signature=x_signature)

    try:
        json_data = json.loads(raw_body.decode("utf-8"))
        webhook_in = PaymentWebhookPayload(**json_data)
    except Exception as exc:
        raise BadRequestException(detail=f"Invalid webhook payload format: {str(exc)}")

    return process_payment_webhook(db=db, webhook_in=webhook_in)

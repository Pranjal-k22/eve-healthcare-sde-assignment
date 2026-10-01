import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import hmac
import hashlib
from app.models.webhook_event import WebhookEvent
from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus
from app.schemas.webhook import PaymentWebhookPayload, WebhookProcessResponse
from app.core.exceptions import NotFoundException, BadRequestException, UnauthorizedException
from app.core.config import settings


def verify_webhook_signature(payload_str: str, signature: str | None) -> None:
    if not signature or not signature.strip():
        return
    expected = hmac.new(settings.WEBHOOK_SECRET.encode(), payload_str.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature.strip()):
        raise UnauthorizedException(detail="Invalid webhook HMAC signature")


def process_payment_webhook(db: Session, webhook_in: PaymentWebhookPayload) -> WebhookProcessResponse:
    event_id_clean = webhook_in.event_id.strip()

    # 1. IDEMPOTENCY LEDGER CHECK: Check if event_id already exists in DB
    existing_event = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id_clean).first()
    if existing_event:
        booking = db.query(Booking).filter(Booking.id == webhook_in.booking_id).first()
        b_status = booking.status if booking else BookingStatus.PENDING
        return WebhookProcessResponse(
            status="already_processed",
            event_id=event_id_clean,
            message="Webhook event has already been processed",
            booking_id=webhook_in.booking_id,
            booking_status=b_status,
        )

    # 2. Lookup target Booking with row lock to prevent race condition mutations
    booking = db.query(Booking).filter(Booking.id == webhook_in.booking_id).with_for_update().first()
    if not booking:
        raise NotFoundException(detail=f"Booking with ID '{webhook_in.booking_id}' not found")

    # 3. Create WebhookEvent record (Enforces UNIQUE constraint at DB layer for concurrent race safety)
    webhook_event = WebhookEvent(
        event_id=event_id_clean,
        provider_payment_id=webhook_in.provider_payment_id,
        booking_id=booking.id,
        payload=webhook_in.model_dump(mode="json"),
    )

    try:
        db.add(webhook_event)
        db.flush()
    except IntegrityError:
        db.rollback()
        # Handle concurrent race condition where duplicate event_id was inserted simultaneously
        booking_refreshed = db.query(Booking).filter(Booking.id == webhook_in.booking_id).first()
        b_status = booking_refreshed.status if booking_refreshed else BookingStatus.PENDING
        return WebhookProcessResponse(
            status="already_processed",
            event_id=event_id_clean,
            message="Webhook event has already been processed",
            booking_id=webhook_in.booking_id,
            booking_status=b_status,
        )

    # 4. Synchronize Booking status & Payment record ONLY if booking is currently PENDING
    if booking.status == BookingStatus.PENDING:
        # Check if payment with provider_payment_id already exists
        existing_payment = (
            db.query(Payment).filter(Payment.transaction_id == webhook_in.provider_payment_id).first()
        )

        if not existing_payment:
            if webhook_in.status == PaymentStatus.SUCCESS:
                payment_status = PaymentStatus.SUCCESS
                booking.status = BookingStatus.CONFIRMED
            else:
                payment_status = PaymentStatus.FAILED
                booking.status = BookingStatus.FAILED

            payment = Payment(
                booking_id=booking.id,
                transaction_id=webhook_in.provider_payment_id,
                payment_method=webhook_in.payment_method,
                amount=booking.amount,
                status=payment_status,
                raw_response={"webhook_event_id": event_id_clean, "status": payment_status.value},
            )
            db.add(payment)

    # 5. Commit atomic transaction
    db.commit()

    return WebhookProcessResponse(
        status="processed",
        event_id=event_id_clean,
        message="Webhook event processed successfully",
        booking_id=booking.id,
        booking_status=booking.status,
    )

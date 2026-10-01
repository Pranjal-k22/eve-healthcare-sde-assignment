import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.payment import Payment, PaymentStatus
from app.models.booking import Booking, BookingStatus
from app.schemas.payment import SimulatedPaymentRequest
from app.core.exceptions import NotFoundException, BadRequestException, ForbiddenException


def process_simulated_payment(
    db: Session,
    current_user_id: uuid.UUID,
    payment_in: SimulatedPaymentRequest,
) -> Payment:
    # 1. Fetch booking by ID with row lock to prevent concurrent payment races
    booking = db.query(Booking).filter(Booking.id == payment_in.booking_id).with_for_update().first()
    if not booking:
        raise NotFoundException(detail=f"Booking with ID '{payment_in.booking_id}' not found")

    # 2. Verify user ownership
    if booking.user_id != current_user_id:
        raise ForbiddenException(detail="Access denied to another user's booking")

    # 3. Verify booking is in PENDING state
    if booking.status != BookingStatus.PENDING:
        raise BadRequestException(
            detail=f"Booking is not in PENDING state. Current status: '{booking.status.value}'"
        )

    # 4. Generate unique transaction ID for mock payment
    tx_id = f"tx_mock_{uuid.uuid4().hex[:16]}"

    # 5. SERVER-SIDE AMOUNT DERIVATION: Amount taken directly from booking.amount
    payment_amount = booking.amount

    # 6. Synchronize booking status based on simulated payment outcome
    if payment_in.simulate_outcome == PaymentStatus.SUCCESS:
        payment_status = PaymentStatus.SUCCESS
        booking.status = BookingStatus.CONFIRMED
    else:
        payment_status = PaymentStatus.FAILED
        booking.status = BookingStatus.FAILED

    # 7. Create Payment record
    payment = Payment(
        booking_id=booking.id,
        transaction_id=tx_id,
        payment_method=payment_in.payment_method,
        amount=payment_amount,
        status=payment_status,
        raw_response={
            "simulated": True,
            "outcome": payment_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)
    db.refresh(booking)

    # Attach booking_status to payment object for DTO response schema compatibility
    payment.booking_status = booking.status
    return payment

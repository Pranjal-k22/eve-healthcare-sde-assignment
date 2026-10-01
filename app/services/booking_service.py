import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload

from app.models.booking import Booking, BookingStatus
from app.models.diagnostic_centre import DiagnosticCentre
from app.models.diagnostic_test import DiagnosticTest
from app.schemas.booking import BookingCreateRequest
from app.core.exceptions import NotFoundException, BadRequestException, ForbiddenException


def create_booking(db: Session, user_id: uuid.UUID, booking_in: BookingCreateRequest) -> Booking:
    # 1. Verify Diagnostic Centre exists
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == booking_in.centre_id).first()
    if not centre:
        raise NotFoundException(detail=f"Diagnostic centre with ID '{booking_in.centre_id}' not found")
    if not centre.is_active:
        raise BadRequestException(detail="Selected diagnostic centre is currently inactive")

    # 2. Verify Diagnostic Test exists
    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == booking_in.test_id).first()
    if not test:
        raise NotFoundException(detail=f"Diagnostic test with ID '{booking_in.test_id}' not found")
    if not test.is_active:
        raise BadRequestException(detail="Selected diagnostic test is currently inactive")

    # 3. CRITICAL BUSINESS INVARIANT: Test MUST belong to the selected Centre
    if test.centre_id != booking_in.centre_id:
        raise BadRequestException(detail="Diagnostic test does not belong to the selected diagnostic centre")

    # 4. Validate appointment date is in the future
    appointment_utc = booking_in.appointment_date
    if appointment_utc.tzinfo is None:
        appointment_utc = appointment_utc.replace(tzinfo=timezone.utc)

    if appointment_utc <= datetime.now(timezone.utc):
        raise BadRequestException(detail="Appointment date must be scheduled in the future")

    # 5. SERVER-SIDE AMOUNT DERIVATION: Amount derived strictly from test.price
    booking_amount = test.price

    # 6. Create Booking record with initial status PENDING
    booking = Booking(
        user_id=user_id,
        centre_id=booking_in.centre_id,
        test_id=booking_in.test_id,
        appointment_date=appointment_utc,
        amount=booking_amount,
        status=BookingStatus.PENDING,
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_user_bookings(
    db: Session, user_id: uuid.UUID, page: int = 1, page_size: int = 10
) -> list[Booking]:
    offset = (page - 1) * page_size
    return (
        db.query(Booking)
        .options(joinedload(Booking.centre), joinedload(Booking.test))
        .filter(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )


def get_booking_by_id(db: Session, booking_id: uuid.UUID, current_user_id: uuid.UUID) -> Booking:
    booking = (
        db.query(Booking)
        .options(joinedload(Booking.centre), joinedload(Booking.test))
        .filter(Booking.id == booking_id)
        .first()
    )

    if not booking:
        raise NotFoundException(detail=f"Booking with ID '{booking_id}' not found")

    # Verify user ownership
    if booking.user_id != current_user_id:
        raise ForbiddenException(detail="Access denied to another user's booking")

    return booking


def cancel_booking(db: Session, booking_id: uuid.UUID, current_user_id: uuid.UUID) -> Booking:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise NotFoundException(detail=f"Booking with ID '{booking_id}' not found")

    # Verify user ownership
    if booking.user_id != current_user_id:
        raise ForbiddenException(detail="Unauthorized to cancel another user's booking")

    # Only PENDING bookings can be manually cancelled by user
    if booking.status != BookingStatus.PENDING:
        raise BadRequestException(detail=f"Cannot cancel booking with current status '{booking.status.value}'")

    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return booking

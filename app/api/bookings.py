import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.booking import BookingCreateRequest, BookingResponse
from app.services.booking_service import (
    create_booking,
    get_user_bookings,
    get_booking_by_id,
    cancel_booking,
)
from app.services.auth_service import get_current_user
from app.models.user import User

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def add_booking(
    booking_in: BookingCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_booking(db=db, user_id=current_user.id, booking_in=booking_in)


@router.get("", response_model=list[BookingResponse], status_code=status.HTTP_200_OK)
def list_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_user_bookings(db=db, user_id=current_user.id)


@router.get("/{booking_id}", response_model=BookingResponse, status_code=status.HTTP_200_OK)
def get_booking_details(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_booking_by_id(db=db, booking_id=booking_id, current_user_id=current_user.id)


@router.post("/{booking_id}/cancel", response_model=BookingResponse, status_code=status.HTTP_200_OK)
def cancel_my_booking(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return cancel_booking(db=db, booking_id=booking_id, current_user_id=current_user.id)

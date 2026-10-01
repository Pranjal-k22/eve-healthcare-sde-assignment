from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.payment import SimulatedPaymentRequest, PaymentResponse
from app.services.payment_service import process_simulated_payment
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

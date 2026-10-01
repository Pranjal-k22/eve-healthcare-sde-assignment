import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.centre import CentreCreateRequest, CentreResponse
from app.schemas.test import TestCreateRequest, TestResponse
from app.services.centre_service import create_centre, get_centres, get_centre_by_id
from app.services.test_service import create_test_for_centre, get_tests_by_centre
from app.services.auth_service import get_current_user
from app.models.user import User

router = APIRouter(prefix="/centres", tags=["Diagnostic Centres"])


@router.post("", response_model=CentreResponse, status_code=status.HTTP_201_CREATED)
def add_centre(
    centre_in: CentreCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_centre(db=db, centre_in=centre_in)


@router.get("", response_model=list[CentreResponse], status_code=status.HTTP_200_OK)
def list_centres(db: Session = Depends(get_db)):
    return get_centres(db=db)


@router.get("/{centre_id}", response_model=CentreResponse, status_code=status.HTTP_200_OK)
def get_centre_details(centre_id: uuid.UUID, db: Session = Depends(get_db)):
    return get_centre_by_id(db=db, centre_id=centre_id)


@router.post("/{centre_id}/tests", response_model=TestResponse, status_code=status.HTTP_201_CREATED)
def add_test_to_centre(
    centre_id: uuid.UUID,
    test_in: TestCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_test_for_centre(db=db, centre_id=centre_id, test_in=test_in)


@router.get("/{centre_id}/tests", response_model=list[TestResponse], status_code=status.HTTP_200_OK)
def list_tests_for_centre(centre_id: uuid.UUID, db: Session = Depends(get_db)):
    return get_tests_by_centre(db=db, centre_id=centre_id)

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.test import TestResponse
from app.services.test_service import get_test_by_id

router = APIRouter(prefix="/tests", tags=["Diagnostic Tests"])


@router.get("/{test_id}", response_model=TestResponse, status_code=status.HTTP_200_OK)
def get_test_details(test_id: uuid.UUID, db: Session = Depends(get_db)):
    return get_test_by_id(db=db, test_id=test_id)

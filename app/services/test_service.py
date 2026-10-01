import uuid
from sqlalchemy.orm import Session
from app.models.diagnostic_test import DiagnosticTest
from app.schemas.test import TestCreateRequest
from app.services.centre_service import get_centre_by_id
from app.core.exceptions import NotFoundException, BadRequestException


def create_test_for_centre(db: Session, centre_id: uuid.UUID, test_in: TestCreateRequest) -> DiagnosticTest:
    # Verify centre exists
    get_centre_by_id(db, centre_id)

    if test_in.price <= 0:
        raise BadRequestException(detail="Test price must be greater than zero")

    test = DiagnosticTest(
        centre_id=centre_id,
        name=test_in.name,
        description=test_in.description,
        price=test_in.price,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


def get_tests_by_centre(db: Session, centre_id: uuid.UUID, active_only: bool = True) -> list[DiagnosticTest]:
    # Verify centre exists
    get_centre_by_id(db, centre_id)

    query = db.query(DiagnosticTest).filter(DiagnosticTest.centre_id == centre_id)
    if active_only:
        query = query.filter(DiagnosticTest.is_active == True)
    return query.all()


def get_test_by_id(db: Session, test_id: uuid.UUID) -> DiagnosticTest:
    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == test_id).first()
    if not test:
        raise NotFoundException(detail=f"Diagnostic test with ID '{test_id}' not found")
    return test

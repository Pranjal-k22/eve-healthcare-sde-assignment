import uuid
from sqlalchemy.orm import Session, joinedload
from app.models.diagnostic_centre import DiagnosticCentre
from app.schemas.centre import CentreCreateRequest
from app.core.exceptions import NotFoundException, BadRequestException


def create_centre(db: Session, centre_in: CentreCreateRequest) -> DiagnosticCentre:
    name_clean = centre_in.name.strip()
    location_clean = centre_in.location.strip()

    if not name_clean:
        raise BadRequestException(detail="Centre name cannot be empty")
    if not location_clean:
        raise BadRequestException(detail="Centre location cannot be empty")

    centre = DiagnosticCentre(
        name=name_clean,
        location=location_clean,
        contact_email=centre_in.contact_email,
        contact_phone=centre_in.contact_phone,
    )
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


def get_centres(db: Session, active_only: bool = True) -> list[DiagnosticCentre]:
    query = db.query(DiagnosticCentre).options(joinedload(DiagnosticCentre.tests))
    if active_only:
        query = query.filter(DiagnosticCentre.is_active == True)
    return query.all()


def get_centre_by_id(db: Session, centre_id: uuid.UUID) -> DiagnosticCentre:
    centre = (
        db.query(DiagnosticCentre)
        .options(joinedload(DiagnosticCentre.tests))
        .filter(DiagnosticCentre.id == centre_id)
        .first()
    )
    if not centre:
        raise NotFoundException(detail=f"Diagnostic centre with ID '{centre_id}' not found")
    return centre

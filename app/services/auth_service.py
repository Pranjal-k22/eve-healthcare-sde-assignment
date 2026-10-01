import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, decode_access_token
from app.core.exceptions import BadRequestException, UnauthorizedException
from app.models.user import User
from app.schemas.auth import UserSignupRequest

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def register_user(db: Session, user_in: UserSignupRequest) -> User:
    # Normalize email to lower case
    normalized_email = user_in.email.lower().strip()

    # Check for existing email in DB
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise BadRequestException(detail="Email already registered")

    hashed_pwd = get_password_hash(user_in.password)
    user = User(
        email=normalized_email,
        hashed_password=hashed_pwd,
        full_name=user_in.full_name.strip(),
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise BadRequestException(detail="Email already registered")


def authenticate_user(db: Session, email: str, password: str) -> User:
    normalized_email = email.lower().strip()
    user = db.query(User).filter(User.email == normalized_email).first()
    
    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedException(detail="Invalid email or password")
    
    if not user.is_active:
        raise UnauthorizedException(detail="User account is disabled")

    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    user_id_str: str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException(detail="Invalid token payload")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException(detail="Invalid user ID in token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise UnauthorizedException(detail="User not found or inactive")

    return user

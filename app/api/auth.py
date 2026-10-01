from datetime import timedelta
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.schemas.auth import UserSignupRequest, UserLoginRequest, TokenResponse, UserResponse
from app.services.auth_service import register_user, authenticate_user, get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserSignupRequest, db: Session = Depends(get_db)):
    user = register_user(db=db, user_in=user_in)
    return user


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(credentials: UserLoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db=db, email=credentials.email, password=credentials.password)
    expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=expires_minutes),
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_minutes * 60,
    )


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

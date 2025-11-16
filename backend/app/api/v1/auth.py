from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Annotated
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.db.database import get_db
from app.schemas.user import User, UserCreate
from app.schemas.token import Token
from app.core import security
from app.models.user import User as UserModel

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = security.decode_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = db.query(UserModel).filter(UserModel.username == username).first()
    if user is None:
        raise credentials_exception

    return User.model_validate(user)


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    existing_user = db.query(UserModel).filter(
        (UserModel.username == user_in.username) | (UserModel.email == user_in.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    # Create new user
    db_user = UserModel(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        password_hash=security.get_password_hash(user_in.password),
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return User.model_validate(db_user)


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """Login with username and password"""
    user = db.query(UserModel).filter(UserModel.username == form_data.username).first()

    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token = security.create_access_token(data={"sub": user.username})
    refresh_token = security.create_refresh_token(data={"sub": user.username})

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=User)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Get current user information"""
    return current_user

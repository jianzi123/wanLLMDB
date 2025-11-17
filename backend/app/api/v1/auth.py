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
from app.core.audit import get_audit_logger
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

    if not token:
        print("DEBUG: get_current_user - No token provided")
        raise credentials_exception
    
    print(f"DEBUG: get_current_user - Token received: {token[:20]}...")

    # Check if token is blacklisted (revoked)
    if security.is_token_blacklisted(token):
        print("DEBUG: get_current_user - Token is blacklisted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = security.decode_token(token)
    if payload is None:
        print("DEBUG: get_current_user - Token decode failed")
        raise credentials_exception
    
    print(f"DEBUG: get_current_user - Token payload: {payload}")

    username: str = payload.get("sub")
    if username is None:
        print("DEBUG: get_current_user - No 'sub' in payload")
        raise credentials_exception
    
    print(f"DEBUG: get_current_user - Username from token: {username}")

    user = db.query(UserModel).filter(UserModel.username == username).first()
    if user is None:
        print(f"DEBUG: get_current_user - User not found: {username}")
        raise credentials_exception
    
    print(f"DEBUG: get_current_user - User found: {user.username}, active: {user.is_active}")

    return User.model_validate(user)


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    audit = get_audit_logger(db)

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

    # Audit log: User registration
    audit.log_user_created(
        admin_user=db_user,  # Self-registration
        new_user_id=db_user.id,
        new_username=db_user.username,
        request=request,
    )

    return User.model_validate(db_user)


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """Login with username and password"""
    audit = get_audit_logger(db)
    user = db.query(UserModel).filter(UserModel.username == form_data.username).first()

    # Check credentials
    if not user or not security.verify_password(form_data.password, user.password_hash):
        # Audit log: Failed login attempt
        audit.log_auth_failure(
            username=form_data.username,
            reason="invalid_credentials",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        # Audit log: Failed login (inactive user)
        audit.log_auth_failure(
            username=form_data.username,
            reason="inactive_user",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    # Create tokens
    access_token = security.create_access_token(data={"sub": user.username})
    refresh_token = security.create_refresh_token(data={"sub": user.username})

    # Audit log: Successful login
    audit.log_auth_success(user=user, request=request)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=User)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Get current user information"""
    return current_user


@router.post("/logout")
async def logout(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Logout by revoking the current access token.

    The token will be added to a blacklist and will no longer be valid.
    Client should also delete the token from local storage.
    """
    audit = get_audit_logger(db)
    success = security.revoke_token(token)

    # Get user model for audit logging
    user = db.query(UserModel).filter(UserModel.username == current_user.username).first()

    # Audit log: User logout
    if user:
        audit.log_logout(user=user, token_revoked=success, request=request)

    if success:
        return {"message": "Successfully logged out", "token_revoked": True}
    else:
        # Token was invalid or Redis unavailable
        # Still return success to client (they wanted to logout anyway)
        return {
            "message": "Logged out (token blacklist unavailable)",
            "token_revoked": False,
            "warning": "Token was not blacklisted due to system unavailability"
        }

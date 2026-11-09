from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM
from app.database.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    if not token:
        raise unauthorized
    try:
        subject = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM]).get("sub")
    except JWTError as exc:
        raise unauthorized from exc
    user = db.get(User, subject) if subject else None
    if not user:
        raise unauthorized
    return user


def current_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user

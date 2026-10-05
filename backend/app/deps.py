import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import Role, User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = decode_token(creds.credentials)
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired token")
    if user is None:
        raise HTTPException(401, "Unknown user")
    return user  # role comes from the DB row, not the token claim


def require_agent(user: User = Depends(current_user)) -> User:
    if user.role != Role.agent.value:
        raise HTTPException(403, "Support agents only")
    return user


def require_customer(user: User = Depends(current_user)) -> User:
    if user.role != Role.customer.value:
        raise HTTPException(403, "Customers only")
    return user

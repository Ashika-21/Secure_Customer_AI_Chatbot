import os
from datetime import datetime, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from auth import get_db
from models import Customer

security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"


def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        customer_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    customer = db.get(Customer, customer_id)

    if customer is None:
        raise HTTPException(status_code=401, detail="Customer not found")

    return customer
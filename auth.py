import os
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Customer

router = APIRouter(prefix="/auth", tags=["Authentication"])

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
TOKEN_MINUTES = 30

if not JWT_SECRET or len(JWT_SECRET) < 32:
    raise RuntimeError("Set a JWT_SECRET of at least 32 characters in .env")

OTP_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
OTP_COOLDOWN_SECONDS = 60


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def now_utc():
    return datetime.now(timezone.utc)


def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


class PhoneRequest(BaseModel):
    phone: str = Field(pattern=r"^\d{10}$")


class OTPVerifyRequest(BaseModel):
    phone: str = Field(pattern=r"^\d{10}$")
    otp: str = Field(pattern=r"^\d{6}$")


@router.post("/request-otp")
def request_otp(data: PhoneRequest, db: Session = Depends(get_db)):
    customer = db.scalar(
        select(Customer).where(Customer.phone == data.phone)
    )

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    now = now_utc()

    if customer.otp_last_sent_at:
        last_sent = customer.otp_last_sent_at
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)

        elapsed = (now - last_sent).total_seconds()
        if elapsed < OTP_COOLDOWN_SECONDS:
            wait = int(OTP_COOLDOWN_SECONDS - elapsed) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {wait} seconds before requesting another OTP"
            )

    otp = f"{secrets.randbelow(1_000_000):06d}"
    customer.otp_hash = hash_otp(otp)
    customer.otp_expires_at = now + timedelta(minutes=OTP_MINUTES)
    customer.otp_attempts = 0
    customer.otp_last_sent_at = now
    db.commit()

    # Development-only delivery: print OTP in the local server terminal.
    # Never return OTP in the API response.
    if os.getenv("DEV_OTP_ENABLED", "false").lower() == "true":
        print(f"Development OTP for {data.phone}: {otp}")

    return {"message": "If the customer is eligible, an OTP request was processed."}


@router.post("/verify-otp")
def verify_otp(data: OTPVerifyRequest, db: Session = Depends(get_db)):
    customer = db.scalar(
        select(Customer).where(Customer.phone == data.phone)
    )

    if customer is None or not customer.otp_hash:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    now = now_utc()
    expires = customer.otp_expires_at

    if expires is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if now >= expires:
        customer.otp_hash = None
        customer.otp_expires_at = None
        customer.otp_attempts = 0
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    if customer.otp_attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Maximum OTP attempts reached")

    if not hmac.compare_digest(customer.otp_hash, hash_otp(data.otp)):
        customer.otp_attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # OTP is single-use.
    customer.otp_hash = None
    customer.otp_expires_at = None
    customer.otp_attempts = 0
    db.commit()

    token = jwt.encode(
        {
            "sub": str(customer.id),
            "exp": now + timedelta(minutes=TOKEN_MINUTES),
            "iat": now,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_minutes": TOKEN_MINUTES,
    }
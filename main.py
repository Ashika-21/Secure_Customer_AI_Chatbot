import logging
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.exc import SQLAlchemyError
from database import test_database_connection
from auth import router as auth_router
from security import get_current_customer
from models import Customer
from invoices import router as invoices_router
from conversations import router as conversations_router
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Secure Customer AI Chatbot")

# OTP authentication endpoints
app.include_router(auth_router)
app.include_router(invoices_router)
app.include_router(conversations_router)

@app.get("/")
def home():
    return {
        "message": "Secure Customer AI Chatbot API is running"
    }


@app.get("/health/database")
def database_health():
    try:
        result = test_database_connection()
        return {
            "database": "connected",
            "test_result": result
        }
    except SQLAlchemyError:
        logging.exception("Database connection failed")
        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )


@app.get("/customer/me")
def get_my_profile(
    customer: Customer = Depends(get_current_customer)
):
    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone
    }
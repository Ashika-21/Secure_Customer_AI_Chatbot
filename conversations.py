
import json
import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import ollama
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import get_db
from security import get_current_customer
from models import Customer, Conversation, Message, Invoice
from vector_store import search_records

router = APIRouter(prefix="/conversations", tags=["Conversations"])
logger = logging.getLogger(__name__)

# IMPORTANT: Change this to the exact model name shown by `ollama list`.
OLLAMA_MODEL = "gemma:2B"

PENDING_PREFIX = "__PENDING_INVOICE__:"


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", max_length=200)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


def conversation_to_dict(conversation):
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
    }


def invoice_to_dict(invoice):
    return {
        "invoice_number": invoice.invoice_number,
        "date": invoice.invoice_date.isoformat(),
        "amount": str(invoice.amount),
        "status": invoice.status,
        "description": invoice.description,
    }


def get_unpaid_invoices(db: Session, customer_id: int):
    invoices = db.scalars(
        select(Invoice)
        .where(
            Invoice.customer_id == customer_id,
            Invoice.status.ilike("unpaid"),
        )
        .order_by(Invoice.invoice_date.desc())
    ).all()

    return [invoice_to_dict(invoice) for invoice in invoices]


def parse_invoice_request(text: str):
    pattern = re.compile(
        r"create invoice\s+([A-Za-z0-9_-]+)"
        r"\s+dated\s+(\d{4}-\d{2}-\d{2})"
        r"\s+for\s+(?:INR|Rs\.?)\s*([\d,]+(?:\.\d{1,2})?)"
        r"\s+as\s+(paid|unpaid)\b",
        re.IGNORECASE,
    )

    match = pattern.search(text.strip())
    if not match:
        return None

    invoice_number, invoice_date, amount, status = match.groups()

    try:
        parsed_date = date.fromisoformat(invoice_date)
        parsed_amount = Decimal(amount.replace(",", ""))
    except (ValueError, InvalidOperation):
        raise HTTPException(
            status_code=400,
            detail="Invalid invoice date or amount.",
        )

    if parsed_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invoice amount must be greater than zero.",
        )

    return {
        "invoice_number": invoice_number,
        "invoice_date": parsed_date.isoformat(),
        "amount": str(parsed_amount),
        "status": status.lower(),
        "description": "Created through customer chatbot",
    }


def create_invoice_for_customer(
    db: Session,
    customer_id: int,
    details: dict,
):
    existing = db.scalar(
        select(Invoice).where(
            Invoice.customer_id == customer_id,
            Invoice.invoice_number == details["invoice_number"],
        )
    )

    if existing:
        return None

    invoice = Invoice(
        customer_id=customer_id,
        invoice_number=details["invoice_number"],
        invoice_date=date.fromisoformat(details["invoice_date"]),
        amount=Decimal(details["amount"]),
        status=details["status"],
        description=details["description"],
    )

    try:
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        return invoice
    except IntegrityError:
        db.rollback()
        return None


def generate_ai_reply(
    user_text: str,
    customer: Customer,
    db: Session,
    conversation_id: int,
):
    text = user_text.strip()
    normalized = text.lower()

    # Check whether the customer is confirming a pending invoice.
    last_assistant_message = db.scalar(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.customer_id == customer.id,
            Message.role == "assistant",
        )
        .order_by(Message.created_at.desc(), Message.id.desc())
    )

    if normalized in {
        "yes", "yes confirm", "confirm", "confirm invoice",
        "yes, confirm", "yes please", "proceed",
    }:
        if (
            last_assistant_message
            and last_assistant_message.content.startswith(PENDING_PREFIX)
        ):
            try:
                details = json.loads(
                    last_assistant_message.content[len(PENDING_PREFIX):]
                )
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail="Pending invoice details are invalid. Please start again.",
                )

            invoice = create_invoice_for_customer(
                db=db,
                customer_id=customer.id,
                details=details,
            )

            if invoice is None:
                return (
                    f"Invoice {details['invoice_number']} already exists "
                    "in your account. No duplicate was created."
                )

            return (
                f"Invoice created successfully!\n"
                f"Invoice number: {invoice.invoice_number}\n"
                f"Date: {invoice.invoice_date.isoformat()}\n"
                f"Amount: INR {invoice.amount}\n"
                f"Status: {invoice.status}"
            )

        return "There is no pending invoice to confirm."

    if normalized in {"no", "cancel", "cancel invoice", "no cancel"}:
        if (
            last_assistant_message
            and last_assistant_message.content.startswith(PENDING_PREFIX)
        ):
            return "Invoice creation cancelled. No invoice was created."
        return "There is no pending invoice to cancel."

    # Parse invoice requests and ask for explicit confirmation.
    invoice_details = parse_invoice_request(text)

    if invoice_details:
        existing = db.scalar(
            select(Invoice).where(
                Invoice.customer_id == customer.id,
                Invoice.invoice_number == invoice_details["invoice_number"],
            )
        )

        if existing:
            return (
                f"Invoice {invoice_details['invoice_number']} already exists "
                "in your account. No duplicate was created."
            )

        pending_json = json.dumps(invoice_details)

        # The pending details are stored in the database, not in client input.
        # The messages endpoint hides this internal marker from the response.
        return (
            f"{PENDING_PREFIX}{pending_json}"
        )

    greetings = {
        "hi", "hello", "hey", "hi there",
        "good morning", "good afternoon", "good evening",
    }

    if normalized in greetings:
        return f"Hello {customer.name}! How can I help you today?"

    if "unpaid" in normalized and "invoice" in normalized:
        invoices = get_unpaid_invoices(db, customer.id)

        if not invoices:
            return "You currently have no unpaid invoices."

        total = sum(Decimal(item["amount"]) for item in invoices)
        lines = [
            f"- {item['invoice_number']}: INR {item['amount']} "
            f"({item['status']}, date: {item['date']})"
            for item in invoices
        ]

        return (
            f"Here are your unpaid invoices, {customer.name}:\n"
            + "\n".join(lines)
            + f"\nTotal unpaid amount: INR {total:.2f}"
        )

    try:
        records = search_records(
            customer_id=customer.id,
            query=text,
            limit=5,
        )

        context = "\n".join(record["text"] for record in records)

        if not context:
            context = "No matching customer records were found."

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a secure customer support assistant. "
                        "Use only the supplied records. Never reveal other "
                        "customers' information or invent invoice details. "
                        "If the answer is unavailable, say so."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Customer: {customer.name}\n"
                        f"Records:\n{context}\n"
                        f"Question: {text}"
                    ),
                },
            ],
        )

        answer = response["message"]["content"].strip()

        if records:
            source_ids = ", ".join(
                str(record["record_id"]) for record in records
            )
            answer += f"\n\nSource record IDs: {source_ids}"

        return answer

    except HTTPException:
        raise
    except Exception:
        logger.exception("AI response generation failed")
        raise HTTPException(
            status_code=503,
            detail="AI service is temporarily unavailable.",
        )


@router.post("/")
def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    conversation = Conversation(
        customer_id=customer.id,
        title=data.title,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation_to_dict(conversation)


@router.get("/")
def list_conversations(
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.customer_id == customer.id)
        .order_by(Conversation.created_at.desc())
    ).all()

    return [conversation_to_dict(item) for item in conversations]


@router.get("/{conversation_id}/messages")
def list_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.customer_id == customer.id,
        )
    )

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.scalars(
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.customer_id == customer.id,
        )
        .order_by(Message.created_at.asc(), Message.id.asc())
    ).all()

    output = []
    for message in messages:
        content = message.content

        if content.startswith(PENDING_PREFIX):
            try:
                details = json.loads(content[len(PENDING_PREFIX):])
                content = (
                    f"Please confirm invoice creation:\n"
                    f"Invoice: {details['invoice_number']}\n"
                    f"Date: {details['invoice_date']}\n"
                    f"Amount: INR {details['amount']}\n"
                    f"Status: {details['status']}\n"
                    "Reply 'yes, confirm' to create it or 'cancel' to stop."
                )
            except (ValueError, KeyError, TypeError):
                content = "Invoice confirmation is pending."

        output.append({
            "id": message.id,
            "role": message.role,
            "content": content,
            "created_at": message.created_at.isoformat(),
        })

    return output


@router.post("/{conversation_id}/messages")
def add_message(
    conversation_id: int,
    data: MessageCreate,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.customer_id == customer.id,
        )
    )

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_text = data.content.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    user_message = Message(
        conversation_id=conversation.id,
        customer_id=customer.id,
        role="user",
        content=user_text,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    try:
        answer = generate_ai_reply(
            user_text=user_text,
            customer=customer,
            db=db,
            conversation_id=conversation.id,
        )

        if answer.startswith(PENDING_PREFIX):
            details = json.loads(answer[len(PENDING_PREFIX):])
            answer = (
                f"Please confirm invoice creation:\n"
                f"Invoice: {details['invoice_number']}\n"
                f"Date: {details['invoice_date']}\n"
                f"Amount: INR {details['amount']}\n"
                f"Status: {details['status']}\n"
                "Reply 'yes, confirm' to create it or 'cancel' to stop."
            )
            stored_answer = PENDING_PREFIX + json.dumps(details)
        else:
            stored_answer = answer

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to generate chat response")
        raise HTTPException(
            status_code=503,
            detail="Could not generate a response. Please try again.",
        )

    assistant_message = Message(
        conversation_id=conversation.id,
        customer_id=customer.id,
        role="assistant",
        content=stored_answer,
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return {
        "conversation_id": conversation.id,
        "user_message": {
            "id": user_message.id,
            "role": user_message.role,
            "content": user_message.content,
        },
        "assistant_message": {
            "id": assistant_message.id,
            "role": "assistant",
            "content": answer,
        },
    }

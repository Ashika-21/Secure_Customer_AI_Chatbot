
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_db
from security import get_current_customer
from models import Customer, Invoice

router = APIRouter(prefix="/invoices", tags=["Invoices"])


def invoice_to_dict(invoice: Invoice):
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date.isoformat(),
        "amount": str(invoice.amount),
        "status": invoice.status,
        "description": invoice.description,
    }


@router.get("/")
def get_my_invoices(
    status: str | None = None,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    query = select(Invoice).where(
        Invoice.customer_id == customer.id
    )

    if status:
        normalized_status = status.strip().lower()

        if normalized_status not in {"paid", "unpaid"}:
            raise HTTPException(
                status_code=400,
                detail="Status must be paid or unpaid",
            )

        query = query.where(
            Invoice.status.ilike(normalized_status)
        )

    invoices = db.scalars(
        query.order_by(Invoice.invoice_date.desc())
    ).all()

    return [invoice_to_dict(invoice) for invoice in invoices]


@router.get("/unpaid")
def get_my_unpaid_invoices(
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    invoices = db.scalars(
        select(Invoice)
        .where(
            Invoice.customer_id == customer.id,
            Invoice.status.ilike("unpaid"),
        )
        .order_by(Invoice.invoice_date.desc())
    ).all()

    return [invoice_to_dict(invoice) for invoice in invoices]


@router.get("/{invoice_id}")
def get_my_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    invoice = db.scalar(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.customer_id == customer.id,
        )
    )

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    return invoice_to_dict(invoice)
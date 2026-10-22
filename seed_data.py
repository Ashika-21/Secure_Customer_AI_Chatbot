from datetime import date
from decimal import Decimal
from sqlalchemy import select
from database import SessionLocal
from models import Customer, Invoice

customers_data = [
    {
        "name": "Arun",
        "phone": "9876543210",
        "invoices": [
            ("INV-101", date(2026, 10, 1), "1500.00", "unpaid"),
            ("INV-102", date(2026, 10, 3), "2500.00", "paid"),
            ("INV-103", date(2026, 10, 5), "1200.00", "unpaid"),
            ("INV-104", date(2026, 10, 8), "3000.00", "paid"),
            ("INV-105", date(2026, 10, 10), "1800.00", "unpaid"),
        ],
    },
    {
        "name": "Deepa",
        "phone": "9123456780",
        "invoices": [
            ("INV-201", date(2026, 10, 2), "900.00", "unpaid"),
            ("INV-202", date(2026, 10, 4), "2100.00", "paid"),
            ("INV-203", date(2026, 10, 6), "1600.00", "unpaid"),
            ("INV-204", date(2026, 10, 9), "2800.00", "paid"),
            ("INV-205", date(2026, 10, 11), "1100.00", "unpaid"),
        ],
    },
    {
        "name": "Karthik",
        "phone": "9000000003",
        "invoices": [
            ("INV-301", date(2026, 10, 1), "1300.00", "paid"),
            ("INV-302", date(2026, 10, 3), "1700.00", "unpaid"),
            ("INV-303", date(2026, 10, 5), "2200.00", "paid"),
            ("INV-304", date(2026, 10, 7), "800.00", "unpaid"),
            ("INV-305", date(2026, 10, 10), "1900.00", "paid"),
        ],
    },
    {
        "name": "Priya",
        "phone": "9000000004",
        "invoices": [
            ("INV-401", date(2026, 10, 2), "1400.00", "unpaid"),
            ("INV-402", date(2026, 10, 4), "2400.00", "paid"),
            ("INV-403", date(2026, 10, 6), "1000.00", "unpaid"),
            ("INV-404", date(2026, 10, 8), "3200.00", "paid"),
            ("INV-405", date(2026, 10, 12), "1600.00", "unpaid"),
        ],
    },
]


def seed_data():
    with SessionLocal() as db:
        for customer_data in customers_data:
            customer = db.scalar(
                select(Customer).where(
                    Customer.phone == customer_data["phone"]
                )
            )

            if customer is None:
                customer = Customer(
                    name=customer_data["name"],
                    phone=customer_data["phone"],
                )
                db.add(customer)
                db.flush()

            for number, invoice_date, amount, status in customer_data["invoices"]:
                existing_invoice = db.scalar(
                    select(Invoice).where(
                        Invoice.customer_id == customer.id,
                        Invoice.invoice_number == number,
                    )
                )

                if existing_invoice is None:
                    db.add(
                        Invoice(
                            customer_id=customer.id,
                            invoice_number=number,
                            invoice_date=invoice_date,
                            amount=Decimal(amount),
                            status=status,
                            description=f"Sample invoice {number}",
                        )
                    )

        db.commit()

    print("Seed data completed: 4 customers and up to 20 invoices.")


if __name__ == "__main__":
    seed_data()
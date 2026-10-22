
import logging
import os
from database import SessionLocal
from models import Invoice
from vector_store import store_record, close_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FAIL_FLAG = "simulate_index_failure.flag"


def main():
    if os.path.exists(FAIL_FLAG):
        os.remove(FAIL_FLAG)
        raise RuntimeError(
            "Simulated indexing failure. Run the script again to retry."
        )

    db = SessionLocal()
    indexed_count = 0

    try:
        invoices = db.query(Invoice).all()

        for invoice in invoices:
            text = (
                f"Invoice number: {invoice.invoice_number}, "
                f"date: {invoice.invoice_date}, "
                f"amount: INR {invoice.amount}, "
                f"status: {invoice.status}, "
                f"description: {invoice.description}"
            )

            store_record(
                customer_id=invoice.customer_id,
                record_id=invoice.id,
                text=text,
            )
            indexed_count += 1

        logger.info("Successfully indexed %s invoices.", indexed_count)

    except Exception:
        logger.exception("Indexing failed. Run the script again to retry.")
        raise

    finally:
        db.close()
        close_vector_store()


if __name__ == "__main__":
    main()

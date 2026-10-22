
from database import SessionLocal
from models import Customer
from vector_store import search_records, close_vector_store


def test_customer_search():
    db = SessionLocal()

    try:
        customer = db.query(Customer).filter(
            Customer.phone == "9876543210"
        ).first()

        if not customer:
            print("Arun customer not found.")
            return

        results = search_records(
            customer_id=customer.id,
            query="What unpaid invoices do I have?"
        )

        print("\nArun's search results:")

        if not results:
            print("No matching records found.")

        for record in results:
            print(record["text"])

    finally:
        db.close()
        close_vector_store()


if __name__ == "__main__":
    test_customer_search()

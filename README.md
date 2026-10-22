# Secure Customer AI Chatbot

## Project Overview
The Secure Customer AI Chatbot is an AI-based application that helps customers check their invoices and get information securely. It uses customer authentication to protect private data.

## Technologies Used
- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Qdrant
- Ollama
- JWT Authentication

## Features
- OTP-based customer login
- OTP expiry, attempt limit, and resend cooldown
- Secure customer data isolation
- View unpaid invoices and invoice details
- Create invoices after customer confirmation
- Prevent duplicate invoices
- AI chatbot with greeting support
- Vector search for customer records
- Persistent conversations and messages
- Indexing failure simulation and recovery

## Sample Customers
- Arun
- Deepa

The project uses sample customer and invoice data for testing.

## Installation

1. Clone the repository:

   ```bash
   git clone YOUR_GITHUB_REPOSITORY_URL
   ```

2. Open the project folder:

   ```bash
   cd Secure_Customer_AI_Chatbot
   ```

3. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   Windows:

   ```powershell
   .venv\Scripts\activate
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file and configure the database URL and JWT secret.

6. Run database migrations:

   ```bash
   python -m alembic upgrade head
   ```

7. Start the application:

   ```bash
   uvicorn main:app --reload
   ```

8. Open the API documentation:

   http://127.0.0.1:8000/docs

## Security
- Customer records are restricted to the authenticated customer.
- OTPs expire and can only be used once.
- Invoice creation requires confirmation.
- Environment secrets and private configuration should not be committed to GitHub.

## Testing
The project was tested for OTP security, customer isolation, invoice creation, duplicate prevention, unpaid invoice retrieval, and vector indexing recovery.

## Future Improvements
- Improve AI response accuracy.
- Add more customer support features.
- Improve error handling and automated testing.

## Author
Ashika K
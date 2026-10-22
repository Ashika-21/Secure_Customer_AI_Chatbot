from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# 1. Customers table
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)

    # OTP security fields
    otp_hash = Column(String(255), nullable=True)
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    otp_attempts = Column(Integer, nullable=False, default=0)
    otp_last_sent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    invoices = relationship(
        "Invoice",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    conversations = relationship(
        "Conversation",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    messages = relationship(
        "Message",
        back_populates="customer",
        cascade="all, delete-orphan",
        foreign_keys="Message.customer_id"
    )


# 2. Invoices table
class Invoice(Base):
    __tablename__ = "invoices"

    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "invoice_number",
            name="uq_customer_invoice_number"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    invoice_number = Column(String(50), nullable=False)
    invoice_date = Column(Date, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), nullable=False, default="unpaid")
    description = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    customer = relationship("Customer", back_populates="invoices")


# 3. Conversations table
class Conversation(Base):
    __tablename__ = "conversations"

    __table_args__ = (
        UniqueConstraint(
            "id",
            "customer_id",
            name="uq_conversation_customer"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    title = Column(String(200), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    customer = relationship(
        "Customer",
        back_populates="conversations"
    )

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )


# 4. Messages table
class Message(Base):
    __tablename__ = "messages"

    __table_args__ = (
        ForeignKeyConstraint(
            ["conversation_id", "customer_id"],
            ["conversations.id", "conversations.customer_id"],
            ondelete="CASCADE",
            name="fk_message_conversation_customer"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    conversation_id = Column(Integer, nullable=False)
    customer_id = Column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )

    customer = relationship(
        "Customer",
        back_populates="messages",
        foreign_keys=[customer_id]
    )

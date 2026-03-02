"""Database models for e-commerce API."""

from sqlalchemy import Column, String, Integer, Numeric, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    category_id = Column(String, index=True)
    stock_quantity = Column(Integer, default=0)
    images = Column(JSON, default=[])
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    product_id = Column(String, index=True)
    quantity = Column(Integer, default=1)
    added_at = Column(DateTime)


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    items = Column(JSON)
    total_amount = Column(Numeric(10, 2))
    shipping_address = Column(JSON)  # PII: contains name, address, phone
    payment_intent_id = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True)
    product_id = Column(String, index=True)
    user_id = Column(String)
    rating = Column(Integer)
    content = Column(Text)  # No sanitization
    created_at = Column(DateTime)

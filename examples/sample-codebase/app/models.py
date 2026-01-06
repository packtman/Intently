"""Database models for sample application."""

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """User model with sensitive data."""
    
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)  # Sensitive
    name = Column(String)
    phone = Column(String)  # PII
    ssn = Column(String)  # Highly sensitive PII
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)


class Session(Base):
    """Session model."""
    
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True)
    user_id = Column(String)
    token = Column(String)  # Sensitive
    expires_at = Column(DateTime)


class AuditLog(Base):
    """Audit log for security events."""
    
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True)
    user_id = Column(String)
    action = Column(String)
    ip_address = Column(String)
    timestamp = Column(DateTime)


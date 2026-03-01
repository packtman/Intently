"""Database models for patient portal."""

from sqlalchemy import Column, String, DateTime, JSON, Date
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    date_of_birth = Column(Date)
    ssn = Column(String)  # PHI — stored without encryption
    insurance_id = Column(String)
    medical_record_number = Column(String)
    phone = Column(String)
    email = Column(String)
    emergency_contact = Column(JSON)


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(String, primary_key=True)
    patient_id = Column(String, index=True)
    record_type = Column(String)
    content = Column(JSON)  # PHI — stored without encryption
    provider_id = Column(String)
    created_at = Column(DateTime)


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True)
    patient_id = Column(String, index=True)
    provider_id = Column(String)
    date = Column(DateTime)
    reason = Column(String)
    status = Column(String, default="scheduled")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    sender_id = Column(String)
    recipient_id = Column(String)
    subject = Column(String)
    body = Column(String)  # PHI — not encrypted
    created_at = Column(DateTime)
    read_at = Column(DateTime, nullable=True)

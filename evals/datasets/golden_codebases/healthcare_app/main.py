"""Healthcare patient portal API — intentionally flawed for eval testing."""

from fastapi import FastAPI, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel

app = FastAPI(title="Patient Portal")
security = HTTPBearer()


class AppointmentCreate(BaseModel):
    provider_id: str
    date: str
    reason: str


class MessageCreate(BaseModel):
    recipient_id: str
    subject: str
    body: str


@app.get("/api/patients/{patient_id}/records")
async def get_records(patient_id: str, token: str = Depends(security)):
    """Get patient medical records — no audit logging."""
    return {"records": []}


@app.post("/api/appointments")
async def create_appointment(appt: AppointmentCreate, token: str = Depends(security)):
    """Schedule appointment."""
    return {"appointment_id": "apt_1"}


@app.get("/api/appointments")
async def list_appointments(token: str = Depends(security)):
    """List appointments."""
    return {"appointments": []}


@app.post("/api/messages")
async def send_message(msg: MessageCreate, token: str = Depends(security)):
    """Send message — content not encrypted, stored as plain text."""
    return {"message_id": "msg_1"}


@app.get("/api/messages")
async def get_messages(token: str = Depends(security)):
    """Get messages."""
    return {"messages": []}


@app.post("/api/prescriptions/{rx_id}/refill")
async def request_refill(rx_id: str, token: str = Depends(security)):
    """Request prescription refill — no rate limiting."""
    return {"refill_id": "rfll_1"}


@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: str):
    """Get patient details — NO AUTH (vulnerability)."""
    return {
        "id": patient_id,
        "first_name": "Jane",
        "last_name": "Doe",
        "ssn": "123-45-6789",
        "date_of_birth": "1990-01-15",
    }

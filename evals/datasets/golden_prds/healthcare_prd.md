# Patient Portal

## Overview

Build a patient portal that allows patients to view their medical records, schedule appointments, and communicate with healthcare providers.

## Summary

HIPAA-compliant patient portal with medical record access, appointment scheduling, and secure messaging between patients and providers.

## Features

- Patient login with MFA
- View medical records (lab results, prescriptions, visit notes)
- Schedule and manage appointments
- Secure messaging with healthcare providers
- Prescription refill requests
- Insurance information management
- Emergency contact management

## User Stories

As a patient, I want to view my lab results online so that I don't have to call the office.

As a patient, I want to message my doctor securely so that I can ask follow-up questions.

As a patient, I want to schedule appointments online so that I don't have to wait on hold.

## API Changes

- `GET /api/patients/{id}/records` - Get medical records
- `POST /api/appointments` - Schedule appointment
- `GET /api/appointments` - List appointments
- `POST /api/messages` - Send secure message
- `GET /api/messages` - Get messages
- `POST /api/prescriptions/{id}/refill` - Request refill

## Data Models

### Patient
```
Patient {
  id: UUID
  first_name: String
  last_name: String
  date_of_birth: Date
  ssn: String (encrypted)
  insurance_id: String
  medical_record_number: String
  phone: String
  email: String
  emergency_contact: JSON
}
```

### MedicalRecord
```
MedicalRecord {
  id: UUID
  patient_id: UUID
  record_type: String
  content: JSON (encrypted)
  provider_id: UUID
  created_at: DateTime
}
```

## Security Considerations

- All endpoints require authentication with MFA
- PHI must be encrypted at rest and in transit
- Audit logging for all PHI access (HIPAA requirement)
- Session timeout after 15 minutes of inactivity
- Role-based access control (patient, provider, admin)

## External Integrations

- Epic/Cerner EHR system for medical records
- Twilio for appointment reminders (SMS)

## Privacy Requirements

- HIPAA compliance required for all PHI
- Minimum necessary standard — only show data needed for context
- Patient consent required before sharing records
- Breach notification within 72 hours

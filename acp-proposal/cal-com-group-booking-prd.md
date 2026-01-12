# Product Requirements Document: Group Booking Feature

**Product:** Cal.com  
**Feature:** Group Booking / Multi-Attendee Events  
**Author:** Product Team  
**Status:** Draft  
**Target Release:** Q2 2026

---

## Overview

Enable hosts to create event types that allow multiple attendees to book the same time slot simultaneously. This is essential for webinars, group coaching sessions, workshops, and team office hours.

## Problem Statement

Currently, Cal.com only supports 1:1 bookings where each time slot can only be booked by a single attendee. Users hosting group sessions must use workarounds like external registration forms or manual coordination.

### User Pain Points
- Coaches running group sessions manually track participants via spreadsheets
- Webinar hosts can't use Cal.com for registration
- Team leads can't offer "office hours" where multiple reports can join

## Proposed Solution

Add a "Group Booking" event type that allows:
- Multiple attendees per time slot (configurable max capacity)
- Attendee list visibility options
- Waitlist when capacity is reached
- Automatic notifications as spots fill

---

## Functional Requirements

### 1. Event Type Configuration

Hosts can create a new event type with group settings:

| Setting | Description | Default |
|---------|-------------|---------|
| Max attendees | Maximum participants per slot | 10 |
| Min attendees | Minimum to confirm (else cancel) | 1 |
| Show attendee count | Display "X spots left" publicly | Yes |
| Show attendee names | Display who else is attending | No |
| Enable waitlist | Allow signups when full | Yes |

### 2. Booking Flow

**For Attendees:**
1. Select available time slot
2. See remaining capacity ("3 of 10 spots available")
3. Enter booking details (name, email, notes)
4. Receive confirmation with calendar invite

**For Hosts:**
1. View all attendees per slot in dashboard
2. Send bulk messages to attendees
3. Export attendee list (CSV)
4. Cancel individual attendees or entire slot

### 3. Waitlist Management

When a slot reaches capacity:
- New bookings go to waitlist
- If attendee cancels, first waitlister is auto-promoted
- Waitlisters receive notification of their position
- Hosts can manually promote waitlist members

### 4. Notifications

| Event | Recipient | Channel |
|-------|-----------|---------|
| New booking | Host | Email |
| Slot confirmed | All attendees | Email |
| Spot opened (waitlist) | Next waitlister | Email |
| Reminder (24h) | All attendees | Email |
| Cancellation | Host + affected attendees | Email |

### 5. Calendar Integration

- Single calendar event created for host with all attendee emails
- Individual calendar invites sent to each attendee
- Support for Google Calendar, Outlook, Apple Calendar

### 6. API Endpoints

```
POST /v2/event-types
  - Add: groupSettings object

GET /v2/bookings/{id}/attendees
  - List all attendees for a group booking

POST /v2/bookings/{id}/attendees
  - Add attendee to existing group booking

DELETE /v2/bookings/{id}/attendees/{attendeeId}
  - Remove specific attendee

GET /v2/bookings/{id}/waitlist
  - Get waitlist for a booking slot

POST /v2/bookings/{id}/waitlist/{waitlistId}/promote
  - Promote waitlist member to confirmed
```

---

## Technical Requirements

### Database Changes

New tables required:
- `group_event_settings` - stores group configuration per event type
- `booking_attendees` - stores multiple attendees per booking
- `waitlist_entries` - manages waitlist queue

### Authentication

- Use existing Cal.com OAuth flow
- API endpoints require valid access token
- Webhook events signed with existing mechanism

### Performance

- Support up to 500 attendees per slot
- Booking page should load in under 2 seconds
- Real-time capacity updates via WebSocket

---

## UI/UX Requirements

### Host Dashboard
- New "Group" toggle when creating event type
- Attendee management table with bulk actions
- Capacity visualization (progress bar)

### Public Booking Page
- Show available spots dynamically
- Display "Waitlist" button when full
- Optional: Show attendee avatars/names

### Mobile
- Fully responsive design
- Native share functionality

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Adoption | 20% of new event types use group booking |
| Completion rate | >80% of started group bookings completed |
| Waitlist conversion | >30% of waitlisters eventually attend |

---

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Design | 2 weeks | Figma mockups, API spec |
| Backend | 3 weeks | Database, API endpoints |
| Frontend | 3 weeks | Host dashboard, booking page |
| Testing | 1 week | QA, load testing |
| Beta | 2 weeks | Limited rollout |

---

## Open Questions

1. Should we support recurring group events in v1?
2. Pricing: Is this a Pro/Enterprise feature only?
3. Integration with Stripe for paid group events?

---

## Appendix

### Competitive Analysis

| Platform | Max Group Size | Waitlist | API |
|----------|----------------|----------|-----|
| Calendly | 100 | Yes | Yes |
| Acuity | 50 | No | Yes |
| Cal.com (proposed) | 500 | Yes | Yes |

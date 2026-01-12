# Product Requirements Document: Team Availability Sync

**Product:** Cal.com  
**Feature:** Team Availability Aggregation & Smart Scheduling  
**Author:** Product Team  
**Status:** Draft  
**Target Release:** Q2 2026

---

## Overview

Enable teams to find optimal meeting times by aggregating individual availability across team members. The system calculates overlap windows and suggests the best slots for team meetings, client calls, and cross-timezone coordination.

## Problem Statement

Scheduling meetings with multiple team members is painful. Organizers must manually check each person's calendar, account for timezone differences, and find overlapping free slots. This wastes hours per week for team leads and operations staff.

---

## Functional Requirements

### 1. Team Availability View

A unified dashboard showing:
- Combined team availability as a heatmap
- Individual member calendars (expandable)
- Timezone-aware time slots
- Buffer time between meetings

### 2. Smart Slot Suggestions

Algorithm ranks available slots by:
- Number of team members available
- Preference scores (morning person vs. night owl)
- Meeting fatigue (avoid back-to-back heavy days)
- Historical booking patterns

### 3. Availability Rules Engine

Team admins can define rules:
- Core hours (e.g., "No meetings before 9am local time")
- Focus time blocks (e.g., "No meetings Tuesday afternoons")
- Maximum meeting hours per day/week
- Minimum break between meetings

### 4. External Calendar Sync

Sync availability from:
- Google Calendar
- Microsoft Outlook / Office 365
- Apple iCloud Calendar
- CalDAV servers

---

## Technical Requirements

### Authentication & Authorization ✅

**OAuth 2.0 Scopes Required:**
| Scope | Purpose | Sensitivity |
|-------|---------|-------------|
| `team:read` | View team membership | Low |
| `team:availability:read` | Read team availability data | Medium |
| `team:availability:write` | Update availability rules | Medium |
| `calendar:read` | Read connected calendar events | High |
| `calendar:write` | Create/modify calendar events | High |

**Authorization Rules:**
- Team members can view aggregated availability only for teams they belong to
- Individual calendar details require explicit sharing consent from calendar owner
- Availability rules can only be modified by team admins or the individual user
- API tokens are scoped to minimum required permissions

**RBAC Levels:**
| Role | View Team Availability | View Individual Calendars | Edit Rules |
|------|------------------------|---------------------------|------------|
| Team Member | ✅ | Own only | Own only |
| Team Admin | ✅ | ✅ (with consent) | Team + Own |
| Org Admin | ✅ | ✅ (with consent) | All |

**Security Controls:**
- All endpoints require valid JWT with appropriate scopes
- CSRF tokens required for state-changing operations
- Rate limiting: 100 requests/min for reads, 20 requests/min for writes
- Audit logging for all availability data access
- Calendar data encrypted at rest (AES-256)

### API Endpoints

```
GET /v2/teams/{teamId}/availability
  - Query params: date_range, timezone, include_individual
  - Auth: team:availability:read scope
  - Returns: aggregated availability slots

POST /v2/teams/{teamId}/availability/suggest
  - Body: { duration, required_attendees, optional_attendees, preferences }
  - Auth: team:availability:read scope
  - Returns: ranked slot suggestions

GET /v2/users/{userId}/availability-rules
  - Auth: team:availability:read scope + user consent or self
  - Returns: user's availability rules

PUT /v2/users/{userId}/availability-rules
  - Auth: team:availability:write scope + admin or self
  - Body: { core_hours, focus_blocks, max_meetings, min_break }
  - Returns: updated rules

POST /v2/calendars/sync
  - Auth: calendar:read scope
  - Body: { provider, credentials }
  - Returns: sync status

GET /v2/teams/{teamId}/availability/heatmap
  - Auth: team:availability:read scope
  - Query params: week_start, granularity
  - Returns: availability density data for visualization
```

### Database Schema

```sql
-- Team availability rules
CREATE TABLE team_availability_rules (
  id UUID PRIMARY KEY,
  team_id UUID REFERENCES teams(id),
  rule_type VARCHAR(50),  -- 'core_hours', 'focus_block', 'max_meetings'
  rule_config JSONB,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- User availability preferences
CREATE TABLE user_availability_preferences (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  preference_type VARCHAR(50),
  preference_value JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Calendar sync connections
CREATE TABLE calendar_connections (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  provider VARCHAR(50),  -- 'google', 'outlook', 'apple', 'caldav'
  credentials_encrypted BYTEA,
  last_sync_at TIMESTAMP,
  sync_status VARCHAR(20),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Cached availability windows
CREATE TABLE availability_cache (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  date DATE,
  available_slots JSONB,
  computed_at TIMESTAMP,
  expires_at TIMESTAMP
);
```

### Performance Requirements

- Availability calculation for 20-person team: < 500ms
- Heatmap generation: < 1 second
- Calendar sync: Background job, < 30 seconds per calendar
- Real-time updates via WebSocket for active dashboard users

---

## UI/UX Requirements

### Team Dashboard

- Weekly/monthly heatmap view
- Click slot to see who's available
- Drag to select time range for suggestions
- Filter by team member

### Slot Suggestion Modal

- Top 5 recommended slots
- Show availability score (e.g., "4/5 required attendees free")
- One-click to create meeting
- Option to override suggestions

### Settings Page

- Availability rules configuration
- Calendar connection management
- Sharing preferences

---

## Integration Points

### Webhooks

Events emitted:
- `team.availability.updated` - when rules change
- `calendar.sync.completed` - when calendar sync finishes
- `calendar.sync.failed` - when sync encounters errors

### Third-Party Integrations

- Slack: Share availability link, receive suggestions
- Zoom: Auto-attach meeting link to created events
- Zapier: Trigger workflows on availability changes

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to find meeting slot | -60% vs manual |
| Team feature adoption | 40% of teams with 5+ members |
| Calendar sync retention | 80% still connected after 30 days |

---

## Open Questions

1. How do we handle DST transitions mid-meeting-series?
2. Should we expose availability API to external partners?
3. Mobile app support in v1?

---

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Design | 2 weeks | UX flows, API spec |
| Backend | 4 weeks | Rules engine, sync jobs |
| Frontend | 3 weeks | Dashboard, settings |
| Integration | 2 weeks | Slack, Zoom, webhooks |
| Testing | 1 week | Load testing, edge cases |

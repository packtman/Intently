# End-to-End Test Specifications

This document outlines the E2E test scenarios that should pass for the Intently Desktop app.
These tests verify the complete user flows across the application.

## Test Environment Requirements

- Backend server must be running
- Test API keys configured (can use mock keys for testing)
- Test codebase available at a known path
- Test PRD files available

## Critical User Flows

### 1. Application Startup

**Test: App launches successfully**
- [ ] Application window opens without errors
- [ ] Sidebar navigation is visible
- [ ] Dashboard loads (or offline state if backend not running)
- [ ] Backend status indicator shows correct state

**Test: Backend auto-connect**
- [ ] If backend is running, app connects automatically
- [ ] Connection status updates within 5 seconds
- [ ] No error dialogs on startup

### 2. Settings Configuration

**Test: Configure backend path**
- [ ] Navigate to Settings page
- [ ] Click Browse for Intently path
- [ ] Select valid directory
- [ ] Path appears in input field
- [ ] Save Settings successfully

**Test: Configure API keys**
- [ ] Enter OpenAI API key
- [ ] Enter Anthropic API key
- [ ] Keys are masked (password type)
- [ ] Save Settings stores keys securely
- [ ] Keys persist after app restart

**Test: Start/Stop backend**
- [ ] Start button enabled when path is configured
- [ ] Click Start begins backend process
- [ ] Status changes to "Connecting..."
- [ ] Status changes to "Online" when ready
- [ ] Stop button appears when online
- [ ] Click Stop terminates backend
- [ ] Status changes to "Offline"

### 3. Create New Review

**Test: Complete review creation flow**

Step 1 - PRD Input:
- [ ] Navigate to New Review page
- [ ] Page shows PRD step first
- [ ] Enter title in title field
- [ ] Paste PRD content in textarea
- [ ] Continue button becomes enabled
- [ ] Click Continue advances to step 2

Step 2 - Codebase Selection:
- [ ] Codebase step is shown
- [ ] Click Browse opens directory picker
- [ ] Select codebase directory
- [ ] Path appears in input
- [ ] Language checkboxes are visible
- [ ] Default languages are selected (Python, Kotlin, TypeScript)
- [ ] Can toggle languages on/off
- [ ] Continue button becomes enabled
- [ ] Click Continue advances to step 3

Step 3 - Configuration:
- [ ] Config step is shown
- [ ] AI-Powered Analysis toggle is visible
- [ ] Toggle is ON by default
- [ ] Dimension checkboxes are visible
- [ ] Security is selected by default
- [ ] Can select multiple dimensions
- [ ] API key inputs appear when AI is enabled
- [ ] Warning shows if no API keys
- [ ] Continue button works

Step 4 - Review Summary:
- [ ] Summary step shows all selections
- [ ] PRD title is displayed
- [ ] Codebase path is displayed
- [ ] Selected dimensions are shown
- [ ] Start Product Review button is visible
- [ ] Click Start submits review
- [ ] Loading state appears
- [ ] Navigates to review detail page

**Test: Load PRD from file**
- [ ] Click Select File on PRD step
- [ ] File picker opens with markdown filter
- [ ] Select .md file
- [ ] Content loads into textarea
- [ ] Filename (without extension) becomes title

**Test: Preview Intent parsing**
- [ ] Enter PRD content
- [ ] Preview Intent button appears
- [ ] Click Preview Intent
- [ ] Loading indicator shows
- [ ] Intent preview card appears
- [ ] Shows feature count
- [ ] Shows API changes count
- [ ] Shows data entities

### 4. View Review Results

**Test: Review detail page loading**
- [ ] Navigate to a completed review
- [ ] Loading spinner shows initially
- [ ] Page loads with review data
- [ ] Title is displayed
- [ ] Risk rating badge is shown
- [ ] Statistics cards show counts

**Test: Review in progress**
- [ ] Navigate to running review
- [ ] Progress bar is visible
- [ ] Progress percentage updates
- [ ] Status message updates
- [ ] Page auto-refreshes status

**Test: Failed review**
- [ ] Navigate to failed review
- [ ] Error state is displayed
- [ ] Error message is shown
- [ ] No crash or blank screen

**Test: View findings**
- [ ] Findings table is visible
- [ ] Each finding shows severity badge
- [ ] Each finding shows dimension badge
- [ ] AI findings show AI badge
- [ ] Click finding expands details
- [ ] Description is shown
- [ ] Recommendation is shown
- [ ] Technical details shown (if available)
- [ ] Attack scenario shown (if available)

**Test: Filter by dimension**
- [ ] Dimension tabs are visible
- [ ] Click dimension tab filters findings
- [ ] Counts update in tabs
- [ ] All tab shows all findings
- [ ] No findings message if dimension has none

**Test: Export review**
- [ ] Export button is visible
- [ ] Click Export opens save dialog
- [ ] Save creates markdown file
- [ ] Notification confirms export

### 5. Dashboard

**Test: Dashboard with reviews**
- [ ] Statistics cards show correct counts
- [ ] Total Reviews count is accurate
- [ ] Critical count matches actual
- [ ] High count matches actual
- [ ] Completed count matches actual
- [ ] Recent reviews list shows up to 5
- [ ] Each review shows title
- [ ] Each review shows risk badge
- [ ] Each review shows findings count
- [ ] Click review navigates to detail

**Test: Dashboard empty state**
- [ ] With no reviews, empty state shows
- [ ] Create Review button is visible
- [ ] Click navigates to new review

**Test: Dashboard offline state**
- [ ] With backend offline, offline state shows
- [ ] Open Settings button is visible
- [ ] Documentation link works

### 6. Reviews List

**Test: View all reviews**
- [ ] Navigate to Reviews page
- [ ] All reviews are listed
- [ ] Search input is visible
- [ ] Filter dropdown is visible

**Test: Search reviews**
- [ ] Type in search box
- [ ] List filters in real-time
- [ ] Matching reviews shown
- [ ] Count updates

**Test: Filter by risk level**
- [ ] Select risk level from dropdown
- [ ] List shows only matching reviews
- [ ] Count updates
- [ ] "All Risk Levels" shows all

### 7. Navigation

**Test: Sidebar navigation**
- [ ] Dashboard link works
- [ ] New Review link works
- [ ] Settings link works
- [ ] Active link is highlighted
- [ ] Backend status shows in sidebar

**Test: Sidebar collapse**
- [ ] Collapse button is visible
- [ ] Click collapses sidebar
- [ ] Icons remain visible
- [ ] Click expands sidebar
- [ ] Labels reappear

**Test: Keyboard shortcuts**
- [ ] Cmd+N opens new review (via menu)
- [ ] Cmd+, opens settings (via menu)
- [ ] Cmd+O opens PRD file picker (via menu)

### 8. Error Handling

**Test: Network errors**
- [ ] API failure shows error message
- [ ] App doesn't crash
- [ ] Retry is possible

**Test: Backend disconnection**
- [ ] If backend dies, status updates
- [ ] Notification or message appears
- [ ] Can attempt reconnect

**Test: Invalid data handling**
- [ ] Malformed API response handled
- [ ] Missing fields don't crash app
- [ ] Fallback values used appropriately

## Performance Requirements

### Startup
- [ ] App window appears within 3 seconds
- [ ] Dashboard loads within 2 seconds (backend running)

### Navigation
- [ ] Page transitions under 500ms
- [ ] No visual glitches during navigation

### Review Processing
- [ ] Status polls every 2 seconds during review
- [ ] Progress bar updates smoothly
- [ ] No UI freezing during long reviews

### Data Display
- [ ] Reviews list with 50+ items renders smoothly
- [ ] Findings table with 100+ items is scrollable
- [ ] Charts render without delay

## Accessibility Requirements

- [ ] All interactive elements are keyboard accessible
- [ ] Focus states are visible
- [ ] Color contrast meets WCAG AA
- [ ] Screen reader compatible (labels present)

## Platform-Specific Tests

### macOS
- [ ] Traffic light buttons positioned correctly
- [ ] Title bar drag area works
- [ ] Native file dialogs open
- [ ] Notifications appear in notification center

### Windows (if supported)
- [ ] Window controls work correctly
- [ ] File dialogs work
- [ ] System notifications work

## Regression Checklist

Before each release, verify:

1. [ ] All Critical User Flows pass
2. [ ] No console errors in DevTools
3. [ ] No uncaught exceptions
4. [ ] Memory usage stable (no leaks)
5. [ ] Backend process terminates on app close
6. [ ] Settings persist across restarts
7. [ ] All dimension types render correctly (including yellow/purple)
8. [ ] Export produces valid markdown
9. [ ] All API endpoints respond correctly
10. [ ] Error states display properly

## Test Data Requirements

### Test PRD (save as test-feature.md)
```markdown
# Test Authentication Feature

## Overview
Implement user authentication with email/password.

## Features
- User registration
- User login
- Password reset
- Session management

## API Changes
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- POST /api/auth/reset-password

## Data Models
- User: id, email, password_hash, created_at
- Session: id, user_id, token, expires_at

## Security Considerations
- Hash passwords with bcrypt
- Use JWT for sessions
- Rate limit login attempts
```

### Test Codebase
Use any Python/TypeScript project with:
- At least 10 source files
- Some API endpoint definitions
- At least one auth-related file


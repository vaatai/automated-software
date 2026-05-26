# Dashboard Frontend Test Plan

## What Changed
A complete Next.js 16 dashboard frontend with 11 pages, dark mode layout, responsive sidebar, reusable UI components, and API integration layer. No backend is running, so tests verify that:
1. Every route renders without runtime errors (no blank white screen / React crash)
2. Layout shell (sidebar + header) renders correctly on every page
3. Each page shows its expected heading and page-specific UI elements
4. Error states display gracefully when backend is unavailable
5. Interactive elements (modals, forms, navigation) function correctly

## Test Cases

### Test 1: Layout Shell — Sidebar and Header render on Dashboard
**Steps:** Navigate to http://localhost:3000
**Pass criteria:**
- Sidebar is visible on the left with "AutoReg" brand text and Settings icon
- All 11 nav items are visible: Dashboard, Websites, Registrations, Running Tasks, Analytics, OTP Tracking, Workers, Queues, Daily Limits, Error Logs, Screenshots
- "Dashboard" nav item has blue/active highlight (text-blue-400)
- Header is visible at top with "Offline" WebSocket indicator (no WS server running)
- Footer shows "AutoReg Dashboard v1.0"
- Background is dark (gray-950)

### Test 2: Dashboard page — Error state on API failure
**Steps:** On http://localhost:3000, wait for API call to fail
**Pass criteria:**
- Page shows an ErrorBanner component (red-tinted box with AlertTriangle icon)
- Error message contains text related to connection failure (e.g. "fetch failed" or similar)
- No blank/white screen, no unhandled React error boundary crash

### Test 3: Navigate to /websites — Page-specific UI renders
**Steps:** Click "Websites" in sidebar
**Pass criteria:**
- URL changes to /websites
- "Websites" sidebar item gets blue active highlight; "Dashboard" loses it
- Page heading reads "Websites"
- "Add Website" blue button is visible with Plus icon
- Search input with placeholder "Search websites..." is present
- ErrorBanner appears (backend unavailable) OR Spinner then ErrorBanner

### Test 4: Website Create Modal — Opens and has correct form fields
**Steps:** On /websites, click "Add Website" button
**Pass criteria:**
- Modal overlay appears (dark backdrop)
- Modal title reads "Add Website"
- Four form fields visible: Name, Domain, Registration URL, Daily Limit
- Daily Limit field has default value "100"
- Cancel and Create buttons are visible
- Clicking Cancel closes the modal

### Test 5: Navigate to /registrations — Form renders correctly
**Steps:** Click "Registrations" in sidebar
**Pass criteria:**
- Heading reads "Trigger Registrations"
- Card with title "Queue New Registrations" is visible
- Form has: Website dropdown (with "Select website..." placeholder), Count input (default 1), Priority dropdown (High/Normal/Low)
- "Start Registrations" button is visible and disabled (no website selected)

### Test 6: Navigate to /analytics — Page with date range picker
**Steps:** Click "Analytics" in sidebar
**Pass criteria:**
- Heading reads "Analytics"
- Date range dropdown selector is visible with options (7/14/30/90 Days)
- ErrorBanner or Spinner appears (no backend data)

### Test 7: Navigate to /logs — Filter controls render
**Steps:** Click "Error Logs" in sidebar
**Pass criteria:**
- Heading reads "Error Logs"
- Search input with "Search logs..." placeholder
- Level dropdown with "All Levels" default (options: DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Two date picker inputs visible
- ErrorBanner appears or EmptyState with "No logs found"

### Test 8: Navigate to remaining pages — No crashes
**Steps:** Click through: OTP Tracking, Workers, Queues, Daily Limits, Screenshots
**Pass criteria for each:**
- Page renders without crash (no white screen)
- Correct heading appears: "OTP Verification Tracking", "Worker Monitoring", "Queue Monitoring", "Daily Limits", "Screenshots"
- Error state or empty state displays gracefully

### Test 9: Sidebar active state — Only current page highlighted
**Steps:** Navigate to /screenshots (last item)
**Pass criteria:**
- "Screenshots" nav item has blue highlight
- "Dashboard" nav item does NOT have blue highlight (plain gray text)
- All other nav items are gray (not highlighted)

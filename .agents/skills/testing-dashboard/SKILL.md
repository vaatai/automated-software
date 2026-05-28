---
name: testing-dashboard
description: Test the AutoReg dashboard frontend (Next.js) locally. Use when verifying UI changes to rentals, campaigns, or other dashboard pages.
---

# Testing AutoReg Dashboard

## Prerequisites

- Node.js installed
- Dashboard dependencies installed: `cd dashboard && npm install`

## Devin Secrets Needed

None required for frontend-only testing. Backend API keys (FIVESIM_API_KEY, PVAPINS_API_KEY, etc.) only needed for end-to-end tests.

## Starting the Dashboard

```bash
cd dashboard && npm run dev
# Runs on http://localhost:3000
```

## Authentication

The dashboard requires login. Since the login form uses `type="email"` validation, use the browser console to authenticate:

```javascript
// Authenticate via direct API call
fetch('/api/auth', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ identifier: 'admin', password: 'autoreg2024' })
}).then(r => r.json()).then(d => {
  localStorage.setItem('autoreg-auth-token', d.token || 'admin-session');
  localStorage.setItem('autoreg-display-name', d.name || 'admin');
  location.reload();
});
```

**Important:** localStorage keys use hyphens (`autoreg-auth-token`), not underscores.

## Mock API Routes (When Backend Unavailable)

The dashboard pages (rentals, campaigns, etc.) fetch from `/api/*` endpoints. Without the FastAPI backend running, pages show `ErrorBanner` and hide all interactive UI.

Create temporary Next.js API routes to mock responses:

- `dashboard/src/app/api/rentals/route.ts` → Return `{ items: [], total: 0 }`
- `dashboard/src/app/api/health/route.ts` → Return `{ status: "ok" }`
- `dashboard/src/app/api/websites/route.ts` → Return `{ items: [...], total: N }`

These mocks make pages render so you can test UI components (dropdowns, forms, dialogs).

## Testing Provider Selection Feature

### Rentals Page (`/rentals`)
1. Click "Rent New Number" button to open dialog
2. Verify "SMS Provider" dropdown exists with Server icon
3. Options: Auto (default order), PVAPins, 5SIM, SMS-Activate
4. Helper text changes based on country + provider:
   - India + Auto → "India: PVAPins → 5SIM → SMS-Activate"
   - Any + specific provider → "[provider] will be tried first, others as fallback"
   - Other countries + Auto → "5SIM → PVAPins → SMS-Activate"

### Campaigns Page (`/campaigns`)
1. Per-entry "Provider" column in Campaign Builder entries
2. Campaign-level "Default SMS Provider" dropdown below entries
3. Helper text: "India uses PVAPins first, others use 5SIM first"

## API Schema Validation

Validate backend schemas accept `preferred_provider` without running the full server:

```python
import sys
sys.path.insert(0, '.')
from api.rentals import RentNumberRequest
from api.campaigns import CampaignEntry, CampaignRequest

# Should not raise
RentNumberRequest(country='IN', preferred_provider='5sim')
CampaignEntry(website_id=1, country='IN', preferred_provider='pvapins')
CampaignRequest(entries=[CampaignEntry(website_id=1, country='US')], preferred_provider='sms-activate')
```

## Key Files

- `dashboard/src/app/rentals/page.tsx` — Rental UI with provider dropdown
- `dashboard/src/app/campaigns/page.tsx` — Campaign UI with per-entry and campaign-level dropdowns
- `api/rentals.py` — RentNumberRequest schema
- `api/campaigns.py` — CampaignEntry and CampaignRequest schemas
- `services/rental_service.py` — Provider reordering logic

## Tips

- The `useFetch` hook (at `dashboard/src/hooks/use-fetch.ts`) shows `ErrorBanner` on API failures, which hides all page content including buttons. Always ensure API mocks are working before testing UI.
- The VPS dashboard is at `http://178.105.219.213` but may not always have the latest code deployed.
- Window maximization on Ubuntu: `sudo apt-get install -y wmctrl && wmctrl -r :ACTIVE: -b add,maximized_vert,maximized_horz`

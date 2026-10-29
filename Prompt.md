Act as a Principal Full-Stack Developer and B2B SaaS Architect. 
I am building an MVP for a B2B startup called "SmartPitch". The product is a "No-code interactive proposal generator with deep reading analytics" to replace static PDF commercial offers. 

**TECH STACK (Strict Constraints):**
- Backend: Python 3, FastAPI, SQLAlchemy, SQLite (no complex DB setups required, local file is perfect).
- Frontend: HTML5, Vanilla JavaScript, Tailwind CSS (via CDN to avoid npm setups for the prototype), Chart.js (via CDN for analytics visualization).

**CORE MVP ARCHITECTURE:**
The system must consist of one single Python backend (`main.py`) serving three static HTML pages (`/static`):
1. `dashboard.html` (Sales Rep View)
2. `editor.html` (To create a new proposal)
3. `viewer.html` (The client-facing generated commercial proposal)

**1. DATABASE MODELS (SQLAlchemy):**
- `Proposal`: id, title, company_name, content_json, access_token (uuid).
- `TrackingEvent`: id, proposal_id, block_id, time_spent_seconds.

**2. BACKEND API ENDPOINTS (`main.py`):**
- `POST /api/proposal/create` -> receives basic text/pricing data, creates record, returns `access_token` for sharing.
- `GET /api/proposal/{token}` -> serves the public data to `viewer.html`.
- `POST /api/track` -> Highly critical. An endpoint receiving `{ token, block_id, time_spent_ms }`.
- `GET /api/stats/{token}` -> Returns grouped data to build the analytics dashboard.

**3. FRONTEND MAGICAL COMPONENT - The Tracker (`viewer.html` JS script):**
- When the generated proposal is opened by a client, it renders different sections: e.g., `<div id="section-intro">`, `<div id="section-pricing">`, `<div id="section-portfolio">`.
- WRITE A STRICT TRACKING SCRIPT using JavaScript `IntersectionObserver`. 
- Logic: When a section enters the viewport (threshold > 50%), start a timer. When it leaves the viewport, stop the timer, calculate duration, and send a JSON payload (using `fetch` or `navigator.sendBeacon`) to `POST /api/track`. 
- This simulates eye-tracking/reading analytics.

**4. DASHBOARD UI (`dashboard.html`):**
- Must look like an expensive, minimalist B2B enterprise software (Notion/Stripe aesthetic: White backgrounds, #0f172a slate text, extremely clean borders).
- Must have a bar chart using Chart.js displaying "Attention Heatmap" (Time spent on Intro vs Pricing vs Features) fetched from the backend.

**YOUR INSTRUCTIONS FOR EXECUTION:**
Output the files step by step. Do NOT cut corners.
Step 1: Write `requirements.txt` and terminal commands to run this.
Step 2: Provide `main.py` containing the FastAPI setup, DB schema, and endpoints. Wait for my confirmation ("Next") if hitting length limits.
Step 3: Provide `static/editor.html`.
Step 4: Provide `static/viewer.html` (containing the complex Observer JS script).
Step 5: Provide `static/dashboard.html` with Chart.js analytics logic.
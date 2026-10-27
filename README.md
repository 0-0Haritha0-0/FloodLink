# FloodLink — Real-Time Flood Disaster Management & Emergency Response Platform

> **UN Sustainable Development Goals (SDG) Alignment:**
> - **SDG 11: Sustainable Cities and Communities** *(Target 11.5: Significantly reduce deaths and economic losses caused by water-related disasters)*
> - **SDG 13: Climate Action** *(Target 13.1: Strengthen resilience and adaptive capacity to climate-related hazards and natural disasters)*

---

## 1. Project Overview

**FloodLink** is a lightweight, secure emergency response platform designed to bridge communication between citizens in flood distress and emergency disaster response coordinators.

### Core Capabilities:
- **Citizen SOS Reporting:** Rapid reporting of flood water depth, trapped individuals, and severity (Low, Medium, High, Critical) with automatic cryptographic tracking ID generation (`FL-XXXXXXXX`).
- **Real-Time Request Tracking:** Live 4-stage visual progress timeline (`Pending` → `Assigned` → `In Progress` → `Resolved`).
- **Coordinator Command Center:** Secure admin dashboard with key performance indicators (KPIs), incident triage, and rescue squad assignment.
- **Rescue Team Field Workflow:** Field dispatch queue for rescue units to view assigned emergencies, record operational notes, and resolve incidents.

---

## 2. System Architecture

FloodLink implements a clean **3-Tier Web Architecture**:

```
+-------------------------------------------------------------+
|                      PRESENTATION TIER                      |
|            React (Vite) + Plain CSS (Light Blue Theme)      |
|  - Citizen SOS Form         - Live Public Incident Feed     |
|  - Request Status Tracker   - Coordinator & Rescue Panels   |
+-------------------------------------------------------------+
                              |
                     HTTP / JSON (fetch)
                              |
+-------------------------------------------------------------+
|                      APPLICATION TIER                       |
|                       FastAPI Backend                       |
|  - Pydantic v2 Validation   - PBKDF2-HMAC-SHA256 Auth       |
|  - Cryptographic ID Gen     - Strict CORS & Error Handlers  |
+-------------------------------------------------------------+
                              |
                 Python sqlite3 (Parameterized)
                              |
+-------------------------------------------------------------+
|                          DATA TIER                          |
|                       SQLite Database                       |
|  - reports                  - active_tokens                 |
|  - admins                   - Indexes & CHECK Constraints   |
+-------------------------------------------------------------+
```

### Technology Stack
- **Frontend:** React 18, Vite 5, JavaScript, Vanilla CSS (responsive light blue/white theme).
- **Backend:** Python 3.13, FastAPI, Uvicorn, Pydantic 2.13.4.
- **Database:** SQLite via Python's built-in `sqlite3` standard library module.
- **Testing:** Comprehensive automated Python test suite.

---

## 3. Cybersecurity & Secure Software Engineering Design

As a cybersecurity-focused prototype, FloodLink implements multiple defense-in-depth principles:

1. **SQL Injection (SQLi) Immunity:**
   - Zero string concatenation in database queries.
   - 100% of SQL statements use parameterized queries (`?` placeholders).
   - SQLi payloads like `Robert'); DROP TABLE reports; --` are neutralized and stored purely as literal text.
2. **Gateway Input Validation (Firewall):**
   - Pydantic models validate data before it reaches application logic.
   - Leading/trailing whitespace is automatically sanitized.
   - Enums strictly enforce allowed severities (`Low`, `Medium`, `High`, `Critical`) and statuses.
3. **Database-Level Integrity Constraints:**
   - SQL `CHECK` constraints on table columns serve as a secondary defensive perimeter.
   - `UNIQUE` constraints on tracking IDs guarantee zero collision.
4. **Password Security (NIST SP 800-63B Compliant):**
   - Passwords hashed using **PBKDF2-HMAC-SHA256** with 100,000 iterations and a 16-byte random salt (`secrets.token_bytes(16)`).
   - Verification uses **constant-time string comparison** (`hmac.compare_digest`) to defeat timing side-channel attacks.
5. **Role-Based Access Control (RBAC):**
   - Privileged coordinator endpoints require the `admin` role.
   - Dispatched field rescue endpoints require the `rescue_team` role.
   - Active bearer tokens are stored and verified in SQLite.
6. **Cross-Origin Resource Sharing (CORS):**
   - Configured specifically for `http://localhost:5173` to prevent unauthorized cross-origin requests.
7. **Privacy by Design (Data Minimization):**
   - Only collects incident location and description necessary to coordinate rescue; no unnecessary personal identity information is collected.

---

## 4. Setup and Execution Instructions

### Prerequisites
- Python 3.10+ installed
- Node.js 18+ and npm installed

---

### Step 1: Start the FastAPI Backend
Open a terminal and run:

```powershell
cd floodlink/backend

# Run the backend dev server (auto-initializes SQLite database)
uvicorn app.main:app --reload --port 8000
```

- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Step 2: Start the React Frontend
Open a **second terminal** and run:

```powershell
cd floodlink/frontend

# Install dependencies (if not already installed)
npm.cmd install

# Start Vite development server
npm.cmd run dev
```

- Frontend UI: [http://localhost:5173](http://localhost:5173)

---

### Step 3: Run the Master Automated Test Suite
Open a **third terminal** and run:

```powershell
cd floodlink/backend
python tests/run_all_tests.py
```

This single command executes all 4 test suites:
- `test_stage2_full.py`: FastAPI configuration & Pydantic 2.13.4 validation.
- `test_stage3_db.py`: SQLite schema, tables, indexes, CHECK constraints, SQLi defense, and persistence.
- `test_stage4_reports.py`: SOS submission, ID uniqueness, and database persistence.
- `test_stages_5_to_8.py`: Report tracking, PBKDF2 authentication, admin dashboard, and rescue team workflows.

---

## 5. College Demonstration & Evaluation Guide

For your college project viva or practical demonstration, follow this step-by-step workflow:

### Demo Scenario: End-to-End Emergency Flood Rescue

#### Step 1: Citizen SOS Report
1. Open [http://localhost:5173](http://localhost:5173) in your browser.
2. Click on **"🆘 Report Flood"** in the top navigation.
3. Fill in the emergency details:
   - **Name:** *Pooja Sharma*
   - **Location:** *Near River Bridge, Ward 4*
   - **Severity:** *Critical*
   - **Description:** *Water entered ground floor, 3 elderly residents stranded on the roof.*
4. Click **"Submit Distress Report"**.
5. Note the generated tracking ID (e.g., `FL-A89D2F`).

#### Step 2: Citizen Status Tracking
1. Click **"Track Status Now"** in the confirmation modal (or go to **"🔍 Track Report"**).
2. The system displays the 4-step progress timeline showing status: **`Pending`** and *"Awaiting Coordinator Assignment"*.

#### Step 3: Coordinator Incident Triage & Dispatch (Admin)
1. Click **"🛡️ Admin Panel"** in the navigation.
2. Log in using default credentials:
   - **Username:** `admin`
   - **Password:** `AdminPass123!`
3. View the live incident counters: Total Incidents, Pending Triage, and Critical alerts.
4. In the table, find Pooja Sharma's report and click **"Manage / Assign"**.
5. Set:
   - **Status:** `Assigned`
   - **Rescue Squad:** `Team Alpha — Rapid Boat Rescue (Water Evacuation)`
   - **Coordinator Notes:** `Dispatched 2 motorized inflatable boats for immediate rooftop evacuation.`
6. Click **"Save Changes"**.

#### Step 4: Rescue Team Field Operations
1. Click **"🚤 Rescue Team"** in the navigation (or log in with `rescuer1` / `RescuePass123!`).
2. The field dispatch queue shows Pooja Sharma's emergency assigned to Team Alpha.
3. Click **"Update Progress / Resolve"**.
4. Set status to **`In Progress`** and enter field notes: `Team Alpha arrived at Ward 4 bridge via boat. Evacuation underway.`
5. Once complete, click **"Update Progress / Resolve"** again, select **`Resolved`**, and enter notes: `All 3 citizens evacuated safely to Ward 4 relief center.`

#### Step 5: Citizen Verification
1. Return to **"🔍 Track Report"** and re-check `FL-A89D2F`.
2. Notice the timeline is now 100% complete at **`Resolved`**, showing the dispatched unit and the complete operational rescue log!

---

## 6. Academic Limitations & Future Scope

### Honest Engineering Disclaimers:
- **Student Prototype:** This application is built as an academic prototype for college evaluation and demonstration of full-stack development and cybersecurity principles.
- **Simulated Dispatch:** Does not connect to live emergency 911/112 municipal dispatch systems or real-time hardware telemetry.
- **Local SQLite Storage:** Designed for single-server prototyping; production multi-node deployments would transition to PostgreSQL.

### Future Enhancements:
- GIS map integration using OpenStreetMap / Leaflet.
- SMS / WhatsApp webhook alerts using Twilio for citizens without active internet.
- AI-based flood depth estimation from citizen photos.

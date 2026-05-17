# 🐕 Watchdog Sentinel

> **Dead Man's Switch API** — CritMon Servers Inc.  
> Tracks remote device heartbeats and fires instant alerts the moment a device goes silent.

---

## Table of Contents

1. [Architecture Diagram](#architecture-diagram)
2. [Setup & Running](#setup--running)
3. [API Documentation](#api-documentation)
4. [Developer's Choice Feature](#developers-choice-feature)
5. [Project Structure](#project-structure)

---

## Architecture Diagram

### State Flowchart — Monitor Lifecycle

```
                          ┌─────────────────────────────┐
                          │   POST /monitors             │
                          │  {"id", "timeout", "email"}  │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────┐
                          │         ACTIVE               │
                          │  Countdown timer running     │
                          │  deadline = now + timeout    │
                          └───┬─────────────┬───────────┘
                              │             │
              POST /heartbeat │             │ POST /pause
                              │             │
                              ▼             ▼
                 ┌──────────────────┐  ┌──────────────────┐
                 │     ACTIVE       │  │     PAUSED        │
                 │  Timer reset to  │  │  deadline = None  │
                 │  full timeout    │  │  No alerts fire   │
                 └──────────────────┘  └────────┬─────────┘
                                                │
                                                │ POST /heartbeat
                                                │ (auto-unpause)
                                                ▼
                                       ┌──────────────────┐
                                       │     ACTIVE        │
                                       │  Timer restarted  │
                                       └──────────────────┘

                 ┌───────────────────────────────────────┐
                 │  Background Scheduler (ticks every 1s) │
                 │                                        │
                 │  IF now >= deadline AND status=ACTIVE: │
                 │    → status = DOWN                     │
                 │    → fire_alert() → console.log JSON   │
                 └───────────────────────────────────────┘

                 ┌──────────────────┐
                 │      DOWN         │
                 │  Alert fired.     │
                 │  Re-register to   │
                 │  start fresh.     │
                 └──────────────────┘
```

### Sequence Diagram — Happy Path vs. Alert Path

```
Device          API Server         Scheduler         Alert System
  │                │                   │                  │
  │─POST /monitors─▶                   │                  │
  │                │─── store Monitor──▶                  │
  │◀── 201 Created─│   deadline=T+60s  │                  │
  │                │                   │                  │
  │  (45s later)   │                   │                  │
  │─POST /heartbeat▶                   │                  │
  │                │── reset deadline ─▶                  │
  │◀─── 200 OK ────│   deadline=T+105s │                  │
  │                │                   │                  │
  │  (device dies) │                   │                  │
  │                │                   │── now≥deadline? ─▶
  │                │                   │   YES             │
  │                │◀── status=DOWN ───│                  │
  │                │                   │──fire_alert()────▶
  │                │                   │                  │── log JSON alert
```

---

## Setup & Running

### Prerequisites

- Python 3.10+
- `pip`

### Installation

```bash
# 1. Clone your fork
git clone https://github.com/<your-username>/watchdog-sentinel.git
cd watchdog-sentinel

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
python main.py
```

The API will be live at **http://localhost:8000**  
Interactive docs (Swagger UI) at **http://localhost:8000/docs**

### Running Tests

```bash
pytest tests/ -v
```

---

## API Documentation

### Base URL

```
http://localhost:8000
```

---

### `POST /monitors` — Register a Monitor

Start tracking a new device.

**Request Body**

```json
{
  "id": "device-123",
  "timeout": 60,
  "alert_email": "admin@critmon.com"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | ✅ | Unique device identifier |
| `timeout` | integer | ✅ | Countdown duration in seconds (5 – 86400) |
| `alert_email` | string | ✅ | Email address to alert on silence |

**Response — `201 Created`**

```json
{
  "id": "device-123",
  "timeout": 60,
  "alert_email": "admin@critmon.com",
  "status": "active",
  "created_at": "2025-06-15T10:00:00Z",
  "last_ping_at": null,
  "deadline": "2025-06-15T10:01:00Z",
  "alert_fired": false
}
```

**Error Responses**

| Code | Reason |
|---|---|
| `409 Conflict` | A monitor with this ID already exists |
| `422 Unprocessable` | Invalid input (bad email, timeout out of range) |

---

### `POST /monitors/{id}/heartbeat` — Send Heartbeat

Reset the countdown timer. Call this repeatedly to keep the monitor alive.

**Example**

```bash
curl -X POST http://localhost:8000/monitors/device-123/heartbeat
```

**Response — `200 OK`**

```json
{
  "message": "Heartbeat received. Timer reset.",
  "monitor_id": "device-123"
}
```

**Error Responses**

| Code | Reason |
|---|---|
| `404 Not Found` | Monitor ID does not exist |
| `410 Gone` | Monitor has already fired its alert (status: down) |

> **Note:** Sending a heartbeat to a **paused** monitor automatically unpauses it and restarts the timer.

---

### `POST /monitors/{id}/pause` — Pause a Monitor

Freeze the timer. Useful during planned maintenance to prevent false alarms.

**Example**

```bash
curl -X POST http://localhost:8000/monitors/device-123/pause
```

**Response — `200 OK`**

```json
{
  "message": "Monitor paused. No alerts will fire until the next heartbeat.",
  "monitor_id": "device-123"
}
```

**Resuming:** Call the heartbeat endpoint to automatically unpause.

---

### `GET /monitors` — List All Monitors *(Developer's Choice)*

Returns the full list of registered monitors and their current status. Ideal for a dashboard.

```bash
curl http://localhost:8000/monitors
```

**Response — `200 OK`**

```json
[
  {
    "id": "device-123",
    "status": "active",
    "deadline": "2025-06-15T10:02:30Z",
    ...
  },
  {
    "id": "solar-farm-7",
    "status": "down",
    ...
  }
]
```

---

### `GET /monitors/{id}` — Get a Single Monitor *(Developer's Choice)*

Inspect the current state of one device.

```bash
curl http://localhost:8000/monitors/device-123
```

---

### `DELETE /monitors/{id}` — Deregister a Monitor *(Developer's Choice)*

Permanently remove a monitor from the system.

```bash
curl -X DELETE http://localhost:8000/monitors/device-123
```

**Response — `200 OK`**

```json
{
  "message": "Monitor deregistered and removed.",
  "monitor_id": "device-123"
}
```

---

## Alert Output

When a device's timer expires, the system logs this to stdout:

```json
{
  "ALERT": "Device device-123 is down!",
  "device_id": "device-123",
  "alert_email": "admin@critmon.com",
  "timeout_seconds": 60,
  "last_ping_at": "2025-06-15T09:59:00Z",
  "time": "2025-06-15T10:01:00Z"
}
```

The `alerts.py` module includes a commented-out extension point to wire in real email (SMTP) or a webhook POST.

---

## Developer's Choice Feature

### Feature: Monitor Management Endpoints (`GET /monitors`, `GET /monitors/{id}`, `DELETE /monitors/{id}`)

**Why I added this:**

The core spec gives you the ability to *create* monitors and *ping* them — but no way to *observe* the system. In a real critical infrastructure context, this gap is dangerous:

- Support engineers can't check the status of 50 solar-farm devices at a glance.
- There's no way to clean up stale/decommissioned monitors, which would accumulate forever.
- Debugging is impossible without being able to inspect `deadline`, `last_ping_at`, and `status`.

The three added endpoints solve these real operational problems:

| Endpoint | Problem Solved |
|---|---|
| `GET /monitors` | Dashboard view — see all device statuses at once |
| `GET /monitors/{id}` | Debug individual device — confirm timer is resetting |
| `DELETE /monitors/{id}` | Lifecycle management — remove decommissioned devices |

These endpoints require zero extra dependencies and follow the same patterns as the core API, making the system production-usable rather than just demo-able.

---

## Project Structure

```
watchdog-sentinel/
├── main.py                  # Entry point — starts uvicorn
├── requirements.txt
├── .gitignore
├── app/
│   ├── main.py              # FastAPI app + lifespan events
│   ├── store.py             # In-memory store + Monitor dataclass
│   ├── scheduler.py         # Async background timer checker
│   ├── alerts.py            # Alert firing logic (log + extension point)
│   ├── schemas.py           # Pydantic request/response models
│   └── routers/
│       └── monitors.py      # All /monitors endpoints
└── tests/
    └── test_monitors.py     # 11 pytest tests covering all endpoints
```

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Framework | **FastAPI** | Async-native, auto-generates OpenAPI docs, Pydantic validation |
| Background tasks | **asyncio** | No extra dependency; native to Python's event loop |
| Validation | **Pydantic v2** | Fast, declarative, email validation built-in |
| Server | **Uvicorn** | ASGI server optimised for FastAPI |
| Tests | **pytest + TestClient** | Synchronous test client, no extra async complexity |

---

*Built for the Amaliteck Rwanda Backend Challenge.*

# EVE Healthcare — Backend Engineering Assignment

Production-ready backend API service for diagnostic test bookings, simulated payment processing, and idempotent payment webhooks built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, **Alembic**, and **Docker**.

---

## Executive Summary & Architecture Overview

This backend system powers the core workflow of a diagnostic healthcare platform where patients can browse diagnostic centres and tests, schedule test bookings, process payments, and sync payment status via idempotent provider webhooks.

### Key Highlights
- **100% Test Pass Rate**: 43 automated unit and integration tests passing cleanly across all modules.
- **Strict Idempotency & Race Protection**: DB-backed `event_id` unique constraint combined with row-level locks (`SELECT ... FOR UPDATE`) preventing duplicate payments or status corruption on repeated or concurrent webhook deliveries.
- **HMAC Signature Security**: Provider webhooks verified using SHA256 HMAC signatures (`X-Signature` header) computed over raw body bytes.
- **Server-Side Price Protection**: Immutable pricing derived strictly from `DiagnosticTest.price`. Client-submitted amounts are ignored.
- **Cross-Tenant Isolation**: Ownership validation on all user booking retrieval, cancellation, and payment operations (`403 FORBIDDEN`).
- **Production Containerization**: Multi-stage Docker setup with Docker Compose orchestrating PostgreSQL and automatic Alembic migrations.

---

## Tech Stack & Tooling

| Component | Technology | Rationale / Purpose |
| :--- | :--- | :--- |
| **Framework** | FastAPI (Python 3.11+) | Async ASGI framework with automatic Pydantic request validation and Swagger generation |
| **Database** | PostgreSQL 15/16 | Relational database enforcing strict foreign keys, unique constraints, and enum types |
| **ORM** | SQLAlchemy 2.0 | Type-safe declarative ORM with explicit session boundaries & row-level locking (`with_for_update()`) |
| **Migrations** | Alembic | Version-controlled schema migrations |
| **Security** | PyJWT & Direct `bcrypt` | HMAC-SHA256 JWT tokens & standard `bcrypt` password hashing |
| **Containerization** | Docker & Docker Compose | Containerized application & database orchestration |
| **Testing** | Pytest & HTTPX TestClient | End-to-end integration and unit testing suite |

---

## System Architecture & Domain Workflows

### Logical Flow Diagram

```text
                                   CLIENT / USER
                                         │
                                         ▼
                            ┌────────────────────────┐
                            │   JWT Bearer Auth      │
                            └────────────┬───────────┘
                                         │
                                         ▼
                       ┌──────────────────────────────────┐
                       │  POST /bookings (PENDING state)  │
                       └─────────────────┬────────────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
                 POST /payments/              POST /payments/webhook/
             (Simulated User Payment)        (Provider Webhook Callback)
                         │                               │
                         │                   ┌───────────┴───────────┐
                         │                   │  X-Signature Header   │
                         │                   │  HMAC-SHA256 Check    │
                         │                   └───────────┬───────────┘
                         │                               │
                         └───────────────┬───────────────┘
                                         │
                                         ▼
                         ┌───────────────────────────────┐
                         │   Idempotent Ledger Check     │
                         │   (event_id UNIQUE Constraint)│
                         └───────────────┬───────────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
                   Payment SUCCESS                Payment FAILED
                         │                               │
                         ▼                               ▼
                 Booking CONFIRMED                 Booking FAILED
```

---

## Database Schema Design

The relational schema is built on 6 core models with strict referential integrity:

1. **`users`**:
   - `id` (UUID, Primary Key)
   - `email` (VARCHAR 255, Unique Index, Required)
   - `hashed_password` (VARCHAR 255, Required)
   - `full_name` (VARCHAR 255, Required)
   - `is_active` (BOOLEAN, Default `True`)
   - `created_at`, `updated_at` (Timestamps with TZ)

2. **`diagnostic_centres`**:
   - `id` (UUID, Primary Key)
   - `name` (VARCHAR 255, Required)
   - `location` (VARCHAR 255, Required)
   - `is_active` (BOOLEAN, Default `True`)
   - `created_at`, `updated_at` (Timestamps with TZ)

3. **`diagnostic_tests`**:
   - `id` (UUID, Primary Key)
   - `centre_id` (UUID, Foreign Key -> `diagnostic_centres.id` RESTRICT)
   - `name` (VARCHAR 255, Required)
   - `description` (TEXT)
   - `price` (NUMERIC(10, 2), Required, > 0)
   - `is_active` (BOOLEAN, Default `True`)
   - `created_at`, `updated_at` (Timestamps with TZ)

4. **`bookings`**:
   - `id` (UUID, Primary Key)
   - `user_id` (UUID, Foreign Key -> `users.id` RESTRICT, Index)
   - `centre_id` (UUID, Foreign Key -> `diagnostic_centres.id` RESTRICT)
   - `test_id` (UUID, Foreign Key -> `diagnostic_tests.id` RESTRICT)
   - `appointment_date` (DateTime with TZ, Required)
   - `amount` (NUMERIC(10, 2), Required)
   - `status` (SQLEnum: `PENDING`, `CONFIRMED`, `FAILED`, `CANCELLED`, Index)
   - `created_at`, `updated_at` (Timestamps with TZ)

5. **`payments`**:
   - `id` (UUID, Primary Key)
   - `booking_id` (UUID, Foreign Key -> `bookings.id` RESTRICT, Index)
   - `transaction_id` (VARCHAR 255, Unique Index, Required)
   - `payment_method` (VARCHAR 50, Default `MOCK_PAYMENT`)
   - `amount` (NUMERIC(10, 2), Required)
   - `status` (SQLEnum: `SUCCESS`, `FAILED`)
   - `raw_response` (JSON)
   - `created_at` (Timestamp with TZ)

6. **`webhook_events`**:
   - `id` (UUID, Primary Key)
   - `event_id` (VARCHAR 255, Unique Index, Required) — *Primary Idempotency Ledger Key*
   - `provider_payment_id` (VARCHAR 255, Required)
   - `booking_id` (UUID, Foreign Key -> `bookings.id` RESTRICT)
   - `payload` (JSON, Required)
   - `processed_at` (Timestamp with TZ)

---

## API Surface & Endpoints

| Category | Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- | :--- |
| **System** | `GET` | `/health` | None | Application health & database ping check |
| **Auth** | `POST` | `/auth/signup` | None | Register new user account |
| **Auth** | `POST` | `/auth/login` | None | Authenticate user & return JWT token |
| **Auth** | `GET` | `/auth/me` | Bearer | Get authenticated user profile |
| **Centres** | `GET` | `/centres` | None | List active diagnostic centres |
| **Centres** | `POST` | `/centres` | Bearer | Create a new diagnostic centre |
| **Centres** | `GET` | `/centres/{centre_id}` | None | Retrieve diagnostic centre details |
| **Tests** | `POST` | `/centres/{centre_id}/tests` | Bearer | Add a diagnostic test to a centre |
| **Tests** | `GET` | `/centres/{centre_id}/tests` | None | List active tests offered by a centre |
| **Tests** | `GET` | `/tests/{test_id}` | None | Retrieve diagnostic test details |
| **Bookings** | `POST` | `/bookings` | Bearer | Create a test booking (`PENDING`). Past appointment date returns `422 Unprocessable Entity` |
| **Bookings** | `GET` | `/bookings` | Bearer | List current user's bookings (Supports query params: `page`, `page_size`) |
| **Bookings** | `GET` | `/bookings/{booking_id}` | Bearer | Retrieve booking details by ID (Ownership protected) |
| **Bookings** | `POST` | `/bookings/{booking_id}/cancel` | Bearer | Cancel a `PENDING` booking (Ownership protected) |
| **Payments** | `POST` | `/payments/` | Bearer | Process simulated payment (`SUCCESS`/`FAILED`). Row locked via `with_for_update()` |
| **Webhooks** | `POST` | `/payments/webhook/` | None / HMAC | Provider-facing idempotent payment status webhook. Verified via `X-Signature` header |

---

## Environment Variables Configuration

The application configures settings via `pydantic-settings` from environment variables or `.env`:

```env
# Application Configuration
APP_NAME="Eve Healthcare Assignment API"
ENV="development"
DEBUG=True

# Database Configuration
POSTGRES_USER=eve_user
POSTGRES_PASSWORD=eve_password
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=eve_healthcare_db
DATABASE_URL=postgresql://eve_user:eve_password@localhost:5432/eve_healthcare_db

# Security & JWT Configuration
SECRET_KEY=change_this_to_a_secure_random_key_in_production_32_bytes_min
WEBHOOK_SECRET=change_this_to_a_secure_webhook_secret_in_production_32_bytes_min
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

## Core Technical Features

### 1. Webhook Idempotency & HMAC Security
When payment providers send event webhooks:
- **HMAC Signature Check**: Webhook requests require an `X-Signature` header containing an HMAC-SHA256 signature computed over the raw body bytes using `WEBHOOK_SECRET`. Requests missing or containing an invalid signature return `401 Unauthorized`.
- **Database Unique Constraint**: Incoming `event_id` is queried against `webhook_events`. If found, processing returns `200 OK` with `status: "already_processed"`.
- **Concurrent Race Protection**: Concurrent duplicate webhook deliveries trigger PostgreSQL `UNIQUE` index constraint violation (`IntegrityError`), caught gracefully with session rollback.
- **State Transition Guard**: Webhook updates only apply to bookings currently in `PENDING` state. Replays against finalized bookings (`CONFIRMED`, `FAILED`, `CANCELLED`) are safely ignored.

### 2. Computing `X-Signature` Header (Copy-Paste Examples)

#### Python Example
```python
import hmac
import hashlib
import requests

secret = "whsec_supersecretmockkey123456789"
body = '{"event_id":"evt_wh_1001","provider_payment_id":"pay_prov_555","booking_id":"b9f8e7d6-1111-2222-3333-444455556666","status":"SUCCESS"}'

signature = hmac.new(secret.encode('utf-8'), body.encode('utf-8'), hashlib.sha256).hexdigest()

headers = {
    "Content-Type": "application/json",
    "X-Signature": signature
}

response = requests.post("http://localhost:8000/payments/webhook/", data=body, headers=headers)
print(response.json())
```

#### PowerShell Example
```powershell
$secret = "whsec_supersecretmockkey123456789"
$body = '{"event_id":"evt_wh_1001","provider_payment_id":"pay_prov_555","booking_id":"b9f8e7d6-1111-2222-3333-444455556666","status":"SUCCESS"}'

$hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($secret))
$hash = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($body))
$signature = [BitConverter]::ToString($hash).Replace("-", "").ToLower()

$headers = @{
    "Content-Type" = "application/json"
    "X-Signature" = $signature
}

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/payments/webhook/" -Headers $headers -Body $body
```

#### cURL / Bash Example
```bash
BODY='{"event_id":"evt_wh_1001","provider_payment_id":"pay_prov_555","booking_id":"b9f8e7d6-1111-2222-3333-444455556666","status":"SUCCESS"}'
SECRET='whsec_supersecretmockkey123456789'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

curl -X POST http://localhost:8000/payments/webhook/ \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIG" \
  -d "$BODY"
```

### 3. State Machine & Row-Level Locking
- **Initial State**: All newly created bookings start in `PENDING` state.
- **Row-Level Lock**: When processing payments or webhooks, the booking is locked using `db.query(Booking).filter(...).with_for_update().first()`, preventing double-payment race conditions.
- **Valid Transitions**:
  - `PENDING` -> `CONFIRMED` (via Payment SUCCESS)
  - `PENDING` -> `FAILED` (via Payment FAILED)
  - `PENDING` -> `CANCELLED` (via User Cancellation)
- Terminal states block further mutations (`400 Bad Request`).

### 4. Server-Side Price Integrity
Pricing is fetched directly from `DiagnosticTest.price` in PostgreSQL during booking creation. Client-submitted price inputs are ignored to prevent price tampering attacks.

---

## Local Setup & Runbook

### Prerequisites
- Python 3.11+
- PostgreSQL server (or Docker & Docker Compose)

### 1. Local Environment Configuration
Clone the repository and copy the environment template:
```bash
git clone https://github.com/Pranjal-k22/eve-healthcare-sde-assignment.git
cd eve-healthcare-sde-assignment
cp .env.example .env
```

Create a virtual environment and install dependencies:
```bash
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Database Migration & Server Execution
Ensure PostgreSQL is running locally with credentials matching `.env`, then run database migrations:
```bash
python -m alembic upgrade head
```

Start the FastAPI development server:
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access the interactive API documentation at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Running with Docker Compose (Recommended)

To launch the complete application stack (PostgreSQL database + FastAPI application + Automatic database migrations) with a single command:

```bash
docker compose up --build
```

The application will automatically wait for PostgreSQL to pass its health check, execute Alembic migrations, and start listening on port `8000`.

To stop the containers:
```bash
docker compose down
```

---

## Running Test Suite

Run the full automated test suite using `pytest`:

```bash
python -m pytest -v
```

### Test Suite Output Summary
```text
tests/test_auth.py ........                             [ 18%]
tests/test_bookings.py .......                           [ 34%]
tests/test_centres.py .....                             [ 46%]
tests/test_health.py ..                                 [ 51%]
tests/test_payments.py ........                         [ 69%]
tests/test_tests.py ......                              [ 83%]
tests/test_webhooks.py ........                         [100%]

======================= 43 passed in 63.78s =======================
```

---

## API Request & Response Examples

### 1. User Signup
**`POST /auth/signup`**
```json
{
  "email": "patient@example.com",
  "password": "SecurePassword123!",
  "full_name": "Jane Doe"
}
```
**Response (`201 Created`)**:
```json
{
  "id": "a3b8c9d0-1234-5678-90ab-cdef12345678",
  "email": "patient@example.com",
  "full_name": "Jane Doe",
  "is_active": true,
  "created_at": "2026-10-01T12:00:00Z"
}
```

### 2. Create Booking
**`POST /bookings`** *(Headers: `Authorization: Bearer <JWT_TOKEN>`)*
```json
{
  "centre_id": "c1a2b3c4-0000-0000-0000-000000000001",
  "test_id": "t1a2b3c4-0000-0000-0000-000000000001",
  "appointment_date": "2026-10-15T10:30:00Z"
}
```
**Response (`201 Created`)**:
```json
{
  "id": "b9f8e7d6-1111-2222-3333-444455556666",
  "user_id": "a3b8c9d0-1234-5678-90ab-cdef12345678",
  "centre_id": "c1a2b3c4-0000-0000-0000-000000000001",
  "test_id": "t1a2b3c4-0000-0000-0000-000000000001",
  "appointment_date": "2026-10-15T10:30:00Z",
  "amount": "150.00",
  "status": "PENDING",
  "created_at": "2026-10-01T12:05:00Z"
}
```

### 3. Process Payment Webhook
**`POST /payments/webhook/`** *(Headers: `X-Signature: <HMAC_SHA256_HEX>`)*
```json
{
  "event_id": "evt_wh_1001",
  "provider_payment_id": "pay_prov_555",
  "booking_id": "b9f8e7d6-1111-2222-3333-444455556666",
  "status": "SUCCESS",
  "amount": "150.00",
  "payment_method": "CREDIT_CARD"
}
```
**Response (`200 OK`)**:
```json
{
  "status": "processed",
  "event_id": "evt_wh_1001",
  "message": "Webhook event processed successfully",
  "booking_id": "b9f8e7d6-1111-2222-3333-444455556666",
  "booking_status": "CONFIRMED"
}
```

---

## Engineering Assumptions & Limitations

- **Assumptions**: Payment providers furnish a unique string `event_id` for every distinct event, along with `provider_payment_id` and target `booking_id`.
- **Limitations**: Idempotency is managed within PostgreSQL database transaction boundaries using unique constraints and row-level locking (`with_for_update()`). For multi-region microservice deployments, a distributed locking mechanism (e.g., Redis `Redlock`) can be layered on top.

---

## Future Enhancements

1. **Rate Limiting**: Integrate `slowapi` or Redis token-bucket rate limiting on `/auth/login` and `/payments/webhook/`.
2. **Asynchronous Webhook Queue**: Integrate Celery or Arq with Redis for background retries of failed downstream webhook events.
3. **Structured JSON Logging**: Implement `structlog` for enhanced observability in cloud logging platforms (Datadog, AWS CloudWatch).

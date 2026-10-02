# EVE Healthcare — Backend Engineering Assignment

[![CI & Docker Verification](https://github.com/Pranjal-k22/eve-healthcare-sde-assignment/actions/workflows/ci.yml/badge.svg)](https://github.com/Pranjal-k22/eve-healthcare-sde-assignment/actions/workflows/ci.yml)

Backend API service for diagnostic test bookings, simulated payment processing, and idempotent payment webhooks built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, **Alembic**, and **Docker**.

---

## Overview

This project is a backend system for a diagnostic healthcare platform where users can browse diagnostic centres and tests, schedule appointments, process simulated payments, and handle provider webhooks reliably.

### Key Implementation Facts
- **Automated Test Suite**: 45 unit and integration tests passing cleanly across all API modules.
- **Idempotency & Race Protection**: Database-backed `event_id` unique constraint combined with row-level locks (`SELECT ... FOR UPDATE`) to prevent duplicate payments or status corruption during concurrent webhook deliveries.
- **HMAC Signature Verification**: Provider webhooks verified via SHA256 HMAC signatures (`X-Signature` header) calculated over raw HTTP body bytes.
- **Server-Side Price Derivation**: Booking amount is read directly from `DiagnosticTest.price` on the server instead of accepting price inputs from the client.
- **Resource Ownership Enforcement**: Ownership validation on user booking retrieval, cancellation, and payment endpoints (`403 FORBIDDEN`).
- **Containerized Environment**: Multi-container setup with Docker Compose orchestrating PostgreSQL, application startup, and automatic database migrations.

---

## Tech Stack

| Component | Technology | Rationale / Purpose |
| :--- | :--- | :--- |
| **Framework** | FastAPI (Python 3.11+) | Async ASGI framework with automatic Pydantic validation and interactive Swagger documentation |
| **Database** | PostgreSQL 15 | Relational storage enforcing foreign keys, unique constraints, and status enums |
| **ORM** | SQLAlchemy 2.0 | Declarative ORM with explicit session boundaries and row-level locking (`with_for_update()`) |
| **Migrations** | Alembic | Version-controlled database schema migrations |
| **Security** | PyJWT & `bcrypt` | HMAC-SHA256 JWT access tokens and `bcrypt` password hashing |
| **Containerization** | Docker & Docker Compose | Application containerization and PostgreSQL service orchestration |
| **Testing** | Pytest & HTTPX TestClient | Automated integration and unit testing suite |

---

## Architecture & Request Flow

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

## Database Design

The database schema consists of 6 models defined in SQLAlchemy and managed via Alembic migrations:

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
   - `created_at` (Timestamp with TZ)

3. **`diagnostic_tests`**:
   - `id` (UUID, Primary Key)
   - `centre_id` (UUID, Foreign Key -> `diagnostic_centres.id` CASCADE)
   - `name` (VARCHAR 255, Required)
   - `description` (TEXT)
   - `price` (NUMERIC(10, 2), Required, > 0)
   - `is_active` (BOOLEAN, Default `True`)
   - `created_at` (Timestamp with TZ)

4. **`bookings`**:
   - `id` (UUID, Primary Key)
   - `user_id` (UUID, Foreign Key -> `users.id` RESTRICT, Index)
   - `centre_id` (UUID, Foreign Key -> `diagnostic_centres.id` RESTRICT)
   - `test_id` (UUID, Foreign Key -> `diagnostic_tests.id` RESTRICT)
   - `appointment_date` (DateTime with TZ, Required)
   - `amount` (NUMERIC(10, 2), Required)
   - `status` (Enum: `PENDING`, `CONFIRMED`, `FAILED`, `CANCELLED`, Index)
   - `created_at`, `updated_at` (Timestamps with TZ)

5. **`payments`**:
   - `id` (UUID, Primary Key)
   - `booking_id` (UUID, Foreign Key -> `bookings.id` RESTRICT, Index)
   - `transaction_id` (VARCHAR 255, Unique Index, Required)
   - `payment_method` (VARCHAR 50, Default `MOCK_PAYMENT`)
   - `amount` (NUMERIC(10, 2), Required)
   - `status` (Enum: `SUCCESS`, `FAILED`)
   - `raw_response` (JSON)
   - `created_at` (Timestamp with TZ)

6. **`webhook_events`**:
   - `id` (UUID, Primary Key)
   - `event_id` (VARCHAR 255, Unique Index, Required)
   - `provider_payment_id` (VARCHAR 255, Required)
   - `booking_id` (UUID, Foreign Key -> `bookings.id` RESTRICT)
   - `payload` (JSON, Required)
   - `processed_at` (Timestamp with TZ)

---

## API Endpoints

| Category | Method | Path | Auth | Purpose | Success | Important Errors |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **System** | `GET` | `/` | None | API welcome & documentation discovery | `200 OK` | N/A |
| **System** | `GET` | `/health` | None | Service & database health check | `200 OK` | `500 Internal Error` |
| **Auth** | `POST` | `/auth/signup` | None | User account registration | `201 Created` | `400 Bad Request` |
| **Auth** | `POST` | `/auth/login` | None | Authenticate user & issue JWT bearer token | `200 OK` | `401 Unauthorized` |
| **Auth** | `GET` | `/auth/me` | Bearer | Get current user profile | `200 OK` | `401 Unauthorized` |
| **Centres** | `POST` | `/centres/` | Bearer | Create a new diagnostic centre | `201 Created` | `401 Unauthorized`, `422 Validation Error` |
| **Centres** | `GET` | `/centres/` | None | List active diagnostic centres | `200 OK` | `422 Validation Error` |
| **Centres** | `GET` | `/centres/{centre_id}` | None | Get diagnostic centre details | `200 OK` | `404 Not Found` |
| **Tests** | `POST` | `/tests/` | Bearer | Add a diagnostic test to a centre | `201 Created` | `400 Bad Request`, `401 Unauthorized`, `404 Not Found` |
| **Tests** | `GET` | `/tests/` | None | List active tests for a centre | `200 OK` | `422 Validation Error` |
| **Tests** | `GET` | `/tests/{test_id}` | None | Get diagnostic test details | `200 OK` | `404 Not Found` |
| **Bookings** | `POST` | `/bookings/` | Bearer | Create a test booking (`PENDING`) | `201 Created` | `400 Bad Request`, `401 Unauthorized`, `404 Not Found` |
| **Bookings** | `GET` | `/bookings/` | Bearer | List current user's bookings | `200 OK` | `401 Unauthorized` |
| **Bookings** | `GET` | `/bookings/{booking_id}` | Bearer | Retrieve booking details (Ownership protected) | `200 OK` | `401 Unauthorized`, `403 Forbidden`, `404 Not Found` |
| **Bookings** | `POST` | `/bookings/{booking_id}/cancel` | Bearer | Cancel a `PENDING` booking (Ownership protected) | `200 OK` | `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found` |
| **Payments** | `POST` | `/payments/` | Bearer | Process simulated payment | `200 OK` | `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found` |
| **Webhooks** | `POST` | `/payments/webhook/` | HMAC Header | Idempotent payment webhook callback | `200 OK` | `400 Bad Request`, `401 Unauthorized`, `404 Not Found` |

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
**`POST /bookings/`** *(Headers: `Authorization: Bearer <JWT_TOKEN>`)*
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

### 3. Simulate Payment
**`POST /payments/`** *(Headers: `Authorization: Bearer <JWT_TOKEN>`)*
```json
{
  "booking_id": "b9f8e7d6-1111-2222-3333-444455556666",
  "simulate_outcome": "SUCCESS",
  "payment_method": "CREDIT_CARD"
}
```
**Response (`200 OK`)**:
```json
{
  "id": "p1a2b3c4-5555-6666-7777-888899990000",
  "booking_id": "b9f8e7d6-1111-2222-3333-444455556666",
  "transaction_id": "tx_mock_a1b2c3d4e5f67890",
  "payment_method": "CREDIT_CARD",
  "amount": "150.00",
  "status": "SUCCESS",
  "booking_status": "CONFIRMED",
  "created_at": "2026-10-01T12:10:00Z"
}
```

### 4. Process Payment Webhook
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

### 5. Duplicate Webhook Handling
If `evt_wh_1001` is sent again:
**Response (`200 OK`)**:
```json
{
  "status": "already_processed",
  "event_id": "evt_wh_1001",
  "message": "Webhook event has already been processed",
  "booking_id": "b9f8e7d6-1111-2222-3333-444455556666",
  "booking_status": "CONFIRMED"
}
```

---

## Booking State Machine

The booking status follows a strict lifecycle:

```
          ┌─────────────┐
          │   PENDING   │
          └──────┬──────┘
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
┌───────────┐ ┌────────┐ ┌───────────┐
│ CONFIRMED │ │ FAILED │ │ CANCELLED │
└───────────┘ └────────┘ └───────────┘
```

1. **`PENDING` -> `CONFIRMED`**: Triggered when a payment or webhook reports `SUCCESS`.
2. **`PENDING` -> `FAILED`**: Triggered when a payment or webhook reports `FAILED`.
3. **`PENDING` -> `CANCELLED`**: Triggered when the user cancels the booking before payment.
4. **Finalized State Protection**: Once a booking reaches `CONFIRMED`, `FAILED`, or `CANCELLED`, subsequent payment or cancellation attempts are rejected with `400 Bad Request`.

---

## Webhook Handling & Idempotency

- **HMAC Signature Security**: The `/payments/webhook/` endpoint requires the `X-Signature` header containing an HMAC-SHA256 digest computed over the raw HTTP request body using `WEBHOOK_SECRET`. Signature comparison uses `hmac.compare_digest` to prevent timing attacks.
- **Idempotency Ledger**: Webhook events are inserted into the `webhook_events` table, which enforces a `UNIQUE` constraint on `event_id`. If a duplicate `event_id` arrives, the system catches the integrity constraint and returns `already_processed` without re-processing payments or altering booking state.
- **Out-of-Order Delivery**: If an out-of-order `FAILED` event arrives after a booking is already `CONFIRMED`, the event is saved to `webhook_events` for auditability, but the booking status remains `CONFIRMED`.

---

## Edge Cases Handled

The implementation and test suite explicitly cover:

- **Invalid User Credentials**: `POST /auth/login` returns `401 Unauthorized` for non-existent users or incorrect passwords.
- **Unauthorized Resource Access**: Attempting to retrieve, cancel, or pay for another user's booking returns `403 Forbidden`.
- **Centre and Test Mismatch**: Booking creation verifies that the specified `test_id` belongs directly to the `centre_id` (`400 Bad Request`).
- **Past Appointment Timestamps**: Bookings scheduled in the past are rejected (`400 Bad Request`).
- **Client Price Tampering**: Client cannot submit arbitrary prices; amounts are read server-side from `DiagnosticTest.price`.
- **Payment on Finalized Bookings**: Processing payments on `CONFIRMED`, `FAILED`, or `CANCELLED` bookings returns `400 Bad Request`.
- **Duplicate Webhooks**: Repeated delivery of identical `event_id` returns `200 OK` with status `already_processed`.
- **Malformed Webhook Payloads**: Signed requests with invalid JSON return `400 Bad Request` without exposing stack traces.
- **Missing / Invalid Webhook Signatures**: Returns `401 Unauthorized`.
- **Concurrent Payments**: Row-level locking (`with_for_update()`) prevents race conditions during simultaneous payment processing.

---

## Local Setup & Configuration

### Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Required variables in `.env`:
```env
APP_NAME="Eve Healthcare Assignment API"
ENV="development"
DEBUG=True

POSTGRES_USER=eve_user
POSTGRES_PASSWORD=eve_password
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=eve_healthcare_db
DATABASE_URL=postgresql+psycopg2://eve_user:eve_password@127.0.0.1:5432/eve_healthcare_db

SECRET_KEY=change_this_to_a_secure_random_key_in_production_32_bytes_min
WEBHOOK_SECRET=change_this_to_a_secure_webhook_secret_in_production_32_bytes_min
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

## Running the Application

### Option A: Docker Compose (Recommended)

Docker Compose builds the FastAPI app container, starts PostgreSQL 15, waits for database readiness, and runs Alembic migrations automatically:

```bash
docker compose up --build
```

Access the API documentation at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

To stop the containers:
```bash
docker compose down
```

### Option B: Local Python Environment (Without Docker)

1. Ensure a local PostgreSQL 15 database is running and create the user/database:
   ```sql
   CREATE USER eve_user WITH PASSWORD 'eve_password';
   CREATE DATABASE eve_healthcare_db OWNER eve_user;
   ```
2. Set up virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. Run Alembic migrations:
   ```bash
   python -m alembic upgrade head
   ```
4. Start the server:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

---

## Running Tests

Run the Pytest suite locally:

```bash
python -m pytest -v
```

### Local Test Output Summary
```text
tests/test_auth.py (8 passed)
tests/test_bookings.py (7 passed)
tests/test_centres.py (5 passed)
tests/test_health.py (2 passed)
tests/test_payments.py (8 passed)
tests/test_tests.py (6 passed)
tests/test_webhooks.py (9 passed)

======================= 45 passed in 23.99s =======================
```

### CI & PostgreSQL Verification
Continuous Integration is configured via GitHub Actions (`.github/workflows/ci.yml`). On every push to `main`, the CI workflow:
1. Starts a PostgreSQL 15 service container.
2. Executes Alembic migrations against live PostgreSQL.
3. Runs the 45 pytest tests against PostgreSQL to verify row-locking behavior.
4. Builds the Docker Compose stack and verifies container health via `/health`.

---

## Assumptions & Limitations

- **Management Authorization**: Currently, creating centres (`POST /centres/`) and tests (`POST /tests/`) requires any valid authenticated user token (`Bearer JWT`). Role-based access control (e.g. `is_admin`) can be added for multi-role environments.
- **Simulated Payment Provider**: The payment endpoint simulates payment outcomes (`SUCCESS` or `FAILED`) without connecting to external banking gateways.
- **Docker Local Availability**: Local execution via Docker Compose requires Docker Desktop installed on the developer machine. Local running without Docker is fully supported using native Python and PostgreSQL.

---

## Future Improvements

1. **Role-Based Access Control (RBAC)**: Restrict diagnostic centre and test management endpoints to administrator roles.
2. **Rate Limiting**: Add rate-limiting middleware (e.g., `slowapi`) to public and auth endpoints to prevent brute-force attacks.
3. **Async Webhook Processing**: Offload payment status webhook actions to background task queues (e.g., Celery / Redis) for high-throughput scaling.

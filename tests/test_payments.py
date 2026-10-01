import uuid
from datetime import datetime, timedelta, timezone
from tests.test_bookings import get_user_headers, setup_centre_and_test


def create_pending_booking(client, headers):
    centre_id, test_id = setup_centre_and_test(client, headers)
    future_date = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    res = client.post(
        "/bookings",
        json={"centre_id": centre_id, "test_id": test_id, "appointment_date": future_date},
        headers=headers,
    )
    return res.json()["id"]


def test_payment_unauthenticated(client):
    payload = {
        "booking_id": str(uuid.uuid4()),
        "payment_method": "CREDIT_CARD",
        "simulate_outcome": "SUCCESS",
    }
    response = client.post("/payments/", json=payload)
    assert response.status_code == 401


def test_payment_success(client):
    headers = get_user_headers(client, "pay.success@example.com")
    booking_id = create_pending_booking(client, headers)

    payment_payload = {
        "booking_id": booking_id,
        "payment_method": "CREDIT_CARD",
        "simulate_outcome": "SUCCESS",
    }
    response = client.post("/payments/", json=payment_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["booking_id"] == booking_id
    assert data["status"] == "SUCCESS"
    assert data["booking_status"] == "CONFIRMED"
    assert float(data["amount"]) == 1200.00

    # Verify booking status updated in DB via GET /bookings/{id}
    res_b = client.get(f"/bookings/{booking_id}", headers=headers)
    assert res_b.status_code == 200
    assert res_b.json()["status"] == "CONFIRMED"


def test_payment_failed(client):
    headers = get_user_headers(client, "pay.failed@example.com")
    booking_id = create_pending_booking(client, headers)

    payment_payload = {
        "booking_id": booking_id,
        "payment_method": "UPI",
        "simulate_outcome": "FAILED",
    }
    response = client.post("/payments/", json=payment_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["booking_id"] == booking_id
    assert data["status"] == "FAILED"
    assert data["booking_status"] == "FAILED"

    # Verify booking status updated in DB
    res_b = client.get(f"/bookings/{booking_id}", headers=headers)
    assert res_b.status_code == 200
    assert res_b.json()["status"] == "FAILED"


def test_payment_another_user_booking_forbidden(client):
    headers_owner = get_user_headers(client, "pay.owner@example.com")
    headers_other = get_user_headers(client, "pay.other@example.com")
    booking_id = create_pending_booking(client, headers_owner)

    payment_payload = {
        "booking_id": booking_id,
        "payment_method": "CREDIT_CARD",
        "simulate_outcome": "SUCCESS",
    }
    response = client.post("/payments/", json=payment_payload, headers=headers_other)
    assert response.status_code == 403
    assert "access denied" in response.json()["detail"].lower()


def test_payment_already_confirmed_booking(client):
    headers = get_user_headers(client, "double.pay@example.com")
    booking_id = create_pending_booking(client, headers)

    # First payment SUCCESS
    client.post(
        "/payments/",
        json={"booking_id": booking_id, "simulate_outcome": "SUCCESS"},
        headers=headers,
    )

    # Second payment attempt -> 400 Bad Request
    res_second = client.post(
        "/payments/",
        json={"booking_id": booking_id, "simulate_outcome": "SUCCESS"},
        headers=headers,
    )
    assert res_second.status_code == 400
    assert "not in pending state" in res_second.json()["detail"].lower()


def test_payment_cancelled_booking(client):
    headers = get_user_headers(client, "pay.cancelled@example.com")
    booking_id = create_pending_booking(client, headers)

    # Cancel booking
    client.post(f"/bookings/{booking_id}/cancel", headers=headers)

    # Attempt payment on CANCELLED booking -> 400 Bad Request
    response = client.post(
        "/payments/",
        json={"booking_id": booking_id, "simulate_outcome": "SUCCESS"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "not in pending state" in response.json()["detail"].lower()


def test_payment_nonexistent_booking(client):
    headers = get_user_headers(client, "pay.fake@example.com")
    fake_booking_id = str(uuid.uuid4())
    response = client.post(
        "/payments/",
        json={"booking_id": fake_booking_id, "simulate_outcome": "SUCCESS"},
        headers=headers,
    )
    assert response.status_code == 404


def test_concurrent_simulated_payments(client):
    import concurrent.futures

    headers = get_user_headers(client, "pay.concurrent@example.com")
    booking_id = create_pending_booking(client, headers)

    payment_payload = {
        "booking_id": booking_id,
        "payment_method": "CREDIT_CARD",
        "simulate_outcome": "SUCCESS",
    }

    def send_payment():
        return client.post("/payments/", json=payment_payload, headers=headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(send_payment)
        f2 = executor.submit(send_payment)
        res1 = f1.result()
        res2 = f2.result()

    status_codes = sorted([res1.status_code, res2.status_code])
    # Exactly one request must succeed (200 OK) and one must be rejected (400 Bad Request)
    assert status_codes == [200, 400]


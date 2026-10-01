import uuid
from datetime import datetime, timedelta, timezone


def get_user_headers(client, email="booking.user@example.com"):
    signup_payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Booking User",
    }
    client.post("/auth/signup", json=signup_payload)
    login_res = client.post("/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def setup_centre_and_test(client, headers):
    # Create Centre
    res_c = client.post("/centres", json={"name": "Health First Lab", "location": "Bangalore"}, headers=headers)
    centre_id = res_c.json()["id"]

    # Create Test
    res_t = client.post(
        f"/centres/{centre_id}/tests",
        json={"name": "Lipid Profile", "price": 1200.00},
        headers=headers,
    )
    test_id = res_t.json()["id"]
    return centre_id, test_id


def test_create_booking_unauthenticated(client):
    payload = {
        "centre_id": str(uuid.uuid4()),
        "test_id": str(uuid.uuid4()),
        "appointment_date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    }
    response = client.post("/bookings", json=payload)
    assert response.status_code == 401


def test_create_booking_success(client):
    headers = get_user_headers(client, "user1@example.com")
    centre_id, test_id = setup_centre_and_test(client, headers)

    future_date = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    booking_payload = {
        "centre_id": centre_id,
        "test_id": test_id,
        "appointment_date": future_date,
    }

    response = client.post("/bookings", json=booking_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["centre_id"] == centre_id
    assert data["test_id"] == test_id
    assert data["status"] == "PENDING"
    assert float(data["amount"]) == 1200.00


def test_create_booking_centre_test_mismatch(client):
    headers = get_user_headers(client, "mismatch.user@example.com")
    centre_id1, test_id1 = setup_centre_and_test(client, headers)

    # Setup Centre 2 with Test 2
    res_c2 = client.post("/centres", json={"name": "Centre Two", "location": "Delhi"}, headers=headers)
    centre_id2 = res_c2.json()["id"]
    res_t2 = client.post(f"/centres/{centre_id2}/tests", json={"name": "Test Two", "price": 500.00}, headers=headers)
    test_id2 = res_t2.json()["id"]

    # Try to book Centre 1 with Test 2 (mismatch!)
    future_date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    bad_payload = {
        "centre_id": centre_id1,
        "test_id": test_id2,  # Belongs to centre 2!
        "appointment_date": future_date,
    }

    response = client.post("/bookings", json=bad_payload, headers=headers)
    assert response.status_code == 400
    assert "does not belong to the selected diagnostic centre" in response.json()["detail"]


def test_create_booking_past_appointment(client):
    headers = get_user_headers(client, "past.date@example.com")
    centre_id, test_id = setup_centre_and_test(client, headers)

    past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    bad_payload = {
        "centre_id": centre_id,
        "test_id": test_id,
        "appointment_date": past_date,
    }

    response = client.post("/bookings", json=bad_payload, headers=headers)
    assert response.status_code == 422
    assert "must be scheduled in the future" in str(response.json()["detail"]).lower()


def test_get_user_bookings_list(client):
    headers = get_user_headers(client, "list.user@example.com")
    centre_id, test_id = setup_centre_and_test(client, headers)
    future_date = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    client.post("/bookings", json={"centre_id": centre_id, "test_id": test_id, "appointment_date": future_date}, headers=headers)

    response = client.get("/bookings", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "PENDING"


def test_get_booking_by_id_and_ownership(client):
    headers_owner = get_user_headers(client, "owner@example.com")
    headers_other = get_user_headers(client, "other@example.com")

    centre_id, test_id = setup_centre_and_test(client, headers_owner)
    future_date = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

    res = client.post("/bookings", json={"centre_id": centre_id, "test_id": test_id, "appointment_date": future_date}, headers=headers_owner)
    booking_id = res.json()["id"]

    # Owner gets details -> Success
    res_owner = client.get(f"/bookings/{booking_id}", headers=headers_owner)
    assert res_owner.status_code == 200
    assert res_owner.json()["id"] == booking_id

    # Other user attempts access -> Forbidden (403)
    res_other = client.get(f"/bookings/{booking_id}", headers=headers_other)
    assert res_other.status_code == 403
    assert "access denied" in res_other.json()["detail"].lower()


def test_cancel_booking_success_and_protection(client):
    headers_owner = get_user_headers(client, "cancel.owner@example.com")
    headers_other = get_user_headers(client, "cancel.other@example.com")

    centre_id, test_id = setup_centre_and_test(client, headers_owner)
    future_date = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()

    res = client.post("/bookings", json={"centre_id": centre_id, "test_id": test_id, "appointment_date": future_date}, headers=headers_owner)
    booking_id = res.json()["id"]

    # Other user attempts cancel -> 403
    res_other_cancel = client.post(f"/bookings/{booking_id}/cancel", headers=headers_other)
    assert res_other_cancel.status_code == 403

    # Owner cancels -> 200 OK, status = CANCELLED
    res_cancel = client.post(f"/bookings/{booking_id}/cancel", headers=headers_owner)
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"

    # Attempt second cancellation -> 400 Bad Request
    res_repeat = client.post(f"/bookings/{booking_id}/cancel", headers=headers_owner)
    assert res_repeat.status_code == 400

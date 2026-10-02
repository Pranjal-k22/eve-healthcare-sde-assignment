import uuid
import hmac
import hashlib
import json
from datetime import datetime, timedelta, timezone
from app.core.config import settings
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


def post_signed_webhook(client, payload_dict, signature_override=None, include_signature=True):
    raw_bytes = json.dumps(payload_dict).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if include_signature:
        if signature_override is not None:
            headers["X-Signature"] = signature_override
        else:
            headers["X-Signature"] = hmac.new(settings.WEBHOOK_SECRET.encode(), raw_bytes, hashlib.sha256).hexdigest()
    return client.post("/payments/webhook/", content=raw_bytes, headers=headers)


def test_webhook_missing_signature(client):
    headers = get_user_headers(client, "webhook.nosig@example.com")
    booking_id = create_pending_booking(client, headers)

    webhook_payload = {
        "event_id": "evt_nosig_001",
        "provider_payment_id": "pay_nosig",
        "booking_id": booking_id,
        "status": "SUCCESS",
    }

    # Request without X-Signature header -> 401 Unauthorized
    response = post_signed_webhook(client, webhook_payload, include_signature=False)
    assert response.status_code == 401
    assert "missing" in response.json()["detail"].lower()


def test_webhook_invalid_signature(client):
    headers = get_user_headers(client, "webhook.badsig@example.com")
    booking_id = create_pending_booking(client, headers)

    webhook_payload = {
        "event_id": "evt_badsig_001",
        "provider_payment_id": "pay_badsig",
        "booking_id": booking_id,
        "status": "SUCCESS",
    }

    # Request with wrong X-Signature header -> 401 Unauthorized
    response = post_signed_webhook(client, webhook_payload, signature_override="invalid_hmac_hash_value")
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_webhook_success_first_delivery(client):
    headers = get_user_headers(client, "webhook.user1@example.com")
    booking_id = create_pending_booking(client, headers)

    webhook_payload = {
        "event_id": "evt_test_success_001",
        "provider_payment_id": "pay_prov_001",
        "booking_id": booking_id,
        "status": "SUCCESS",
    }

    response = post_signed_webhook(client, webhook_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["event_id"] == "evt_test_success_001"
    assert data["booking_status"] == "CONFIRMED"

    # Verify booking status updated in DB
    res_b = client.get(f"/bookings/{booking_id}", headers=headers)
    assert res_b.status_code == 200
    assert res_b.json()["status"] == "CONFIRMED"


def test_webhook_failed_first_delivery(client):
    headers = get_user_headers(client, "webhook.user2@example.com")
    booking_id = create_pending_booking(client, headers)

    webhook_payload = {
        "event_id": "evt_test_failed_001",
        "provider_payment_id": "pay_prov_002",
        "booking_id": booking_id,
        "status": "FAILED",
    }

    response = post_signed_webhook(client, webhook_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["booking_status"] == "FAILED"

    # Verify booking status in DB
    res_b = client.get(f"/bookings/{booking_id}", headers=headers)
    assert res_b.status_code == 200
    assert res_b.json()["status"] == "FAILED"


def test_webhook_idempotency_duplicate_delivery(client):
    headers = get_user_headers(client, "webhook.idempotent@example.com")
    booking_id = create_pending_booking(client, headers)

    webhook_payload = {
        "event_id": "evt_duplicate_999",
        "provider_payment_id": "pay_dup_999",
        "booking_id": booking_id,
        "status": "SUCCESS",
    }

    # First delivery -> processed
    res1 = post_signed_webhook(client, webhook_payload)
    assert res1.status_code == 200
    assert res1.json()["status"] == "processed"

    # Second delivery -> already_processed
    res2 = post_signed_webhook(client, webhook_payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "already_processed"
    assert res2.json()["event_id"] == "evt_duplicate_999"

    # Third delivery -> already_processed
    res3 = post_signed_webhook(client, webhook_payload)
    assert res3.status_code == 200
    assert res3.json()["status"] == "already_processed"

    # Verify booking status remains CONFIRMED
    res_b = client.get(f"/bookings/{booking_id}", headers=headers)
    assert res_b.status_code == 200
    assert res_b.json()["status"] == "CONFIRMED"


def test_webhook_unknown_booking(client):
    fake_booking_id = str(uuid.uuid4())
    webhook_payload = {
        "event_id": "evt_unknown_booking_001",
        "provider_payment_id": "pay_fake_001",
        "booking_id": fake_booking_id,
        "status": "SUCCESS",
    }

    response = post_signed_webhook(client, webhook_payload)
    assert response.status_code == 404


def test_webhook_conflicting_replay(client):
    headers = get_user_headers(client, "webhook.replay@example.com")
    booking_id = create_pending_booking(client, headers)

    # First event says SUCCESS
    res1 = post_signed_webhook(
        client,
        {
            "event_id": "evt_conflict_777",
            "provider_payment_id": "pay_conflict_777",
            "booking_id": booking_id,
            "status": "SUCCESS",
        },
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "processed"

    # Conflicting replay for SAME event_id says FAILED -> Should return already_processed without state mutation!
    res2 = post_signed_webhook(
        client,
        {
            "event_id": "evt_conflict_777",
            "provider_payment_id": "pay_conflict_777",
            "booking_id": booking_id,
            "status": "FAILED",
        },
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "already_processed"

    # Booking remains CONFIRMED
    res_b = client.get(f"/bookings/{booking_id}", headers=headers)
    assert res_b.status_code == 200
    assert res_b.json()["status"] == "CONFIRMED"


def test_webhook_same_payment_different_event(client):
    headers = get_user_headers(client, "webhook.samepay@example.com")
    booking_id = create_pending_booking(client, headers)

    # Event 1 for Payment X
    res1 = post_signed_webhook(
        client,
        {
            "event_id": "evt_first_111",
            "provider_payment_id": "pay_shared_888",
            "booking_id": booking_id,
            "status": "SUCCESS",
        },
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "processed"

    # Event 2 for SAME Payment X
    res2 = post_signed_webhook(
        client,
        {
            "event_id": "evt_second_222",
            "provider_payment_id": "pay_shared_888",
            "booking_id": booking_id,
            "status": "SUCCESS",
        },
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "processed"

    # Booking remains CONFIRMED
    res_b = client.get(f"/bookings/{booking_id}", headers=headers)
    assert res_b.status_code == 200
    assert res_b.json()["status"] == "CONFIRMED"


def test_webhook_malformed_json_valid_signature(client):
    malformed_bytes = b'{"event_id": "evt_malformed", "provider_payment_id": "pay_123", "booking_id":'
    signature = hmac.new(settings.WEBHOOK_SECRET.encode(), malformed_bytes, hashlib.sha256).hexdigest()
    headers = {"Content-Type": "application/json", "X-Signature": signature}

    response = client.post("/payments/webhook/", content=malformed_bytes, headers=headers)
    assert response.status_code == 400
    assert "detail" in response.json()
    assert "payload format" in response.json()["detail"].lower()


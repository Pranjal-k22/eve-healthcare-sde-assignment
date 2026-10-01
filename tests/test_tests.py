import uuid
from tests.test_centres import get_auth_headers


def test_create_test_unauthorized(client):
    headers = get_auth_headers(client)
    res = client.post("/centres", json={"name": "Centre X", "location": "Delhi"}, headers=headers)
    centre_id = res.json()["id"]

    test_payload = {"name": "Blood Group Test", "price": 500.00}
    response = client.post(f"/centres/{centre_id}/tests", json=test_payload)
    assert response.status_code == 401


def test_create_test_success(client):
    headers = get_auth_headers(client)
    res = client.post("/centres", json={"name": "Centre X", "location": "Delhi"}, headers=headers)
    centre_id = res.json()["id"]

    test_payload = {
        "name": "Complete Blood Count (CBC)",
        "description": "Measures white and red blood cells",
        "price": 450.00,
    }
    response = client.post(f"/centres/{centre_id}/tests", json=test_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["centre_id"] == centre_id
    assert data["name"] == "Complete Blood Count (CBC)"
    assert float(data["price"]) == 450.00
    assert data["is_active"] is True


def test_create_test_invalid_price(client):
    headers = get_auth_headers(client)
    res = client.post("/centres", json={"name": "Centre Y", "location": "Pune"}, headers=headers)
    centre_id = res.json()["id"]

    # Zero price
    res1 = client.post(f"/centres/{centre_id}/tests", json={"name": "Test A", "price": 0.00}, headers=headers)
    assert res1.status_code == 422

    # Negative price
    res2 = client.post(f"/centres/{centre_id}/tests", json={"name": "Test B", "price": -100.00}, headers=headers)
    assert res2.status_code == 422


def test_get_tests_by_centre(client):
    headers = get_auth_headers(client)
    res = client.post("/centres", json={"name": "Centre Z", "location": "Chennai"}, headers=headers)
    centre_id = res.json()["id"]

    client.post(f"/centres/{centre_id}/tests", json={"name": "Test 1", "price": 200.00}, headers=headers)
    client.post(f"/centres/{centre_id}/tests", json={"name": "Test 2", "price": 300.00}, headers=headers)

    response = client.get(f"/centres/{centre_id}/tests")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_test_by_id_success(client):
    headers = get_auth_headers(client)
    res_c = client.post("/centres", json={"name": "Centre W", "location": "Hyderabad"}, headers=headers)
    centre_id = res_c.json()["id"]

    res_t = client.post(f"/centres/{centre_id}/tests", json={"name": "Thyroid Profile", "price": 800.00}, headers=headers)
    test_id = res_t.json()["id"]

    response = client.get(f"/tests/{test_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Thyroid Profile"


def test_get_test_by_id_not_found(client):
    fake_id = str(uuid.uuid4())
    response = client.get(f"/tests/{fake_id}")
    assert response.status_code == 404

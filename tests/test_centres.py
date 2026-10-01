import uuid


def get_auth_headers(client):
    signup_payload = {
        "email": "admin.centre@example.com",
        "password": "Password123!",
        "full_name": "Admin User",
    }
    client.post("/auth/signup", json=signup_payload)
    login_res = client.post("/auth/login", json={"email": "admin.centre@example.com", "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_centre_unauthorized(client):
    payload = {
        "name": "Apollo Diagnostic Centre",
        "location": "Bangalore",
        "contact_email": "apollo@example.com",
    }
    response = client.post("/centres", json=payload)
    assert response.status_code == 401


def test_create_centre_success(client):
    headers = get_auth_headers(client)
    payload = {
        "name": "Apollo Diagnostic Centre",
        "location": "Bangalore",
        "contact_email": "apollo@example.com",
        "contact_phone": "+919876543210",
    }
    response = client.post("/centres", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Apollo Diagnostic Centre"
    assert data["location"] == "Bangalore"
    assert data["contact_email"] == "apollo@example.com"
    assert data["is_active"] is True
    assert data["tests"] == []


def test_get_centres_list(client):
    headers = get_auth_headers(client)
    client.post("/centres", json={"name": "Centre A", "location": "City A"}, headers=headers)
    client.post("/centres", json={"name": "Centre B", "location": "City B"}, headers=headers)

    response = client.get("/centres")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


def test_get_centre_by_id_success(client):
    headers = get_auth_headers(client)
    res = client.post("/centres", json={"name": "Metropolis Healthcare", "location": "Mumbai"}, headers=headers)
    centre_id = res.json()["id"]

    response = client.get(f"/centres/{centre_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Metropolis Healthcare"


def test_get_centre_by_id_not_found(client):
    fake_id = str(uuid.uuid4())
    response = client.get(f"/centres/{fake_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

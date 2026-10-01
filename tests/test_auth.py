from datetime import timedelta
import uuid
from app.core.security import create_access_token


def test_signup_success(client):
    payload = {
        "email": "jane.doe@example.com",
        "password": "SecurePassword123!",
        "full_name": "Jane Doe",
    }
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == "jane.doe@example.com"
    assert data["full_name"] == "Jane Doe"
    assert data["is_active"] is True
    # Ensure sensitive fields are NEVER returned
    assert "hashed_password" not in data
    assert "password" not in data


def test_signup_duplicate_email(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "full_name": "First User",
    }
    res1 = client.post("/auth/signup", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/auth/signup", json=payload)
    assert res2.status_code == 400
    assert res2.json()["detail"] == "Email already registered"


def test_signup_invalid_input(client):
    # Invalid email
    res1 = client.post(
        "/auth/signup",
        json={"email": "invalid-email", "password": "Password123!", "full_name": "User"},
    )
    assert res1.status_code == 422

    # Short password
    res2 = client.post(
        "/auth/signup",
        json={"email": "user@example.com", "password": "123", "full_name": "User"},
    )
    assert res2.status_code == 422


def test_login_success(client):
    signup_payload = {
        "email": "login.user@example.com",
        "password": "Password123!",
        "full_name": "Login User",
    }
    client.post("/auth/signup", json=signup_payload)

    login_payload = {
        "email": "login.user@example.com",
        "password": "Password123!",
    }
    response = client.post("/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_invalid_credentials(client):
    # Signup user
    signup_payload = {
        "email": "user.wrong@example.com",
        "password": "CorrectPassword123!",
        "full_name": "User Wrong",
    }
    client.post("/auth/signup", json=signup_payload)

    # Wrong password
    res1 = client.post(
        "/auth/login",
        json={"email": "user.wrong@example.com", "password": "WrongPassword123!"},
    )
    assert res1.status_code == 401
    assert res1.json()["detail"] == "Invalid email or password"

    # Non-existent email
    res2 = client.post(
        "/auth/login",
        json={"email": "nonexistent@example.com", "password": "Password123!"},
    )
    assert res2.status_code == 401
    assert res2.json()["detail"] == "Invalid email or password"


def test_get_me_success(client):
    signup_payload = {
        "email": "me.user@example.com",
        "password": "Password123!",
        "full_name": "Me User",
    }
    signup_res = client.post("/auth/signup", json=signup_payload)
    user_id = signup_res.json()["id"]

    login_res = client.post("/auth/login", json={"email": "me.user@example.com", "password": "Password123!"})
    token = login_res.json()["access_token"]

    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["id"] == user_id
    assert me_data["email"] == "me.user@example.com"


def test_get_me_unauthorized(client):
    # No token
    res1 = client.get("/auth/me")
    assert res1.status_code == 401

    # Invalid token
    res2 = client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken123"})
    assert res2.status_code == 401

    # Expired token
    expired_token = create_access_token(
        data={"sub": str(uuid.uuid4())},
        expires_delta=timedelta(seconds=-10),
    )
    res3 = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res3.status_code == 401
    assert res3.json()["detail"] == "Token has expired"


def test_get_me_nonexistent_user_token(client):
    fake_user_id = str(uuid.uuid4())
    token = create_access_token(data={"sub": fake_user_id})
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert res.json()["detail"] == "User not found or inactive"

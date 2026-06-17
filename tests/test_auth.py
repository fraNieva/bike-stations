"""
Tests for the authentication endpoints.

Covers: login with valid credentials, login with wrong password,
login with unknown email, and access to protected endpoints
with and without a valid JWT.
"""

import pytest


@pytest.mark.asyncio
async def test_login_success(client, test_user):
    """Valid credentials return a JWT access token."""
    response = await client.post("/auth/login", json={
        "email": "mariano@bicing.com",
        "password": "securepassword123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user):
    """Wrong password returns 401 Unauthorized."""
    response = await client.post("/auth/login", json={
        "email": "mariano@bicing.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client):
    """Unknown email returns 401 Unauthorized."""
    response = await client.post("/auth/login", json={
        "email": "unknown@bicing.com",
        "password": "anypassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client):
    """Calling a protected endpoint without JWT returns 401."""
    response = await client.get("/stations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_invalid_token(client):
    """Calling a protected endpoint with a fake token returns 401."""
    response = await client.get(
        "/stations",
        headers={"Authorization": "Bearer fake.token.here"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(client, auth_headers):
    """Valid JWT grants access to protected endpoints."""
    response = await client.get("/stations", headers=auth_headers)
    assert response.status_code == 200
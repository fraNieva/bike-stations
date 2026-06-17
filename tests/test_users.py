"""
Tests for user management endpoints.

Covers: creating users, listing users, activating and deactivating users,
and duplicate email validation.
"""

import pytest


@pytest.mark.asyncio
async def test_create_user(client, auth_headers):
    """POST /admin/users creates a new user and returns it without the password."""
    response = await client.post("/admin/users", json={
        "email": "operator@bicing.com",
        "password": "strongpassword456",
    }, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "operator@bicing.com"
    assert data["is_active"] is True
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_create_duplicate_user(client, auth_headers, test_user):
    """Creating a user with an existing email returns 409 Conflict."""
    response = await client.post("/admin/users", json={
        "email": "mariano@bicing.com",
        "password": "anotherpassword",
    }, headers=auth_headers)

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_users(client, auth_headers, test_user):
    """GET /admin/users returns all users."""
    response = await client.get("/admin/users", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert any(u["email"] == "mariano@bicing.com" for u in data)


@pytest.mark.asyncio
async def test_deactivate_user(client, auth_headers, test_user):
    """PATCH /admin/users/{id} with is_active=false deactivates the user."""
    response = await client.patch(
        f"/admin/users/{test_user.id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_deactivated_user_cannot_login(client, test_user, db):
    """A deactivated user cannot obtain a JWT token."""
    test_user.is_active = False
    db.commit()

    response = await client.post("/auth/login", json={
        "email": "mariano@bicing.com",
        "password": "securepassword123",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_user_endpoints_require_authentication(client):
    """User admin endpoints return 401 without a valid JWT."""
    response = await client.get("/admin/users")
    assert response.status_code == 401
import pytest
from httpx import ASGITransport, AsyncClient
from passlib.hash import bcrypt

from backend.api.main import app
from backend.core.database import get_db
from backend.models.user import User

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_client(client, db_session):
    rounds = 12
    user = User(
        email="auth@test.com",
        username="authuser",
        hashed_password=bcrypt.using(rounds=rounds).hash("testpass"),
        role="admin",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "authuser", "password": "testpass"},
    )
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


class TestHealth:
    async def test_root(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["version"] == "1.0.0"

    async def test_health(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")


class TestAuthRoutes:
    async def test_me_unauthenticated(self, client):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestLeakRoutes:
    async def test_delete_leak_requires_admin(self, client, db_session):
        from backend.models.leak import Leak
        leak = Leak(title="DeleteMe", severity="low")
        db_session.add(leak)
        await db_session.commit()
        response = await client.delete(f"/api/v1/leaks/{leak.id}")
        assert response.status_code == 401


class TestAlertRoutes:
    async def test_list_alerts_requires_auth(self, client):
        response = await client.get("/api/v1/alerts")
        assert response.status_code == 401


class TestRoutesAccess:
    async def test_delete_actor_requires_admin(self, client, db_session):
        from backend.models.threat_actor import ThreatActor
        actor = ThreatActor(name="DeleteMe")
        db_session.add(actor)
        await db_session.commit()
        response = await client.delete(f"/api/v1/threat-actors/{actor.id}")
        assert response.status_code == 401

    async def test_delete_leak_requires_admin(self, client, db_session):
        from backend.models.leak import Leak
        leak = Leak(title="DeleteMe", severity="low")
        db_session.add(leak)
        await db_session.commit()
        response = await client.delete(f"/api/v1/leaks/{leak.id}")
        assert response.status_code == 401

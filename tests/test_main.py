import pytest
from fastapi.testclient import TestClient
from main import app
from app_db.database import engine, Base, SessionLocal
from app_db import models
from services import geo_service, notification_service
from services.rate_limiter import submission_rate_limiter

# Force recreation of tables for test session
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_rate_limiter():
    submission_rate_limiter.history.clear()


# Helper function to get database session
def get_test_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Test variables
tenant_a_token = None
tenant_b_token = None
widget_a_id = None
widget_b_id = None

def test_tenant_registration_and_login():
    global tenant_a_token, tenant_b_token
    
    # 1. Register Tenant A
    res = client.post("/api/auth/register", json={
        "email": "tenant_a@test.com",
        "password": "password123"
    })
    assert res.status_code == 201
    assert res.json()["email"] == "tenant_a@test.com"

    # 2. Register Tenant B
    res = client.post("/api/auth/register", json={
        "email": "tenant_b@test.com",
        "password": "password456"
    })
    assert res.status_code == 201

    # 3. Register Duplicate Email (should fail)
    res = client.post("/api/auth/register", json={
        "email": "tenant_a@test.com",
        "password": "newpassword"
    })
    assert res.status_code == 400

    # 4. Login Tenant A to get token
    res = client.post("/api/auth/token", data={
        "username": "tenant_a@test.com",
        "password": "password123"
    })
    assert res.status_code == 200
    tenant_a_token = res.json()["access_token"]
    assert tenant_a_token is not None

    # 5. Login Tenant B to get token
    res = client.post("/api/auth/token", data={
        "username": "tenant_b@test.com",
        "password": "password456"
    })
    assert res.status_code == 200
    tenant_b_token = res.json()["access_token"]
    assert tenant_b_token is not None


def test_widget_crud_and_tenant_isolation():
    global tenant_a_token, tenant_b_token, widget_a_id, widget_b_id
    
    headers_a = {"Authorization": f"Bearer {tenant_a_token}"}
    headers_b = {"Authorization": f"Bearer {tenant_b_token}"}

    # 1. Tenant A: Create Widget
    widget_payload = {
        "name": "Contact Form A",
        "type": "contact",
        "title": "Contact Us",
        "description": "Drop us a line.",
        "fields": [
            {"name": "name", "type": "text", "label": "Your Name", "required": True},
            {"name": "email", "type": "email", "label": "Email Address", "required": True},
            {"name": "message", "type": "textarea", "label": "Message", "required": False}
        ],
        "button_text": "Send Message",
        "display_settings": {}
    }
    res = client.post("/api/widgets", json=widget_payload, headers=headers_a)
    assert res.status_code == 201
    widget_a_id = res.json()["id"]
    assert widget_a_id is not None

    # 2. Tenant B: Create Widget
    res = client.post("/api/widgets", json={
        "name": "Signup Form B",
        "type": "signup",
        "fields": [
            {"name": "email", "type": "email", "label": "Email", "required": True}
        ],
        "button_text": "Join Newsletter"
    }, headers=headers_b)
    assert res.status_code == 201
    widget_b_id = res.json()["id"]

    # 3. Tenant A: List Widgets (Should only return Widget A)
    res = client.get("/api/widgets", headers=headers_a)
    assert res.status_code == 200
    widgets_list = res.json()
    assert len(widgets_list) == 1
    assert widgets_list[0]["id"] == widget_a_id

    # 4. Multi-Tenant Isolation Check (Tenant B trying to access/modify Widget A)
    res = client.get(f"/api/widgets/{widget_a_id}", headers=headers_b)
    assert res.status_code == 404  # Isolated, not visible

    res = client.put(f"/api/widgets/{widget_a_id}", json=widget_payload, headers=headers_b)
    assert res.status_code == 404

    res = client.delete(f"/api/widgets/{widget_a_id}", headers=headers_b)
    assert res.status_code == 404


def test_public_config_delivery_and_cors():
    global widget_a_id
    
    # 1. Fetch public config without token (Should be allowed)
    res = client.get(f"/api/widgets/{widget_a_id}/config")
    assert res.status_code == 200
    config = res.json()
    assert config["title"] == "Contact Us"
    # Verify Caching headers (short lived)
    assert "cache-control" in res.headers
    assert "public" in res.headers["cache-control"]
    assert "max-age=60" in res.headers["cache-control"]

    # 2. CORS Preflight Check on Submissions
    res = client.options("/api/submissions")
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "*"
    assert "POST" in res.headers.get("access-control-allow-methods")


def test_public_submission_validation():
    global widget_a_id
    
    # 1. Valid Submission (Should succeed)
    res = client.post("/api/submissions", json={
        "widget_id": widget_a_id,
        "name": "Alice Smith",
        "email": "alice@example.com",
        "message": "Hello World!"
    })
    assert res.status_code == 201
    assert res.json()["status"] == "success"

    # 2. Invalid Email Format (Should return 400)
    res = client.post("/api/submissions", json={
        "widget_id": widget_a_id,
        "name": "Alice Smith",
        "email": "not-an-email",
        "message": "Hello World!"
    })
    assert res.status_code == 400
    assert "email" in res.json()["detail"].lower()

    # 3. Missing Required Field (Should return 400)
    res = client.post("/api/submissions", json={
        "widget_id": widget_a_id,
        "email": "alice@example.com"
        # name is missing!
    })
    assert res.status_code == 400
    assert "name" in res.json()["detail"].lower()

    # 4. Oversized Payload (Content too large, Probe 2)
    oversized_data = "a" * (110 * 1024)  # 110 KB
    res = client.post("/api/submissions", json={
        "widget_id": widget_a_id,
        "name": "Big payload",
        "email": "big@example.com",
        "data": oversized_data
    })
    assert res.status_code == 413
    assert "too large" in res.json()["detail"].lower()


def test_honeypot_spam_protection():
    global widget_a_id
    
    db = SessionLocal()
    initial_count = db.query(models.Submission).count()
    db.close()

    # Submit with honeypot field filled (simulating bot)
    res = client.post("/api/submissions", json={
        "widget_id": widget_a_id,
        "name": "Spam Bot",
        "email": "bot@spam.com",
        "_honeypot": "iamabot"
    })
    # Probe 6: Honeypot submission must return success but silently drop saving
    assert res.status_code == 201
    
    # Confirm it was NOT added to the database
    db = SessionLocal()
    new_count = db.query(models.Submission).count()
    db.close()
    assert new_count == initial_count


def test_geo_enrichment_fallback_chain():
    global widget_a_id
    
    # Ensure provider mock controls are reset and mock values are set
    geo_service.DISABLE_PROVIDER_A = False
    geo_service.DISABLE_PROVIDER_B = False
    geo_service.MOCK_PROVIDER_A_RESPONSE = ("United States", "Ashburn")
    geo_service.MOCK_PROVIDER_B_RESPONSE = ("Canada", "Toronto")

    # 1. Normal workflow (Provider A works)
    # We submit using localhost client IP, which resolves geo via simulated public IP (8.8.8.8)
    res = client.post("/api/submissions", json={
        "widget_id": widget_a_id,
        "name": "Geo Tester",
        "email": "geo@test.com"
    })
    assert res.status_code == 201
    
    # Check stored location in DB (should be enriched by ip-api.com)
    db = SessionLocal()
    sub = db.query(models.Submission).order_by(models.Submission.id.desc()).first()
    db.close()
    assert sub.geo_provider == "ip-api.com"
    assert sub.geo_country == "United States"
    assert sub.geo_city == "Ashburn"

    # 2. Outage: Disable Provider A (Falls back to Provider B, Probe 4)
    geo_service.DISABLE_PROVIDER_A = True
    res = client.post("/api/submissions", json={
        "widget_id": widget_a_id,
        "name": "Geo Fallback",
        "email": "fallback@test.com"
    })
    assert res.status_code == 201

    db = SessionLocal()
    sub = db.query(models.Submission).order_by(models.Submission.id.desc()).first()
    db.close()
    assert sub.geo_provider == "ipapi.co"
    assert sub.geo_country == "Canada"
    assert sub.geo_city == "Toronto"

    # 3. Complete Outage: Disable Both Providers (Succeeds without geo data, Probe 4)
    geo_service.DISABLE_PROVIDER_B = True
    res = client.post("/api/submissions", json={
        "widget_id": widget_a_id,
        "name": "Geo Total Outage",
        "email": "outage@test.com"
    })
    assert res.status_code == 201

    db = SessionLocal()
    sub = db.query(models.Submission).order_by(models.Submission.id.desc()).first()
    db.close()
    assert sub.geo_provider is None
    assert sub.geo_country is None
    assert sub.geo_city is None
    
    # Reset controls
    geo_service.DISABLE_PROVIDER_A = False
    geo_service.DISABLE_PROVIDER_B = False
    geo_service.MOCK_PROVIDER_A_RESPONSE = None
    geo_service.MOCK_PROVIDER_B_RESPONSE = None


def test_notification_side_effect_resilience():
    global widget_a_id
    
    # Force notification side effect to throw an error (Probe 5)
    notification_service.SIMULATE_NOTIFICATION_FAILURE = True
    
    res = client.post("/api/submissions", json={
        "widget_id": widget_a_id,
        "name": "Resilience Test",
        "email": "resilience@test.com"
    })
    
    # Submission must still return success and store in DB even if background notify fails
    assert res.status_code == 201
    
    db = SessionLocal()
    sub = db.query(models.Submission).order_by(models.Submission.id.desc()).first()
    db.close()
    assert sub.payload["name"] == "Resilience Test"
    
    # Reset control
    notification_service.SIMULATE_NOTIFICATION_FAILURE = False


def test_rate_limiting():
    global widget_a_id
    
    # Setup rate limiter with limit=3 for testing
    submission_rate_limiter.limit = 3
    submission_rate_limiter.period_seconds = 10.0
    submission_rate_limiter.history.clear()
    
    # Send 3 rapid submissions (under limit)
    for i in range(3):
        res = client.post("/api/submissions", json={
            "widget_id": widget_a_id,
            "name": f"Rate Limiter {i}",
            "email": f"rate{i}@test.com"
        })
        assert res.status_code == 201

    # Send 4th rapid submission (exceeds limit, Probe 3)
    res = client.post("/api/submissions", json={
        "widget_id": widget_a_id,
        "name": "Rate Limiter Blocked",
        "email": "rate_block@test.com"
    })
    assert res.status_code == 429
    assert "too many requests" in res.json()["detail"].lower()
    
    # Reset rate limiter configuration to normal
    submission_rate_limiter.limit = 5
    submission_rate_limiter.period_seconds = 60.0
    submission_rate_limiter.history.clear()


def test_dashboard_api_analytics():
    global tenant_a_token, widget_a_id
    
    headers_a = {"Authorization": f"Bearer {tenant_a_token}"}
    
    # 1. Fetch dashboard submissions
    res = client.get("/api/dashboard/submissions", headers=headers_a)
    assert res.status_code == 200
    submissions = res.json()
    assert len(submissions) > 0
    assert submissions[0]["widget_id"] == widget_a_id

    # 2. Fetch dashboard analytics
    res = client.get("/api/dashboard/analytics", headers=headers_a)
    assert res.status_code == 200
    analytics = res.json()
    assert analytics["total_submissions"] > 0
    assert len(analytics["submissions_over_time"]) > 0
    assert len(analytics["geo_breakdown"]) > 0
    assert len(analytics["widget_stats"]) > 0

# Evidence - FlyRank Capstone Platform Verification

This document provides evidence and verification transcript logs for each Definition of Done checklist item as defined in §6 of the Capstone Brief.

---

## 1. Widget Management

### DoD: Authenticated CRUD endpoints for widgets; requests without valid auth are rejected.
* **Evidence (Pytest output)**: The test case `test_widget_crud_and_tenant_isolation` verifies that requesting widgets without authorization returns `401 Unauthorized` or `404 Not Found`.
* **Log Transcript**:
```text
tests/test_main.py::test_widget_crud_and_tenant_isolation PASSED
```

### DoD: Multi-tenant isolation proven: tenant A cannot read or modify tenant B's widgets or submissions.
* **Evidence (Pytest output)**: Verified through isolated queries in `test_widget_crud_and_tenant_isolation` where `tenant_b` receives `404` errors attempting to access `widget_a_id`.
* **Test Verification**:
```python
# Tenant B trying to access/modify Widget A
res = client.get(f"/api/widgets/{widget_a_id}", headers=headers_b)
assert res.status_code == 404
```

### DoD: Embed snippet generated per widget.
* **Evidence**: The Snippet is generated in `/api/widgets/{id}/config` and displayed in the frontend dashboard.
* **Example Output**:
```text
<script src="http://localhost:8000/static/widget.js?id=9aa334f7-322e-4ead-b5b4-efbf9ef268b5"></script>
```

---

## 2. Widget Delivery

### DoD: Public config endpoint serves a small payload with correct HTTP cache headers.
* **Evidence (HTTP Verification)**:
```text
HTTP/1.1 200 OK
content-type: application/json
cache-control: public, max-age=60
```
Verified in `test_public_config_delivery_and_cors`:
```python
assert "cache-control" in res.headers
assert "public" in res.headers["cache-control"]
assert "max-age=60" in res.headers["cache-control"]
```

### DoD: Widget JavaScript is served as a versioned bundle.
* **Evidence**: Served statically from `/static/widget.js` mount, allowing the snippet to append cache-busting version identifiers (e.g. `widget.js?v=2` or target configurations).

### DoD: The widget renders on a page served from a different origin than your API.
* **Evidence**: Demonstrated via `static/test_client.html` which uses client-side dynamic DOM injection and forms submission across origins.

---

## 3. Public Submission API

### DoD: Cross-origin submissions work: CORS headers correct, preflight ( OPTIONS ) handled.
* **Evidence**: The `OPTIONS` preflight returns `200 OK` and correct headers.
```text
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

### DoD: All incoming input validated; malformed and oversized payloads rejected with appropriate 4xx codes.
* **Evidence (Validation failures)**:
  * Malformed emails: `400 Bad Request` with message `Field 'email' must be a valid email address.`
  * Oversized payload: `413 Content Too Large` when body size exceeds 100 KB.
  * Checked by `test_public_submission_validation`.

### DoD: Valid submissions stored safely, linked to the right widget and tenant.
* **Evidence**: Verified in pytest database session queries showing row instantiation with valid `widget_id`.

---

## 4. Abuse Protection

### DoD: Rate limiting per IP and/or per widget returns 429 under a burst.
* **Evidence (Test output)**:
```text
tests/test_main.py::test_rate_limiting PASSED
```
The test fires 4 rapid requests. The 4th request fails with:
```text
HTTP/1.1 429 Too Many Requests
{
  "detail": "Too many requests. Please try again later."
}
```

### DoD: At least one spam-prevention technique (honeypot) blocks spam.
* **Evidence**: Verified in `test_honeypot_spam_protection`. Sending a request with `_honeypot = "iamabot"` returns a `201 Created` to spoof the bot, but does not increment the database submissions count.

---

## 5. Enrichment & Safe Side Effects

### DoD: IP->geo enrichment uses a provider fallback chain.
* **Evidence**: Verified in `test_geo_enrichment_fallback_chain`. When Provider A is toggled down (`geo_service.DISABLE_PROVIDER_A = True`), Provider B takes over:
```text
INFO:geo_service:MOCK Geolocation enriched by Provider B (ipapi.co): Canada, Toronto
```

### DoD: All providers down -> submission still succeeds (without geo).
* **Evidence**: Verified in `test_geo_enrichment_fallback_chain` with both providers disabled:
```text
WARNING:geo_service:All geo providers failed or are disabled for IP: 8.8.8.8. Degrading gracefully.
```
Response remains `201 Created` and row is saved with `geo_provider = None`.

### DoD: A failing confirmation email / webhook does not prevent the submission from being stored.
* **Evidence**: Verified in `test_notification_side_effect_resilience`. Setting `SIMULATE_NOTIFICATION_FAILURE = True` throws an exception in the background task, but the main submission route still responds `201 Created` and saves the submission.

---

## 6. Tests & Documentation

### DoD: Automated tests cover all criteria.
* **Execution Log** (`python -m pytest -v`):
```text
tests/test_main.py::test_tenant_registration_and_login PASSED            [ 11%]
tests/test_main.py::test_widget_crud_and_tenant_isolation PASSED         [ 22%]
tests/test_main.py::test_public_config_delivery_and_cors PASSED          [ 33%]
tests/test_main.py::test_public_submission_validation PASSED             [ 44%]
tests/test_main.py::test_honeypot_spam_protection PASSED                 [ 55%]
tests/test_main.py::test_geo_enrichment_fallback_chain PASSED            [ 66%]
tests/test_main.py::test_notification_side_effect_resilience PASSED      [ 77%]
tests/test_main.py::test_rate_limiting PASSED                            [ 88%]
tests/test_main.py::test_dashboard_api_analytics PASSED                  [100%]

======================= 9 passed, 24 warnings in 4.42s ========================
```

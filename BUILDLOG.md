# Build Log - AI Development Journal

This log documents the collaboration, development trajectory, and debugging process for building the FlyRank Embeddable Widget and Lead-Capture Platform.

---

## Where the AI Helped
1. **Core Structure**: Scaffolding the multi-tenant database schemas, API routers, and Pydantic validation models using clean-layered design patterns.
2. **Abuse Protection & Services**: Designing a lightweight sliding window in-memory rate limiter and implementing the geolocation provider fallback chain.
3. **Frontend Assets**: Designing high-fidelity interactive HTML/CSS files:
   - `static/widget.js`: Scoped form injector with client-side loaders.
   - `static/dashboard.html`: Glassmorphism dark-themed control console displaying custom SVG metrics charts.
4. **Automated Test Coverage**: Formulating a complete `pytest` suite checking preflight headers, content length restrictions, rate limits, outages fallbacks, and honeypots.

---

## Where the AI Was Wrong & Debugging Actions

### 1. Database Package Namespace Collision
* **Issue**: Initially, the database layer was placed under the package `db/`. Upon running `pytest`, Python failed to load our models due to a namespace collision with a globally installed, outdated Python 2 package named `db` in the system `site-packages` directory.
* **Resolution**: Refactored the local folder name from `db/` to `app_db/` to prevent shadowing and ensure correct local imports.

### 2. Passlib & Bcrypt Compatibility on Python 3.13
* **Issue**: The authentication service initially imported `passlib.context.CryptContext` with `bcrypt`. In Python 3.13 and newer versions of the `bcrypt` library (4.x), `passlib` raises a `ValueError` inside its internal feature-checking routines because it passes a long mock secret that exceeds bcrypt's 72-byte threshold.
* **Resolution**: Refactored password verification and hashing in `services/auth_service.py` to use the standard `bcrypt` package directly (`bcrypt.hashpw` and `bcrypt.checkpw`), eliminating the `passlib` dependency and error.

### 3. Rate Limit Leakage Across Tests
* **Issue**: The tests failed with `429 Too Many Requests` during geolocation and safe side-effect tests because requests from previous tests filled the sliding window limit (5 requests per minute).
* **Resolution**: Added a `pytest.fixture(autouse=True)` in `tests/test_main.py` that clears the rate limiter history logs before each test function runs.

### 4. TestClient Client Hostname resolving
* **Issue**: During tests, FastAPI's `TestClient` uses `"testclient"` as the client host. This caused the geolocation service to pass the string `"testclient"` to external APIs, triggering failure responses.
* **Resolution**: Patched `services/geo_service.py` to recognize `"testclient"` as a local address, defaulting to `8.8.8.8` (Google Public DNS) for testing. Furthermore, implemented a mock override parameter (`MOCK_PROVIDER_A_RESPONSE` and `MOCK_PROVIDER_B_RESPONSE`) to make test runs entirely deterministic and network-independent.

### 5. Repository Initialization & Git History

* **Issue**: The dedicated GitHub repository was initialized after the initial development work had already been completed. This meant the Git history does not represent the complete chronology of the project's development from day one.

* **Resolution**: Initialized and published the dedicated repository once this was identified, and tracked subsequent development, testing, documentation, and fixes through meaningful commits. No historical commits were fabricated or backdated.

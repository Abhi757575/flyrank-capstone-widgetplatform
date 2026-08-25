# FlyRank Capstone: Embeddable Widget & Lead-Capture Platform

A robust, multi-tenant lead capture platform that allows businesses (tenants) to configure forms, embed them on external websites using a single `<script>` tag, and capture validated, geo-enriched, and spam-protected submissions in a dashboard.

Built using **Python (FastAPI)** and **Vanilla CSS + HTML5**.

---

## Architecture Diagram

```text
              +-------------------------------------------------+
              |                 CUSTOMER WEBSITE                |
              |       (e.g., http://localhost:8080/index.html)  |
              +-----------------------+-------------------------+
                                      |
                      1. Fetch config | 3. POST submissions
                                      v
+-------------------------------------+-------------------------------------+
|                              API BACKEND (8000)                           |
|                                                                           |
|   +-------------------+    +-------------------+    +-----------------+   |
|   |   GET CONFIG      |    |  POST SUBMISSIONS |    |  ADMIN API      |   |
|   |   /widgets/id/conf|    |  /submissions     |    |  /widgets (CRUD)|   |
|   +---------+---------+    +---------+---------+    +--------+--------+   |
|             |                        |                       |            |
|             | [CORS Allowed]         | [CORS, Rate Limiting] | [JWT Auth] |
|             v                        v                       v            |
|     +---------------+        +---------------+               |            |
|     |  Widget Cache |        | Honeypot Check|               |            |
|     +---------------+        +-------+-------+               |            |
|                                      | [Not spam]            |            |
|                                      v                       |            |
|                              +---------------+               |            |
|                              |  Validation   |               |            |
|                              +-------+-------+               |            |
|                                      | [Valid]               v            |
|                                      v              +-----------------+   |
|                              +---------------+      |   Dashboard     |   |
|                              |  Geo-Lookup   | <----+   Analytics     |   |
|                              |  (Fallback)   |      |   Submissions   |   |
|                              +-------+-------+      +--------+--------+   |
|                                      |                       |            |
|                                      +-----------+-----------+            |
|                                                  |                        |
|                                                  v                        |
|                                       +--------------------+              |
|                                       | SQLite / Postgres  |              |
|                                       +----------+---------+              |
|                                                  |                        |
|                                                  v                        |
|                                       +--------------------+              |
|                                       | Background Task:   |              |
|                                       | Webhook / Email    |              |
|                                       +--------------------+              |
+---------------------------------------------------------------------------+
```

---

## Core Features

1. **Multi-Tenant Administration**: Dashboard with user authentication (registration & JWT-based login), allowing full CRUD widget management.
2. **CORS & Preflight Compliance**: Public endpoints are exposed safely to external domains with complete CORS and preflight (`OPTIONS`) configurations.
3. **HTTP Caching**: Public configurations are served with a short-lived cache-control (`max-age=60`) to balance fresh settings and server performance.
4. **Honeypot Spam Protection**: Silently drops spam submissions where hidden honeypot fields are filled, returning fake HTTP successes to bots.
5. **In-Memory Rate Limiting**: sliding window rate limiter keyed per Client IP + Widget ID (returns `429 Too Many Requests` during bursts).
6. **Robust Geolocation Lookup**: IP geolocation enrichment utilizing `ip-api.com` with fallback to `ipapi.co`. Degrades gracefully to save submissions if both go offline.
7. **Resilient Side Effects**: Triggers webhooks or confirmation emails asynchronously using FastAPI's background thread pools. Failures in side-effects do not block submissions.

---

## Installation & Setup

Ensure you have **Python 3.11+** installed.

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(The default configuration sets SQLite `sqlite:///./capstone.db` as the database)*

### 3. Initialize & Seed Database
Initialize schema and seed demo widgets, an owner tenant account, and historical submissions:
```bash
python seed.py
```
This prints the credentials to use:
* **Tenant Email**: `tenant@company.com`
* **Tenant Password**: `password123`

### 4. Run the API Server
Start the FastAPI server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
* The API Swagger documentation is available at: [http://localhost:8000/docs](http://localhost:8000/docs)
* The Owner Dashboard is available at: [http://localhost:8000/static/dashboard.html](http://localhost:8000/static/dashboard.html)

---

## Embedding a Widget (Demo)

To see the widget render on an external website:

1. Open a second terminal and start a static web server from the `static/` directory to simulate another origin:
   ```bash
   python -m http.server 8080
   ```
2. Navigate to the test client site: [http://localhost:8080/static/test_client.html](http://localhost:8080/static/test_client.html)
3. Log into the FlyRank Dashboard ([http://localhost:8000/static/dashboard.html](http://localhost:8000/static/dashboard.html)) with the seeded user (`tenant@company.com` / `password123`).
4. Click on the widget in the sidebar, copy the Widget ID or the generated `<script>` tag.
5. Paste the Widget ID into the input on the test site at port `8080` and click "Embed Widget". The widget will load, render, and submit successfully to port `8000` via CORS!

---

## Running Tests
Run the automated test suite covering all 9 acceptance criteria:
```bash
python -m pytest -v
```

---

## Limitations

* **In-Memory Rate Limiter**: The sliding window rate limiter stores logs in RAM. If the application is deployed behind a horizontal load balancer with multiple process nodes, rate limits won't synchronize unless refactored to use a distributed store (e.g., Redis).
* **SMTP Server**: Email side-effects are simulated via background prints and logging rather than connecting to a live SMTP server.
* **Database Migrations**: Database tables are initialized using SQLAlchemy `create_all`. Changes to schema require table drops or manual management since Alembic migrations are not configured in this scope.

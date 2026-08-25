import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config import settings
from app_db.database import engine, Base
from api import auth, widgets, submissions, dashboard

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title="FlyRank Capstone - Widget & Lead-Capture Platform",
    description="Multi-tenant embeddable widget system with geo-enrichment and abuse protection.",
    version="1.0.0",
    lifespan=lifespan
)

# Global CORS middleware configuration
# Since widgets are embedded on external sites, the submission and config endpoints
# must allow cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins to load widgets and send submissions
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router)
app.include_router(widgets.router)
app.include_router(submissions.router)
app.include_router(dashboard.router)

# Mount the static directory to serve frontend assets:
# - widget.js (embed script)
# - test_client.html (customer mock host page)
# - dashboard.html (tenant admin dashboard)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "FlyRank Capstone API. Admin dashboard available at /static/dashboard.html"
    }

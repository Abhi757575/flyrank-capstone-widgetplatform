import logging
import re
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from app_db.database import get_db
from app_db import models
from services.rate_limiter import submission_rate_limiter
from services.geo_service import get_ip_geolocation
from services.notification_service import process_submission_side_effects

logger = logging.getLogger("submissions_api")

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

# Maximum allowed payload size in bytes (e.g., 100 KB)
MAX_PAYLOAD_SIZE = 100 * 1024

def validate_submission_payload(widget: models.Widget, payload: dict):
    """
    Dynamically validates the submitted payload fields against the widget configuration.
    """
    configured_fields = widget.fields
    
    # Track required and type validations
    for field in configured_fields:
        field_name = field.get("name")
        field_type = field.get("type", "text")
        is_required = field.get("required", False)
        
        val = payload.get(field_name)
        
        # Check required fields
        if is_required:
            if val is None or (isinstance(val, str) and val.strip() == ""):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Field '{field_name}' is required."
                )
        
        # Validate data types if value is provided
        if val is not None and val != "":
            if field_type == "email":
                # Basic email regex
                email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
                if not isinstance(val, str) or not re.match(email_regex, val):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Field '{field_name}' must be a valid email address."
                    )
            elif field_type == "number":
                try:
                    float(val)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Field '{field_name}' must be a numeric value."
                    )


@router.options("", tags=["public"])
async def options_submissions():
    """
    Handle CORS preflight OPTIONS request.
    We return standard success status codes and headers.
    """
    return Response(
        status_code=status.HTTP_200_OK,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "86400",
        }
    )

@router.post("", tags=["public"])
async def submit_form(request: Request, db: Session = Depends(get_db)):
    """
    Public submission receiver.
    Accepts submissions from any origin (CORS).
    Enforces payload size limits, rate limits, honeypots, geo-enrichment, and background tasks.
    """
    # Custom headers for CORS
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    # 1. Enforce Payload Size Limit (Headers check first)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_PAYLOAD_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Payload size too large."
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Content-Length header."
            )

    # Read body to verify actual bytes size
    body = await request.body()
    if len(body) > MAX_PAYLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload size too large."
        )

    # Parse JSON body
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload."
        )

    # Extract widget ID
    widget_id = data.get("widget_id")
    if not widget_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'widget_id' in submission."
        )

    # Verify widget exists
    widget = db.query(models.Widget).filter(models.Widget.id == widget_id).first()
    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found."
        )

    # 2. Abuse Protection: Rate Limiting
    # Resolve real client IP
    client_ip = request.headers.get("x-forwarded-for")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    if submission_rate_limiter.is_rate_limited(client_ip, widget_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )

    # 3. Abuse Protection: Honeypot Check
    # We look for a field named '_honeypot' or 'website' (if configured in widget fields as hidden)
    # The default widget template uses '_honeypot'
    honeypot_val = data.get("_honeypot")
    if honeypot_val is not None and str(honeypot_val).strip() != "":
        logger.warning(f"Spam detected: honeypot field filled. Client IP: {client_ip}")
        # Silent drop: Return HTTP 201 success so the spam bot believes it succeeded
        return Response(
            status_code=status.HTTP_201_CREATED,
            content='{"status": "success", "message": "Submission received"}',
            media_type="application/json",
            headers=cors_headers
        )

    # 4. Extract form fields payload (excluding control metadata like widget_id and honeypot)
    submission_payload = {k: v for k, v in data.items() if k not in ("widget_id", "_honeypot")}

    # 5. Validation: Validate field inputs
    validate_submission_payload(widget, submission_payload)

    # 6. Geolocation Enrichment
    # Fetch country and city asynchronously with fallbacks
    geo_country, geo_city, geo_provider = await get_ip_geolocation(client_ip)

    # 7. Store Submission in DB
    db_submission = models.Submission(
        widget_id=widget.id,
        payload=submission_payload,
        geo_country=geo_country,
        geo_city=geo_city,
        geo_provider=geo_provider
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)

    # 8. Safe Side Effects (Background Tasks)
    # Inside, it logs email or triggers webhooks safely (won't throw into our HTTP thread)
    process_submission_side_effects(widget, submission_payload)

    return Response(
        status_code=status.HTTP_201_CREATED,
        content='{"status": "success", "message": "Submission successfully received and processed."}',
        media_type="application/json",
        headers=cors_headers
    )

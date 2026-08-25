from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app_db.database import get_db
from app_db import models
from schemas import AnalyticsResponse, SubmissionResponse
from api.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/submissions", response_model=List[SubmissionResponse])
def get_dashboard_submissions(
    widget_id: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all submissions for the tenant's widgets, with optional widget filtering.
    """
    query = db.query(models.Submission).join(models.Widget).filter(
        models.Widget.owner_id == current_user.id
    )
    
    if widget_id:
        query = query.filter(models.Submission.widget_id == widget_id)
        
    submissions = query.order_by(models.Submission.created_at.desc()).all()
    return submissions

@router.get("/analytics", response_model=AnalyticsResponse)
def get_dashboard_analytics(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates aggregated statistics for the tenant's widgets.
    """
    # 1. Total Submissions count
    total_submissions = db.query(models.Submission).join(models.Widget).filter(
        models.Widget.owner_id == current_user.id
    ).count()

    # 2. Submissions over time (Group by Date)
    # Using SQLite date function to extract date string (YYYY-MM-DD)
    # If using postgres, we can use func.to_char
    date_func = func.date(models.Submission.created_at)
    time_stats = db.query(
        date_func.label("date"),
        func.count(models.Submission.id).label("count")
    ).join(models.Widget).filter(
        models.Widget.owner_id == current_user.id
    ).group_by(date_func).order_by(date_func).all()
    
    submissions_over_time = [{"date": s.date, "count": s.count} for s in time_stats]

    # 3. Geolocation breakdown
    geo_stats = db.query(
        models.Submission.geo_country.label("country"),
        func.count(models.Submission.id).label("count")
    ).join(models.Widget).filter(
        models.Widget.owner_id == current_user.id
    ).group_by(models.Submission.geo_country).all()
    
    geo_breakdown = []
    for g in geo_stats:
        country_name = g.country if g.country else "Unknown"
        geo_breakdown.append({"country": country_name, "count": g.count})

    # 4. Per-widget breakdown
    widget_stats_query = db.query(
        models.Widget.id.label("widget_id"),
        models.Widget.name.label("widget_name"),
        func.count(models.Submission.id).label("count")
    ).outerjoin(models.Submission).filter(
        models.Widget.owner_id == current_user.id
    ).group_by(models.Widget.id, models.Widget.name).all()

    widget_stats = [
        {"widget_id": w.widget_id, "widget_name": w.widget_name, "count": w.count}
        for w in widget_stats_query
    ]

    return {
        "total_submissions": total_submissions,
        "submissions_over_time": submissions_over_time,
        "geo_breakdown": geo_breakdown,
        "widget_stats": widget_stats
    }

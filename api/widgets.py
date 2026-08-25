from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app_db.database import get_db
from app_db import models
from schemas import WidgetCreate, WidgetResponse
from api.auth import get_current_user

router = APIRouter(prefix="/api/widgets", tags=["widgets"])

@router.post("", response_model=WidgetResponse, status_code=status.HTTP_201_CREATED)
def create_widget(widget_in: WidgetCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Create a new widget for the authenticated tenant.
    """
    # Convert FieldConfig models to dict
    fields_list = [f.dict() for f in widget_in.fields]
    
    db_widget = models.Widget(
        owner_id=current_user.id,
        name=widget_in.name,
        type=widget_in.type,
        title=widget_in.title,
        description=widget_in.description,
        fields=fields_list,
        button_text=widget_in.button_text,
        display_settings=widget_in.display_settings
    )
    db.add(db_widget)
    db.commit()
    db.refresh(db_widget)
    return db_widget

@router.get("", response_model=List[WidgetResponse])
def list_widgets(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    List all widgets belonging to the authenticated tenant.
    """
    widgets = db.query(models.Widget).filter(models.Widget.owner_id == current_user.id).all()
    return widgets

@router.get("/{widget_id}", response_model=WidgetResponse)
def get_widget(widget_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieve a specific widget (must belong to the authenticated tenant).
    """
    widget = db.query(models.Widget).filter(
        models.Widget.id == widget_id,
        models.Widget.owner_id == current_user.id
    ).first()
    
    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found or unauthorized access"
        )
    return widget

@router.put("/{widget_id}", response_model=WidgetResponse)
def update_widget(widget_id: str, widget_in: WidgetCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Update a widget's details (must belong to the authenticated tenant).
    """
    widget = db.query(models.Widget).filter(
        models.Widget.id == widget_id,
        models.Widget.owner_id == current_user.id
    ).first()
    
    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found or unauthorized access"
        )
    
    # Update fields
    widget.name = widget_in.name
    widget.type = widget_in.type
    widget.title = widget_in.title
    widget.description = widget_in.description
    widget.fields = [f.dict() for f in widget_in.fields]
    widget.button_text = widget_in.button_text
    widget.display_settings = widget_in.display_settings
    
    db.commit()
    db.refresh(widget)
    return widget

@router.delete("/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_widget(widget_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Delete a widget (must belong to the authenticated tenant).
    """
    widget = db.query(models.Widget).filter(
        models.Widget.id == widget_id,
        models.Widget.owner_id == current_user.id
    ).first()
    
    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found or unauthorized access"
        )
    
    db.delete(widget)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Public Endpoints ---

@router.get("/{widget_id}/config", tags=["public"])
def get_widget_config(widget_id: str, response: Response, db: Session = Depends(get_db)):
    """
    Public configuration endpoint for widget rendering.
    Allows public GET and returns cache control headers for standard short caching.
    """
    widget = db.query(models.Widget).filter(models.Widget.id == widget_id).first()
    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget config not found"
        )
    
    # Add HTTP caching: short-lived cache (60 seconds)
    response.headers["Cache-Control"] = "public, max-age=60"
    
    return {
        "id": widget.id,
        "type": widget.type,
        "title": widget.title,
        "description": widget.description,
        "fields": widget.fields,
        "button_text": widget.button_text,
        "display_settings": widget.display_settings
    }

import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr, Field

# User / Authentication schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None


# Widget schemas
class FieldConfig(BaseModel):
    name: str = Field(..., description="Machine-readable name of the input field")
    type: str = Field("text", description="Input type: text, email, number, textarea, select")
    label: str = Field(..., description="Human-readable label")
    required: bool = False
    options: Optional[List[str]] = None  # for select dropdowns
    placeholder: Optional[str] = None

class WidgetCreate(BaseModel):
    name: str = Field(..., min_length=1)
    type: str = Field("signup", description="signup, contact, popover")
    title: Optional[str] = None
    description: Optional[str] = None
    fields: List[FieldConfig]
    button_text: str = "Submit"
    display_settings: Dict[str, Any] = Field(default_factory=dict)

class WidgetResponse(BaseModel):
    id: str
    owner_id: int
    name: str
    type: str
    title: Optional[str]
    description: Optional[str]
    fields: List[FieldConfig]
    button_text: str
    display_settings: Dict[str, Any]
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# Submission schemas
class SubmissionCreate(BaseModel):
    # Flexible payload matching the widget's configured fields
    payload: Dict[str, Any]

class SubmissionResponse(BaseModel):
    id: int
    widget_id: str
    payload: Dict[str, Any]
    geo_country: Optional[str]
    geo_city: Optional[str]
    geo_provider: Optional[str]
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# Analytics schemas
class SubmissionCountOverTime(BaseModel):
    date: str
    count: int

class GeoBreakdown(BaseModel):
    country: str
    count: int

class WidgetStats(BaseModel):
    widget_id: str
    widget_name: str
    count: int

class AnalyticsResponse(BaseModel):
    total_submissions: int
    submissions_over_time: List[SubmissionCountOverTime]
    geo_breakdown: List[GeoBreakdown]
    widget_stats: List[WidgetStats]

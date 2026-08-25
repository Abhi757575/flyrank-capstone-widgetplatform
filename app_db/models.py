import datetime
import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app_db.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    widgets = relationship("Widget", back_populates="owner", cascade="all, delete-orphan")


class Widget(Base):
    __tablename__ = "widgets"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, default="signup", nullable=False)  # signup, contact, popover
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    fields = Column(JSON, nullable=False)  # List of field configurations
    button_text = Column(String, default="Submit", nullable=False)
    display_settings = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="widgets")
    submissions = relationship("Submission", back_populates="widget", cascade="all, delete-orphan")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    widget_id = Column(String, ForeignKey("widgets.id", ondelete="CASCADE"), nullable=False)
    payload = Column(JSON, nullable=False)  # Submitted form data
    geo_country = Column(String, nullable=True)
    geo_city = Column(String, nullable=True)
    geo_provider = Column(String, nullable=True)
    spam_filtered = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    widget = relationship("Widget", back_populates="submissions")

import datetime
from app_db.database import SessionLocal, Base, engine
from app_db import models
from services import auth_service

def seed():
    print("Dropping existing tables and recreating them...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Creating tenant user...")
        hashed_password = auth_service.get_password_hash("password123")
        user = models.User(
            email="tenant@company.com",
            hashed_password=hashed_password
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print("Creating default widget...")
        widget = models.Widget(
            owner_id=user.id,
            name="Newsletter Widget",
            type="signup",
            title="Weekly Newsletter SignUp",
            description="Subscribe to receive product updates and engineering tips directly in your inbox.",
            fields=[
                {"name": "name", "type": "text", "label": "Full Name", "required": True, "placeholder": "Jane Doe"},
                {"name": "email", "type": "email", "label": "Email Address", "required": True, "placeholder": "jane.doe@company.com"}
            ],
            button_text="Subscribe Now",
            display_settings={}
        )
        db.add(widget)
        db.commit()
        db.refresh(widget)

        print("Seeding submissions analytics data...")
        # Create some historical submissions
        now = datetime.datetime.utcnow()
        submissions_data = [
            {"payload": {"name": "Alice Smith", "email": "alice@gmail.com"}, "country": "United States", "city": "Ashburn", "provider": "ip-api.com", "days_ago": 4},
            {"payload": {"name": "Bob Jones", "email": "bob@yahoo.com"}, "country": "Canada", "city": "Toronto", "provider": "ipapi.co", "days_ago": 3},
            {"payload": {"name": "Charlie Brown", "email": "charlie@outlook.com"}, "country": "United Kingdom", "city": "London", "provider": "ip-api.com", "days_ago": 2},
            {"payload": {"name": "David Miller", "email": "david@company.com"}, "country": "Germany", "city": "Berlin", "provider": "ipapi.co", "days_ago": 1},
            {"payload": {"name": "Eva Davis", "email": "eva@domain.eu"}, "country": "France", "city": "Paris", "provider": "ip-api.com", "days_ago": 0},
        ]
        
        for data in submissions_data:
            created_at = now - datetime.timedelta(days=data["days_ago"])
            sub = models.Submission(
                widget_id=widget.id,
                payload=data["payload"],
                geo_country=data["country"],
                geo_city=data["city"],
                geo_provider=data["provider"],
                created_at=created_at
            )
            db.add(sub)
        
        db.commit()
        print("\nDatabase seeded successfully!")
        print("========================================")
        print("Tenant Email:   tenant@company.com")
        print("Tenant Password: password123")
        print(f"Widget ID:      {widget.id}")
        print(f"Widget Snippet: <script src=\"http://localhost:8000/static/widget.js?id={widget.id}\"></script>")
        print("========================================")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed()

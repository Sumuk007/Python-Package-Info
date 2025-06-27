# create_tables.py

from database import engine
from models import Base, User

print("📦 Connecting and creating tables...")

try:
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully.")
except Exception as e:
    print("❌ Table creation failed:", e)

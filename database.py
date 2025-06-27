from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql://postgres:sumuk@localhost:5500/python_package_info"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ✅ Connection test
try:
    with engine.connect() as conn:
        print("✅ Connected to PostgreSQL at port 5500")
except Exception as e:
    print("❌ Connection failed:", e)

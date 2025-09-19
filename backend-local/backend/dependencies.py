from sqlalchemy.orm import Session
from db.db import SessionLocal

def get_db():
    """Shared database dependency for all routers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from database import Base

class GuestDB(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    will_attend = Column(Boolean)
    drinks = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
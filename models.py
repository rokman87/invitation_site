from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base
from pydantic import BaseModel
from typing import Optional, List

class GuestBase(BaseModel):
    name: str
    will_attend: bool
    drinks: Optional[List[str]] = None

class GuestCreate(GuestBase):
    pass

class Guest(GuestBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # Заменяем orm_mode на from_attributes

class GuestDB(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    will_attend = Column(Boolean, nullable=False)
    drinks = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_pydantic(self):
        return Guest.model_validate(self)  # Используем новый метод валидации
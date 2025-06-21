from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, field_validator

class GuestBase(BaseModel):
    name: str
    will_attend: bool
    drinks: Optional[List[str]] = None

class GuestCreate(GuestBase):
    pass

class Guest(GuestBase):
    id: int
    created_at: datetime

    @field_validator('drinks', mode='before')
    def parse_drinks(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [item.strip() for item in v.split(',') if item.strip()]
        return v

    class Config:
        from_attributes = True
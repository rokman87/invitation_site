from typing import List
from datetime import datetime
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse, HTMLResponse
from starlette.status import HTTP_303_SEE_OTHER
from models import GuestDB, GuestCreate, Guest
from database import SessionLocal, engine, Base

app = FastAPI(title="Wedding Invitation", version="1.0")

# Инициализация БД
Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/submit-guest-form", response_class=RedirectResponse)
async def submit_guest_form(
    request: Request,
    name: str = Form(...),
    attendance: str = Form(...),
    drinks: List[str] = Form([]),
    db: Session = Depends(get_db)
):
    try:
        guest = GuestDB(
            name=name,
            will_attend=(attendance == "yes"),
            drinks=",".join(drinks) if drinks else None
        )
        db.add(guest)
        db.commit()
        return RedirectResponse(url="/?success=true", status_code=HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/guests/", response_model=Guest)
def create_guest(guest: GuestCreate, db: Session = Depends(get_db)):
    try:
        db_guest = GuestDB(
            name=guest.name,
            will_attend=guest.will_attend,
            drinks=",".join(guest.drinks) if guest.drinks else None
        )
        db.add(db_guest)
        db.commit()
        db.refresh(db_guest)
        return Guest.model_validate(db_guest)  # Используем новый метод валидации
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/guests/", response_model=List[Guest])
def read_guests(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    guests = db.query(GuestDB).offset(skip).limit(limit).all()
    return [Guest.model_validate(guest) for guest in guests]  # Обновленный метод валидации

if __name__ == "__main__":
    import uvicorn
    # Изменяем способ запуска для поддержки reload
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
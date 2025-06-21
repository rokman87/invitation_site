from datetime import datetime
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse, HTMLResponse, JSONResponse
from starlette.status import HTTP_303_SEE_OTHER
from models import GuestDB
from schemas import GuestCreate, Guest, GuestsResponse
from database import SessionLocal, init_db
from typing import List, Dict
from collections import defaultdict
# Инициализация приложения
app = FastAPI(title="Wedding Invitation", version="1.0")

# Инициализация БД (вызывается только при первом запуске)
init_db()

# Настройка статических файлов и шаблонов
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Роуты
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
            drinks=",".join(guest.drinks) if guest.drinks and len(guest.drinks) > 0 else None
        )
        db.add(db_guest)
        db.commit()
        db.refresh(db_guest)
        return db_guest
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# Модифицируем существующий endpoint /api/guests/
@app.get("/api/guests/", response_model=GuestsResponse)
def read_guests(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    guests = db.query(GuestDB).offset(skip).limit(limit).all()

    # Подсчет алкогольных предпочтений
    drinks_counter = defaultdict(int)
    total_count = 0

    for guest in guests:
        total_count += 1
        if guest.drinks:
            for drink in guest.drinks.split(','):
                drinks_counter[drink.strip()] += 1

    return {
        "guests": guests,
        "total_count": total_count,
        "drinks_summary": dict(drinks_counter)
    }


# Добавим новый endpoint только для summary (опционально)
@app.get("/api/guests/summary/")
def get_guests_summary(db: Session = Depends(get_db)):
    guests = db.query(GuestDB).all()

    drinks_counter = defaultdict(int)
    attending_count = 0
    total_count = len(guests)

    for guest in guests:
        if guest.will_attend:
            attending_count += 1
        if guest.drinks:
            for drink in guest.drinks.split(','):
                drinks_counter[drink.strip()] += 1

    return JSONResponse({
        "total_guests": total_count,
        "attending_guests": attending_count,
        "drinks_summary": dict(drinks_counter)
    })

@app.get("/guests", response_class=HTMLResponse)
async def view_guests(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("guests.html", {"request": request})


@app.get("/view-guests", response_class=HTMLResponse)
async def view_guests(
        request: Request,
        attendance: str = Query(None),
        drink: str = Query(None),
        db: Session = Depends(get_db)
):
    query = db.query(GuestDB)

    # Фильтрация по посещению
    if attendance == "yes":
        query = query.filter(GuestDB.will_attend == True)
    elif attendance == "no":
        query = query.filter(GuestDB.will_attend == False)

    # Фильтрация по напиткам
    if drink:
        query = query.filter(GuestDB.drinks.contains(drink))

    guests = query.order_by(GuestDB.created_at.desc()).all()

    return templates.TemplateResponse(
        "guests_view.html",
        {
            "request": request,
            "guests": guests,
            "attendance_filter": attendance,
            "drink_filter": drink
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
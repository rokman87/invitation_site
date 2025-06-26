from datetime import datetime
from fastapi import FastAPI, Request, Depends, Form, HTTPException, Response, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse, HTMLResponse
from starlette.status import HTTP_303_SEE_OTHER, HTTP_401_UNAUTHORIZED
from models import GuestDB
from database import SessionLocal, init_db
from typing import List, Optional
from fastapi import Query, status
import secrets
import hashlib

app = FastAPI(title="Wedding Invitation", version="1.0")

# Инициализация БД
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

# Конфигурация аутентификации
SECRET_KEY = "wedding-secret-key-123"
SESSION_COOKIE_NAME = "auth_token"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("wedding123".encode()).hexdigest()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_session(auth_token: Optional[str] = Cookie(default=None)):
    if not auth_token or auth_token != f"valid-{SECRET_KEY}":
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

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

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error}
    )

@app.post("/login")
async def do_login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if (secrets.compare_digest(username, ADMIN_USERNAME) and
        secrets.compare_digest(password_hash, ADMIN_PASSWORD_HASH)):
        response = RedirectResponse(url="/view-guests", status_code=HTTP_303_SEE_OTHER)
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=f"valid-{SECRET_KEY}",
            httponly=True,
            secure=False,  # В продакшене должно быть True
            samesite="lax"
        )
        return response
    else:
        return templates.TemplateResponse(
            "login.html",
            {"request": Request, "error": "Неверные учетные данные"},
            status_code=HTTP_401_UNAUTHORIZED
        )

@app.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/login")
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response

@app.get("/view-guests", response_class=HTMLResponse)
async def view_guests(
    request: Request,
    attendance: str = Query(None),
    drink: str = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(verify_session)
):
    query = db.query(GuestDB)

    if attendance == "yes":
        query = query.filter(GuestDB.will_attend == True)
    elif attendance == "no":
        query = query.filter(GuestDB.will_attend == False)

    if drink:
        query = query.filter(GuestDB.drinks.contains(drink))

    guests = query.order_by(GuestDB.created_at.desc()).all()

    return templates.TemplateResponse(
        "guests_view.html",
        {
            "request": request,
            "guests": guests,
            "attendance_filter": attendance,
            "drink_filter": drink,
        }
    )

@app.delete("/api/guests/{guest_id}")
def delete_guest(
    guest_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_session)
):
    guest = db.query(GuestDB).filter(GuestDB.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    try:
        db.delete(guest)
        db.commit()
        return {"message": "Guest deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
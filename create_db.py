from models import User, News
from database import engine, Base

Base.metadata.create_all(bind=engine)
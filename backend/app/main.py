from fastapi import APIRouter, FastAPI

from app.api.routes import auth, chat, documents, labs, medicines, profiles, shares, sheets, whatsapp

app = FastAPI(title="YourHealth")
api = APIRouter(prefix="/api/v1")


@api.get("/health/live")
def live():
    return {"status": "ok"}


api.include_router(auth.router)
api.include_router(profiles.router)
api.include_router(documents.router)
api.include_router(labs.router)
api.include_router(medicines.router)
api.include_router(chat.router)
api.include_router(sheets.router)
api.include_router(shares.router)
api.include_router(whatsapp.router)
app.include_router(api)

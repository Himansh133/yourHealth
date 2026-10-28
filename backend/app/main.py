from fastapi import APIRouter, FastAPI

app = FastAPI(title="YourHealth")
api = APIRouter(prefix="/api/v1")


@api.get("/health/live")
def live():
    return {"status": "ok"}


app.include_router(api)

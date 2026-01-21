from fastapi import FastAPI
from api.routes.status import router as status_router

app = FastAPI(title="Bot Status API", version="1.0")
app.include_router(status_router)

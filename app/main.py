from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router as api_router
from app.db import init_db
from app.websocket import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get('/')
def root():
    return {'status': 'ok-200'}


app.include_router(api_router)
app.include_router(websocket_router)
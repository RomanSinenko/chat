from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.websocket import router as websocket_router
from app.routers.users import router as users_router
from app.routers.chats import router as chats_router
from app.routers.chat_list import router as chat_list_router
from app.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get('/')
def root():
    return {'status': 'ok-200'}


app.include_router(websocket_router)
app.include_router(users_router)
app.include_router(chats_router)
app.include_router(chat_list_router)
app.include_router(auth_router)

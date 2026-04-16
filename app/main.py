from fastapi import FastAPI

from app.websocket import router as websocket_router

app = FastAPI()

@app.get('/')
def root():
    return {'status': 'ok-200'}


app.include_router(websocket_router)
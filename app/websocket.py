from typing import Dict
from fastapi import WebSocket, APIRouter


active_connections: Dict[int, WebSocket] = {}

router = APIRouter()

@router.websocket('/ws/{user_id}')
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    active_connections[user_id] = websocket
    try:
        while True:
            await websocket.receive_text()
    except:
        active_connections.pop(user_id, None)


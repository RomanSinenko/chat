from typing import Dict
from fastapi import WebSocket, APIRouter


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    async def send_message(self, to_user_id: int, message: str):
        connection = self.active_connections.get(to_user_id)
        if connection:
            await connection.send_text(message)
            return True
        return False

    async def send_message_to_self(self, websocket:WebSocket, message: str):
        await websocket.send_text(message)

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)


manager = ConnectionManager()
router = APIRouter()


@router.websocket('/ws/{user_id}')
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    await manager.send_message_to_self(websocket, 'Подключение с сервером установлено!')
    try:

        while True:
            message = await websocket.receive_text()
            data = message.split(':', 1)

            if len(data) == 2:
                try:
                    to_user_id = int(data[0])
                except ValueError:
                    continue
                text = data[1]

                sent = await manager.send_message(to_user_id, f'From: {user_id}: {text}')
                if not sent:
                    await manager.send_message_to_self(websocket,f'User {to_user_id} not connected')

            else:
                await manager.send_message_to_self(
                    websocket, 'Не верный формат сообщении. Используй "Номер абонента": "Сообщение" ')

    except:
        manager.disconnect(user_id)
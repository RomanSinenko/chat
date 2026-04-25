import json

from typing import Dict
from fastapi import WebSocket, APIRouter
from starlette.websockets import WebSocketDisconnect

from app.db import AsyncSessionLocal
from app.queries.chats import get_chat_by_id
from app.queries.users import get_user_by_id
from app.queries.messages import create_message


class ConnectionManager:
    def __init__(self):
        # Храним активные подключения по user_id, чтобы можно было
        # быстро найти нужный сокет и отправить сообщение конкретному пользователю.
        self.active_connections: Dict[int, WebSocket] = {}

    # Если пользователь переподключается, стараемся закрыть старый сокет,
    # чтобы в active_connections всегда оставалось только одно актуальное соединение.
    async def connect(self, user_id: int, websocket: WebSocket):
        # если соединение было установлено ранее - оно закрывается
        if user_id in self.active_connections:
            old_connection = self.active_connections[user_id]

            try:
                await old_connection.close()
            except RuntimeError:
                pass

            print(f'User {user_id} reconnected (old connection closed)')

        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f'User {user_id} connected')


    # Отправляем готовое сообщение конкретному пользователю, если его соединение активно.
    async def send_message(self, to_user_id: int, message: str):
        connection = self.active_connections.get(to_user_id)

        if connection:
            try:
                await connection.send_text(message)
                print(f'Sent to {to_user_id}: {message}')
                return True
            except WebSocketDisconnect:
                self.disconnect(to_user_id)
                print(f'Failed to send: user {to_user_id} disconnected')
        return False


    # Системные сообщения отправляем обратно текущему клиенту.
    async def send_message_to_self(self, websocket:WebSocket, message: str):
        response_send = {
            'type': 'system',
            'text': message,
        }
        await websocket.send_text(json.dumps(response_send, ensure_ascii=False))

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)
        print(f'User {user_id} disconnected')


manager = ConnectionManager()
router = APIRouter()


# Разбираем входящий JSON и возвращаем только те данные,
# которые нужны для message flow: chat_id, получатель и текст.
def parse_message(message: str):
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return None, None, None

    chat_id = data.get('chat_id')
    to_user_id = data.get('to_user_id')
    text = data.get('text')

    # Если один из обязательных параметров невалиден, считаем сообщение некорректным.
    if not isinstance(chat_id, int) or not isinstance(to_user_id, int) or not isinstance(text, str):
        return None, None, None

    return chat_id, to_user_id, text


@router.websocket('/ws/{user_id}')
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    await manager.send_message_to_self(websocket, 'Подключение с сервером установлено!')
    try:

        while True:
            message = await websocket.receive_text()
            print(f'Received from {user_id}: {message}')

            chat_id, to_user_id, text = parse_message(message)
            if  chat_id is None:
                await manager.send_message_to_self(
                    websocket, 'Неверный формат сообщения. Используй JSON: {"chat_id": 1, "to_user_id": 2, "text": "hello"}')
                continue

            response_sent = {
                'type': 'message',
                'from_user_id': user_id,
                'text': text,
            }

            async with AsyncSessionLocal() as session:
                user = await get_user_by_id(session, user_id)
                chat = await get_chat_by_id(session, chat_id)

                if user is None:
                    await manager.send_message_to_self(websocket, f'User with id {user_id} not found in database')
                    continue

                if chat is None:
                    await manager.send_message_to_self(websocket, f'Chat with id {chat_id} not found in database')
                    continue

                # Сначала сохраняем сообщение в БД, чтобы realtime и storage не расходились.
                await create_message(
                    session=session,
                    chat_id=chat_id,
                    sender_id=user_id,
                    text=text,
                )

            # После успешного сохранения пытаемся доставить сообщение получателю онлайн.
            sent = await manager.send_message(to_user_id, json.dumps(response_sent, ensure_ascii=False))

            if not sent:
                await manager.send_message_to_self(websocket, f'User {to_user_id} not connected')


    except WebSocketDisconnect:
        manager.disconnect(user_id)
        print(f'User {user_id} disconnected')

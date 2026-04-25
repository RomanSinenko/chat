import json

from typing import Dict
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect


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


    # Сообщение об ошибках
    async def send_error(self, websocket: WebSocket, code: str, message: str):
        response_error = {
            'type': 'error',
            'code': code,
            'text': message,
        }
        await  websocket.send_text(json.dumps(response_error, ensure_ascii=False))


    # Подтверждаем отправителю, что сервер принял и сохранил сообщение.
    async def send_message_ack(self, websocket: WebSocket, chat_id: int, message_id: int):
        response_ack = {
            'type': 'message_ack',
            'chat_id': chat_id,
            'message_id': message_id,
            'status': 'saved',
        }
        await websocket.send_text(json.dumps(response_ack, ensure_ascii=False))



    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)
        print(f'User {user_id} disconnected')

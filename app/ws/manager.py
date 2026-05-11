import json

from dataclasses import dataclass
from typing import Dict
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect


@dataclass
class ActiveConnection:
    # WebSocket нужен для отправки событий пользователю онлайн.
    websocket: WebSocket
    # session_id связывает socket с конкретной активной сессией пользователя.
    session_id: int


class ConnectionManager:
    def __init__(self):
        # Храним активные подключения по user_id.
        # Вместе с websocket сохраняем session_id, чтобы можно было
        # закрывать и проверять конкретную пользовательскую сессию.
        self.active_connections: Dict[int, ActiveConnection] = {}

    # Если пользователь переподключается, стараемся закрыть старый сокет,
    # чтобы в active_connections всегда оставалось только одно актуальное соединение.
    async def connect(self, user_id: int, session_id: int, websocket: WebSocket):
        # если соединение было установлено ранее - оно закрывается
        if user_id in self.active_connections:
            old_connection = self.active_connections[user_id].websocket

            try:
                await old_connection.close()
            except RuntimeError:
                pass

            print(f'User {user_id} reconnected (old connection closed)')

        await websocket.accept()
        self.active_connections[user_id] = ActiveConnection(
            websocket=websocket,
            session_id=session_id,
        )
        print(f'User {user_id} connected')


    # Отправляем готовое сообщение конкретному пользователю, если его соединение активно.
    async def send_message(self, to_user_id: int, message: str):
        connection = self.active_connections.get(to_user_id)

        if connection:
            try:
                await connection.websocket.send_text(message)
                print(f'Sent message to user {to_user_id}')
                return True
            except WebSocketDisconnect:
                self.disconnect(to_user_id, connection.session_id)
                print(f'Failed to send: user {to_user_id} disconnected')

        return False


    # Возвращает session_id активного WebSocket-соединения пользователя.
    def get_connection_session_id(self, user_id: int) -> int | None:
        connection = self.active_connections.get(user_id)

        if connection is None:
            return None

        return connection.session_id


    # Закрываем активное WebSocket-соединение пользователя, если оно есть.
    async def close_connection(self, user_id: int, session_id: int | None = None):
        connection = self.active_connections.get(user_id)

        if connection is None:
            return

        if session_id is not None and connection.session_id != session_id:
            return

        try:
            await connection.websocket.close()
        except RuntimeError:
            pass

        self.disconnect(user_id, connection.session_id)

    # Системные сообщения отправляем обратно текущему клиенту.
    async def send_message_to_self(self, websocket: WebSocket, message: str):
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
    async def send_message_ack(
            self,
            websocket: WebSocket,
            client_message_id: str,
            chat_id: int,
            message_id: int,
            created_at
    ):

        response_ack = {
            'type': 'message_ack',
            'client_message_id': client_message_id,
            'chat_id': chat_id,
            'message_id': message_id,
            'status': 'saved',
            'created_at': created_at.isoformat(),
        }
        await websocket.send_text(json.dumps(response_ack, ensure_ascii=False))


    # Удаляем соединение только если session_id совпадает.
    # Это защищает новое соединение от случайного удаления старым socket-ом.
    def disconnect(self, user_id: int, session_id: int | None = None):
        connection = self.active_connections.get(user_id)

        if connection is None:
            return

        if session_id is not None and connection.session_id != session_id:
            return

        self.active_connections.pop(user_id, None)
        print(f'User {user_id} disconnected')

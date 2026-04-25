import json

from fastapi import WebSocket, APIRouter
from starlette.websockets import WebSocketDisconnect

from app.db import AsyncSessionLocal
from app.ws.manager import ConnectionManager
from app.ws.protocol import parse_message

from app.queries.chats import get_chat_by_id
from app.queries.users import get_user_by_id
from app.queries.messages import create_message
from app.queries.chat_members import get_chat_member


manager = ConnectionManager()
router = APIRouter()


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
                await manager.send_error(
                    websocket,
                    'invalid_message_format',
                    'Неверный формат сообщения. Используй JSON: {"chat_id": 1, "to_user_id": 2, "text": "hello"}',
                )
                continue

            response_sent = {
                'type': 'message',
                'from_user_id': user_id,
                'text': text,
            }

            async with AsyncSessionLocal() as session:
                user = await get_user_by_id(session, user_id)
                chat = await get_chat_by_id(session, chat_id)
                chat_member = await get_chat_member(session, chat_id, user_id)

                # Проверка, что пользователь существует
                if user is None:
                    await manager.send_error(
                        websocket,
                        'user_not_found',
                        f'User with id {user_id} not found in database',
                    )
                    continue

                # Проверка, что чат существует
                if chat is None:
                    await manager.send_error(
                        websocket,
                        'chat_not_found',
                        f'Chat with id {chat_id} not found in database',)
                    continue

                # Проверка, что пользователь состоит в чате
                if chat_member is None:
                    await manager.send_error(
                        websocket,
                        'user_not_found_in_chat',
                        f'User with id {user_id} is not a member of chat {chat_id}',
                    )
                    continue

                # Сначала сохраняем сообщение в БД, чтобы realtime и storage не расходились.
                saved_message = await create_message(
                    session=session,
                    chat_id=chat_id,
                    sender_id=user_id,
                    text=text,
                )

            # Для self-chat не отправляем сообщение обратно как входящее.
            # Вместо этого подтверждаем отправителю, что сообщение сохранено.
            if to_user_id == user_id:
                await manager.send_message_ack(
                    websocket,
                    chat_id=chat_id,
                    message_id=saved_message.id,
                )
                continue

            # После успешного сохранения пытаемся доставить сообщение получателю онлайн.
            sent = await manager.send_message(to_user_id, json.dumps(response_sent, ensure_ascii=False))

            if not sent:
                await manager.send_error(
                    websocket,
                    'recipient_not_connected',
                    f'User {to_user_id} not connected',
                )


    except WebSocketDisconnect:
        manager.disconnect(user_id)
        print(f'User {user_id} disconnected')

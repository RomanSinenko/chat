import json

from fastapi import WebSocket, APIRouter, Header
from starlette.websockets import WebSocketDisconnect

from app.db import AsyncSessionLocal
from app.ws.manager import ConnectionManager
from app.ws.protocol import parse_send_message

from app.queries.chats import get_chat_by_id
from app.queries.users import get_user_by_id
from app.queries.messages import create_message
from app.queries.chat_members import get_chat_member
from app.queries.user_sessions import get_active_user_session_by_token, get_active_user_session_by_id


manager = ConnectionManager()
router = APIRouter()


@router.websocket('/ws')
async def websocket_endpoint(
        websocket: WebSocket,
        authorization: str | None = Header(default=None)
):

    # WebSocket не умеет удобно передавать Bearer token через Depends,
    # поэтому header Authorization проверяем вручную при handshake.
    if authorization is None or not authorization.startswith('Bearer '):
        await websocket.accept()
        await manager.send_error(
            websocket,
            'missing_token',
            'Authorization Bearer token is required',
        )
        await websocket.close()
        return

    session_token = authorization.removeprefix('Bearer ').strip()

    if not session_token:
        await websocket.accept()
        await manager.send_error(
            websocket,
            'missing_token',
            'Authorization Bearer token is required',
        )
        await websocket.close()
        return

    async with AsyncSessionLocal() as session:
        user_session = await get_active_user_session_by_token(session, session_token)

    if user_session is None:
        await websocket.accept()
        await  manager.send_error(
            websocket,
            'invalid_token',
            'Invalid or expired session token',
        )
        await websocket.close()
        return

    user_id = user_session.user_id
    session_id = user_session.id

    # В manager кладем и user_id, и session_id, чтобы позже закрывать именно эту сессию.
    await manager.connect(user_id, session_id, websocket)
    await manager.send_message_to_self(websocket, 'Подключение с сервером установлено!')

    try:

        while True:
            message = await websocket.receive_text()

            # Перед каждым входящим сообщением проверяем, что сессия все еще активна.
            # Если токен отозвали после подключения, старый socket должен быть закрыт.
            async with AsyncSessionLocal() as session:
                active_session = await get_active_user_session_by_id(session, session_id)

            if active_session is None:
                await manager.send_error(
                    websocket,
                    'session_inactive',
                    'Session is no longer active',
                )
                await manager.close_connection(user_id, session_id)
                return

            payload, error_code, error_text = parse_send_message(message)
            if payload is None:
                await manager.send_error(
                    websocket,
                    error_code,
                    error_text,
                )
                continue

            client_message_id = payload['client_message_id']
            chat_id = payload['chat_id']
            to_user_id = payload['to_user_id']
            text = payload['text']

            print(
                f'Received message metadata: '
                f'user_id={user_id}, chat_id={chat_id}, text_length={len(text)}'
            )


            async with AsyncSessionLocal() as session:
                user = await get_user_by_id(session, user_id)
                chat = await get_chat_by_id(session, chat_id)
                chat_member = await get_chat_member(session, chat_id, user_id)
                recipient_member = await get_chat_member(session, chat_id, to_user_id)

                # Проверка, что пользователь существует.
                if user is None:
                    await manager.send_error(
                        websocket,
                        'user_not_found',
                        f'User with id {user_id} not found in database',
                    )
                    continue

                # Проверка, что чат существует.
                if chat is None:
                    await manager.send_error(
                        websocket,
                        'chat_not_found',
                        f'Chat with id {chat_id} not found in database',
                    )
                    continue

                # Проверка, что пользователь состоит в чате
                if chat_member is None:
                    await manager.send_error(
                        websocket,
                        'user_not_found_in_chat',
                        f'User with id {user_id} is not a member of chat {chat_id}',
                    )
                    continue

                # Проверка, что получатель тоже состоит в этом чате.
                if recipient_member is None:
                    await manager.send_error(
                        websocket,
                        'recipient_not_found_in_chat',
                        f'User with id {to_user_id} is not a member of chat {chat_id}',
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
                    client_message_id=client_message_id,
                    chat_id=chat_id,
                    message_id=saved_message.id,
                    created_at=saved_message.created_at,
                )
                continue

            await manager.send_message_ack(
                websocket,
                client_message_id=client_message_id,
                chat_id=chat_id,
                message_id=saved_message.id,
                created_at=saved_message.created_at,
            )

            response_sent = {
                'type': 'message',
                'message': {
                    'id': saved_message.id,
                    'chat_id': saved_message.chat_id,
                    'sender_id': saved_message.sender_id,
                    'text': saved_message.text,
                    'message_type': saved_message.message_type,
                    'created_at': saved_message.created_at.isoformat(),
                }
            }

            recipient_session_id = manager.get_connection_session_id(to_user_id)

            if recipient_session_id is not None:
                # Перед доставкой online-получателю проверяем, что его socket привязан
                # к активной сессии, а не к уже отозванному токену.
                async with AsyncSessionLocal() as session:
                    recipient_session = await get_active_user_session_by_id(session, recipient_session_id)

                if recipient_session is None:
                    await manager.close_connection(to_user_id, recipient_session_id)

            # После успешного сохранения пытаемся доставить сообщение получателю онлайн.
            sent = await manager.send_message(to_user_id, json.dumps(response_sent, ensure_ascii=False))

            if not sent:
                print(
                    f'Recipient offline: '
                    f'to_user_id={to_user_id}, chat_id={chat_id}, message_id={saved_message.id}'
                )


    except WebSocketDisconnect:
        manager.disconnect(user_id, session_id)
        print(f'User {user_id} disconnected')

import json


MAX_MESSAGE_TEXT_LENGTH = 4000
MAX_CLIENT_MESSAGE_ID_LENGTH = 64


# Разбирает WebSocket-событие отправки сообщения.
# Возвращает данные сообщения или код ошибки.
def parse_send_message(message: str):
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return None, 'invalid_json', 'Message must be valid JSON'

    event_type = data.get('type')
    client_message_id = data.get('client_message_id')
    chat_id = data.get('chat_id')
    to_user_id = data.get('to_user_id')
    text = data.get('text')

    if event_type != 'send_message':
        return None, 'invalid_event_type', 'Event type must be send_message'

    if not isinstance(client_message_id, str):
        return None, 'invalid_client_message_id', 'client_message_id must be a string'

    if not client_message_id or len(client_message_id) > MAX_CLIENT_MESSAGE_ID_LENGTH:
        return None, 'invalid_client_message_id', 'client_message_id length must be from 1 to 64'

    if not isinstance(chat_id, int):
        return None, 'invalid_chat_id', 'chat_id must be an integer'

    if not isinstance(to_user_id, int):
        return None, 'invalid_to_user_id', 'to_user_id must be an integer'

    if not isinstance(text, str):
        return None, 'invalid_text', 'text must be a string'

    text = text.strip()

    if not text:
        return None, 'empty_message', 'Message text cannot be empty'

    if len(text) > MAX_MESSAGE_TEXT_LENGTH:
        return None, 'message_too_long', 'Message text is too long'

    return {
        'client_message_id': client_message_id,
        'chat_id': chat_id,
        'to_user_id': to_user_id,
        'text': text,
    }, None, None


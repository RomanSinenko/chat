import json


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


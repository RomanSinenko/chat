# Chat Backend MVP

Backend MVP чат-приложения на `FastAPI` с:
- HTTP API
- WebSocket realtime messaging
- PostgreSQL persistence
- private chat / self-chat flow

## Текущий статус

Сейчас backend умеет:
- создавать пользователей
- искать пользователей по части имени
- создавать или находить private chat между двумя пользователями
- возвращать список чатов пользователя
- возвращать мета-информацию о чате
- возвращать историю сообщений по `chat_id`
- отправлять сообщения по WebSocket
- сохранять сообщения в PostgreSQL

## Стек

- Python 3.12
- FastAPI
- Uvicorn
- PostgreSQL
- SQLAlchemy 2.x
- asyncpg

## Структура проекта

```text
app/
  main.py
  db.py
  models.py
  websocket.py
  routers/
    users.py
    chats.py
  ws/
    manager.py
    protocol.py
  queries/
    users.py
    chats.py
    messages.py
    chat_members.py
```

## Запуск

1. Создать и активировать виртуальное окружение
2. Установить зависимости:

```bash
pip install -r requirements.txt
```

3. Поднять локальный PostgreSQL и создать базу `chat_db`
4. Установить `DATABASE_URL`, если нужен не дефолтный локальный адрес
5. Запустить приложение:

```bash
python run.py
```

После запуска:
- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

## Основные HTTP endpoints

### Пользователи

- `POST /auth/dev-login`
  Временный вход/регистрация по телефону через JSON body

- `GET /users/search?query=...`
  Ищет пользователя по точному публичному username

### Чаты

- `POST /private-chats`
  Находит существующий private chat или создаёт новый

- `GET /users/me/chats`
  Возвращает список чатов текущего пользователя из токена

- `GET /chats/{chat_id}`
  Возвращает мета-информацию о чате для экрана открытия

- `GET /chats/{chat_id}/messages?limit=50&offset=0`
  Возвращает историю сообщений

Все рабочие ручки, кроме `/` и `/auth/dev-login`, требуют header:

```http
Authorization: Bearer <session_token>
```

## WebSocket

Подключение:

```text
/ws
```

Header:

```http
Authorization: Bearer <session_token>
```

Формат исходящего сообщения от клиента:

```json
{
  "type": "send_message",
  "client_message_id": "ios-local-id-123",
  "chat_id": 1,
  "to_user_id": 2,
  "text": "hello"
}
```

Форматы ответов сервера:

Обычное сообщение:

```json
{
  "type": "message",
  "from_user_id": 1,
  "text": "hello"
}
```

Ошибка:

```json
{
  "type": "error",
  "code": "recipient_not_connected",
  "text": "User 2 not connected"
}
```

Подтверждение для self-chat:

```json
{
  "type": "message_ack",
  "chat_id": 1,
  "message_id": 15,
  "status": "saved"
}
```

## Ближайший фокус

- подгрузка истории при открытии чата
- offline-basic сценарий через чтение истории из БД
- подготовка backend под мобильный фронт

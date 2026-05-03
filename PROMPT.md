# Backend Prompt

Backend MVP чат-приложения с realtime-обменом по WebSocket.

Путь:
- `/Users/romansinenko/Desktop/prog/Chat/backend`

Текущая ветка:
- `backend-phone-only-dev-login`

Цель текущей ветки:
- подготовить backend-контракты под дальнейшую iOS-интеграцию
- разделить identity-модель пользователя
- добавить временный dev-login по телефону
- закрыть базовые contract/security блокеры перед продолжением iOS

---

# Текущий Стек

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy async
- asyncpg
- WebSocket
- phonenumbers для проверки и нормализации телефонов
- uvicorn

Запуск:

```bash
cd /Users/romansinenko/Desktop/prog/Chat/backend
source .venv/bin/activate
python3 run.py
```

---

# Текущая Модель Данных

## `User`

Публичный профиль пользователя:
- `id`
- `username` — уникальный публичный handle, в UI показывается как `@username`
- `display_name` — неуникальное отображаемое имя, может быть `null`, если пользователь еще не заполнил профиль
- `is_username_custom` — показывает, выбрал ли пользователь username сам
- `created_at`
- `updated_at`

Старое поле `user_name` убрано из backend-кода.

## `UserPhone`

Телефон и auth/identity-часть:
- `id`
- `user_id`
- `phone_e164`
- `phone_verified_at`
- `is_primary`
- `created_at`
- `updated_at`

Телефон:
- хранится отдельно от публичного профиля
- в MVP не показывается другим пользователям
- в MVP не используется для поиска
- без SMS считается неподтвержденным

## `Chat`

- `id`
- `chat_type`
- `title`
- `created_at`
- `last_message_at`

## `Message`

- `id`
- `chat_id`
- `sender_id`
- `text`
- `message_type`
- `created_at`

## `ChatMember`

- `id`
- `chat_id`
- `user_id`
- `role`
- `joined_at`

---

# Текущие HTTP Endpoints

## Auth

`POST /auth/dev-login?phone=...`

Временная dev-ручка без SMS:
- принимает только телефон
- проверяет телефон через `phonenumbers`
- приводит телефон к E.164
- если телефон уже есть в `user_phones`, возвращает существующего пользователя
- если телефона нет, создает нового пользователя
- новому пользователю backend генерирует временный username вида `user_a8f31c2d`
- `display_name = null`, профиль пользователь заполнит позже в Settings
- `is_username_custom = False`
- `phone_verified = False`

Ответ:

```json
{
  "user": {
    "id": 1,
    "username": "user_a8f31c2d",
    "display_name": null,
    "is_username_custom": false,
    "phone_verified": false
  },
  "created": true
}
```

## Users

`POST /users/{username}?display_name=...`

Dev-ручка создания пользователя с уже выбранным публичным username.

`GET /users/search?query=...`

Поиск:
- работает только по `username`
- `display_name` в поиске не используется
- поиск по телефону в MVP не реализуется

Целевое правило global search:
- глобальный поиск ищет только точное совпадение `username`
- пользователь может ввести `username` с `@` или без него, backend нормализует запрос
- поиск по `username` должен быть case-insensitive
- partial / substring global search не используем, чтобы не облегчать перебор пользователей
- global search возвращает максимум одного пользователя
- auto-generated username вида `user_a8f31c2d` не считается публичным
- пользователь попадает в global search только если username выбран явно и является public/custom
- будущая настройка `can_be_found_by_username = false` должна применяться на backend, а не только в UI
- поиск по контактам, поиск по существующим чатам и поиск участников группы являются отдельными контекстами, не этой ручкой

Discovery-основания:
- написать пользователю можно, если он есть в контактах
- или он написал первым и существующий чат не удален
- или есть общая группа
- или у него есть публичный custom username
- или он явно разрешил публичный поиск/доступ по телефону
- если переписка удалена и других оснований нет, пользователь снова не должен находиться текущим пользователем

Будущий smart search:
- отдельная задача после MVP exact-search
- цель: понимать близкие варианты имени между латиницей и кириллицей, например `Elena` и `Елена`
- также учитывать `ё/е`, Unicode-normalization, пробелы, возможную транслитерацию и опечатки
- smart search должен проектироваться отдельным backend/search слоем, а не случайной логикой внутри router
- запускать smart search глобально можно только с privacy/rate-limit ограничениями

## Chats

`POST /private-chats/{user_id}/{peer_user_id}`

Находит или создает private chat.

Возвращает:
- `id`
- `chat_type`
- `title`
- `peer_user_id`
- `created_at`
- `created`

`GET /users/{user_id}/chats`

Возвращает список чатов пользователя.

Для private chat:
- `display_name` строится через `app/services/peer_presentation.py`
- текущее правило: `peer_user.display_name` или `peer_user.username`
- `peer_user_id` равен id собеседника
- для self-chat `peer_user_id = null`

`GET /chats/{chat_id}?user_id=...`

Возвращает meta-информацию о чате и требует membership пользователя.

`GET /chats/{chat_id}/messages?user_id=...`

Возвращает историю сообщений и требует membership пользователя.

Если пользователь не участник чата, backend возвращает `403`.

---

# WebSocket

Endpoint:

```text
WS /ws/{user_id}
```

Входящий формат:

```json
{
  "chat_id": 1,
  "to_user_id": 2,
  "text": "hello"
}
```

События сервера:
- `message`
- `system`
- `error`
- `message_ack`

WebSocket перед сохранением сообщения проверяет:
- пользователь существует
- чат существует
- отправитель состоит в чате
- получатель тоже состоит в этом чате

Self-chat:
- сообщение сохраняется
- сервер не дублирует его как входящее
- вместо этого отправляется `message_ack`

Ограничение:
- `user_id` все еще приходит от клиента и не является production-auth
- позже нужно заменить это на `current_user` из полноценного auth-flow

---

# Структура Проекта

```text
app/
├── main.py
├── websocket.py
├── models.py
├── db.py
├── routers/
│   ├── __init__.py
│   ├── auth.py
│   ├── users.py
│   ├── chats.py
│   └── chat_list.py
├── queries/
│   ├── __init__.py
│   ├── user_phones.py
│   ├── users.py
│   ├── chats.py
│   ├── messages.py
│   └── chat_members.py
├── services/
│   ├── __init__.py
│   └── peer_presentation.py
└── ws/
    ├── __init__.py
    ├── manager.py
    └── protocol.py
```

---

# Реализованные Модули

## `main.py`

- создает `FastAPI`
- подключает `auth_router`
- подключает `users_router`
- подключает `chats_router`
- подключает WebSocket router
- через `lifespan` вызывает `init_db()`

## `models.py`

- `User`
- `UserPhone`
- `Chat`
- `Message`
- `ChatMember`

Даты используют `DateTime(timezone=True)`.

## `queries/users.py`

- `create_user(session, username, display_name, is_username_custom=False)`
- `get_user_by_id(session, user_id)`
- `search_users_by_username(session, query, limit=20)`
- `get_user_by_username(session, username)`

## `queries/user_phones.py`

- `get_user_phone_by_phone(session, phone_e164)`
- `create_user_phone(session, user_id, phone_e164)`

## `queries/chats.py`

- `create_chat(session, chat_type, title=None)`
- `get_chat_by_id(session, chat_id)`
- `get_private_chat_between_users(session, user_id, peer_user_id)`
- `get_chats_by_user_id(session, user_id)`
- `get_chat_meta_by_id(session, chat_id)`

## `queries/messages.py`

- `create_message(session, chat_id, sender_id, text, message_type='text')`
- `get_message_by_chat_id(session, chat_id, limit=50, offset=0)`
- `get_last_message_by_chat_id(session, chat_id)`

## `queries/chat_members.py`

- `add_chat_member(session, chat_id, user_id, role='member')`
- `get_chat_member(session, chat_id, user_id)`
- `get_chat_members(session, chat_id)`

## `routers/auth.py`

- dev-login по телефону
- нормализация телефона через `phonenumbers`
- генерация временного username
- возврат существующего пользователя при повторном входе по телефону

## `routers/users.py`

- создание пользователя с username
- поиск пользователей по username
- валидация username
- валидация display_name

## `routers/chats.py`

- chat meta
- history
- private chat get-or-create
- `peer_user_id` в private chat response
- membership check для истории

## `routers/chat_list.py`

- список чатов пользователя через `GET /users/{user_id}/chats`
- `peer_user_id` в chat list response
- `display_name` для private chat строится через `get_peer_display_name`

## `services/peer_presentation.py`

- единая точка логики отображения собеседника
- текущее правило: `display_name`, если он есть, иначе `username`
- позже сюда можно добавить имя из телефонной книги и privacy-правила показа телефона

## `websocket.py`

- WebSocket endpoint `/ws/{user_id}`
- прием JSON-сообщений
- сохранение сообщений
- membership checks
- recipient membership check
- `message_ack` для self-chat

---

# Что Проверять Перед Коммитом

```http
POST http://localhost:8000/auth/dev-login?phone=%2B79991234567
POST http://localhost:8000/auth/dev-login?phone=%2B79991234567
POST http://localhost:8000/private-chats/1/2
GET http://localhost:8000/users/1/chats
GET http://localhost:8000/chats/1/messages?user_id=1
GET http://localhost:8000/chats/1/messages?user_id=3
```

Ожидания:
- первый `dev-login` возвращает `created: true`
- второй `dev-login` с тем же телефоном возвращает `created: false`
- новый пользователь получает `display_name: null`
- список чатов содержит `peer_user_id`
- список чатов показывает `display_name`, если он есть, иначе `username`
- история для участника работает
- история для чужого пользователя возвращает `403`

Синтаксическая проверка:

```bash
./.venv/bin/python -m compileall app
```

---

# Важные Ограничения MVP

- SMS-auth пока не реализован
- JWT/session-auth пока не реализованы
- `user_id` в path/query/WebSocket пока приходит от клиента
- phone visibility/discoverability заложены как будущая идея, но в MVP выключены
- поиск по телефону не реализуется
- отображение телефона другим пользователям не реализуется
- `UUID/public_id` пока не вводим
- внутренний `int id` остается рабочим контрактом
- Redis / брокер сообщений пока не используются
- Docker / production deploy пока не делаем
- E2EE пока не делаем
- группы пока не делаем

---

# Backend Backlog

Ближайшее:
- добавить endpoint смены username
- добавить стабильные error codes вместо завязки клиента на текст ошибки
- позже заменить `user_id` из query/path/WebSocket на `current_user` из auth
- позже добавить SMS/OTP, rate limits и полноценный auth-flow
- позже вернуться к `UUID/public_id`, если потребуется внешний opaque identifier

Для iOS после закрытия ветки:
- использовать `POST /auth/dev-login?phone=...`
- модель `display_name` должна быть nullable
- подключить поиск по `username`
- создавать/открывать private chat
- загружать историю через `GET /chats/{chat_id}/messages?user_id=...`
- подключить отправку сообщений и WebSocket

Позже:
- хранение устройств
- offline-сценарии
- настройки видимости телефона
- настройки поиска по телефону
- тесты на API и WebSocket
- линтеры и форматирование
- Alembic migrations
- Docker и базовая инфраструктура
- Redis / broker для нескольких backend-инстансов
- E2EE

# Backend Prompt

Backend MVP чат-приложения с realtime-обменом по WebSocket.

Путь:
- `/Users/romansinenko/Desktop/prog/Chat/backend`

Текущий backend-статус:
- WebSocket-контракт отправки сообщений под iOS готов для следующего iOS-шага
- минимальный session-auth foundation для HTTP/WebSocket добавлен
- активный следующий шаг находится на стороне iOS: обновить HTTP-контракты под `Authorization` и подключить отправку через WebSocket

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

`POST /auth/dev-login`

Временная dev-ручка без SMS:
- принимает JSON body с телефоном
- проверяет телефон через `phonenumbers`
- приводит телефон к E.164
- если телефон уже есть в `user_phones`, возвращает существующего пользователя
- если телефона нет, создает нового пользователя
- новому пользователю backend генерирует временный username вида `user_a8f31c2d`
- `display_name = null`, профиль пользователь заполнит позже в Settings
- `is_username_custom = False`
- `phone_verified = False`
- возвращает `session_token` для защищенных HTTP-ручек и WebSocket

Body:

```json
{
  "phone": "+79991234567"
}
```

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
  "session_token": "plaintext_token_returned_once",
  "created": true
}
```

## Users

`GET /users/search?query=...`

Поиск:
- работает только по `username`
- `display_name` в поиске не используется
- поиск по телефону в MVP не реализуется
- требует `Authorization: Bearer <session_token>`
- исключает текущего пользователя из результатов поиска

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

`POST /private-chats`

Находит или создает private chat.
Текущий пользователь берется из `Authorization`, а `peer_user_id` приходит в JSON body.

Body:

```json
{
  "peer_user_id": 2
}
```

Возвращает:
- `id`
- `chat_type`
- `title`
- `peer_user_id`
- `created_at`
- `created`

`GET /users/me/chats`

Возвращает список чатов текущего пользователя из active session.

Для private chat:
- `display_name` строится через `app/services/peer_presentation.py`
- текущее правило: `peer_user.display_name` или `peer_user.username`
- `peer_user_id` равен id собеседника
- для self-chat `peer_user_id = null`

`GET /chats/{chat_id}`

Возвращает meta-информацию о чате и требует membership текущего пользователя.

`GET /chats/{chat_id}/messages?limit=50&offset=0`

Возвращает историю сообщений и требует membership текущего пользователя.

Если пользователь не участник чата, backend возвращает `403`.

---

# WebSocket

Текущий endpoint:

```text
WS /ws
```

Header:

```http
Authorization: Bearer <session_token>
```

Важно:
- WebSocket определяет пользователя по active session token
- `user_id` из URL больше не используется
- при revoked/expired session socket получает ошибку и закрывается

Целевой входящий формат отправки сообщения:

```json
{
  "type": "send_message",
  "client_message_id": "ios-local-id-123",
  "chat_id": 1,
  "to_user_id": 2,
  "text": "hello"
}
```

Поля:
- `type = "send_message"` — тип клиентского события
- `client_message_id` — локальный id сообщения на клиенте, нужен для связи optimistic UI и backend ack
- `chat_id` — id чата
- `to_user_id` — id получателя
- `text` — текст сообщения

Валидация текста:
- `text.strip()` не должен быть пустым
- максимальная длина для MVP: `4000` символов
- пустые сообщения и строки из пробелов не сохраняются

События сервера:
- `message`
- `system`
- `error`
- `message_ack`

Целевой `message_ack` отправителю после успешного сохранения:

```json
{
  "type": "message_ack",
  "client_message_id": "ios-local-id-123",
  "chat_id": 1,
  "message_id": 55,
  "status": "saved",
  "created_at": "2026-05-10T12:00:00Z"
}
```

Правило:
- `message_ack` отправляется всегда после сохранения сообщения
- `saved` означает, что backend принял и записал сообщение в БД
- `saved` не означает, что получатель уже получил или прочитал сообщение

Целевой `message` online-получателю:

```json
{
  "type": "message",
  "message": {
    "id": 55,
    "chat_id": 1,
    "sender_id": 2,
    "text": "hello",
    "message_type": "text",
    "created_at": "2026-05-10T12:00:00Z"
  }
}
```

Правило:
- `chat_id` обязателен, чтобы iOS мог обновить список чатов и поднять нужный чат наверх
- если получатель offline, это не ошибка сохранения
- offline recipient не должен превращать успешное сохранение в failed send
- delivered/read статусы будут отдельным будущим шагом
- offline delivery будет отдельным будущим шагом:
  - сейчас offline recipient не считается ошибкой, если сообщение сохранено
  - backend пока не досылает сохраненные сообщения при повторном WebSocket-подключении получателя
  - получатель увидит сообщение через загрузку истории
  - позже нужно спроектировать sync непрочитанных сообщений, unread counters и delivered/read statuses

WebSocket перед сохранением сообщения проверяет:
- пользователь существует
- чат существует
- отправитель состоит в чате
- получатель тоже состоит в этом чате

Self-chat:
- сообщение сохраняется
- сервер не дублирует его как входящее
- вместо этого отправителю отправляется `message_ack`

Logging/security:
- не логировать полный текст сообщений
- в логах допустимы metadata: `user_id`, `chat_id`, `message_id`, длина текста
- внешние ошибки должны быть стабильными кодами и не раскрывать лишние внутренние детали
- подробности можно писать только в server logs

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
- телефон принимается через JSON body
- выдача `session_token`
- отзыв старых active sessions при повторном login
- нормализация телефона через `phonenumbers`
- генерация временного username
- возврат существующего пользователя при повторном входе по телефону

## `routers/users.py`

- поиск пользователей по публичному custom username
- защищено через `Authorization: Bearer <session_token>`
- текущий пользователь исключается из результатов
- валидация username
- валидация display_name

## `routers/chats.py`

- chat meta
- history
- private chat get-or-create
- `POST /private-chats` принимает `peer_user_id` в JSON body
- текущий пользователь берется из active session
- `peer_user_id` в private chat response
- membership check для истории

## `routers/chat_list.py`

- список чатов пользователя через `GET /users/me/chats`
- текущий пользователь берется из active session
- `peer_user_id` в chat list response
- `display_name` для private chat строится через `get_peer_display_name`

## `services/peer_presentation.py`

- единая точка логики отображения собеседника
- текущее правило: `display_name`, если он есть, иначе `username`
- позже сюда можно добавить имя из телефонной книги и privacy-правила показа телефона

## `websocket.py`

- WebSocket endpoint `/ws`
- подключение требует `Authorization: Bearer <session_token>`
- активная session проверяется при подключении и перед каждым входящим сообщением
- прием JSON-сообщений
- сохранение сообщений
- membership checks
- recipient membership check
- всегда отправляет `message_ack` после успешного сохранения
- online-получателю отправляет полноценное `message` событие с `id`, `chat_id`, `sender_id`, `text`, `message_type`, `created_at`

---

# Что Проверять Перед Коммитом

```http
POST http://localhost:8000/auth/dev-login
GET http://localhost:8000/users/search?query=roman
POST http://localhost:8000/private-chats
GET http://localhost:8000/users/me/chats
GET http://localhost:8000/chats/1
GET http://localhost:8000/chats/1/messages?limit=50&offset=0
WS ws://localhost:8000/ws
```

Ожидания:
- первый `dev-login` возвращает `created: true`
- второй `dev-login` с тем же телефоном возвращает `created: false`
- новый пользователь получает `display_name: null`
- защищенные HTTP-ручки без токена возвращают `401`
- revoked/expired token возвращает `401`
- список чатов содержит `peer_user_id`
- список чатов показывает `display_name`, если он есть, иначе `username`
- история для участника работает
- история для чужого пользователя возвращает `403`
- WebSocket без токена возвращает `missing_token`
- WebSocket с revoked/expired token возвращает `invalid_token` или `session_inactive`

Синтаксическая проверка:

```bash
./.venv/bin/python -m compileall app
```

---

# Важные Ограничения MVP

- SMS-auth пока не реализован
- JWT пока не реализован
- session-auth foundation реализован через `user_sessions` и `Authorization: Bearer <session_token>`
- активна MVP-логика: один active session token на пользователя, новый login отзывает старые сессии
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

# Последний Завершенный Backend-Шаг

Сделано в `backend-websocket-message-contract-polish`:
- добавлен session-auth foundation через `user_sessions`
- `POST /auth/dev-login` возвращает `session_token`
- HTTP-ручки переведены на `Authorization: Bearer <session_token>`
- WebSocket переведен на `/ws` + `Authorization`
- входящий WebSocket event обновлен до `type = send_message`
- добавлен `client_message_id`
- текст валидируется: trim, не пустой, max 4000
- всегда отправляется `message_ack` после сохранения
- online-получателю отправляется полноценное `message` событие
- offline-получатель не считается ошибкой сохранения
- убрано логирование полного текста сообщений
- добавлены учебные комментарии в измененные backend-модули

---

# Backend Backlog

Ближайшее:
- добавить endpoint смены username
- добавить endpoint изменения display_name
- добавить logout/revoke текущей сессии
- добавить стабильные error codes вместо завязки клиента на текст ошибки
- позже добавить SMS/OTP, rate limits и полноценный auth-flow
- позже вернуться к `UUID/public_id`, если потребуется внешний opaque identifier

Для следующего iOS-шага:
- использовать `POST /auth/dev-login` с JSON body `{ "phone": "+79991703321" }`
- хранить `session_token` и передавать его в `Authorization: Bearer <session_token>`
- модель `display_name` должна быть nullable
- подключить поиск по `username`
- создавать/открывать private chat
- загружать историю через `GET /chats/{chat_id}/messages?limit=50&offset=0`
- подключить отправку сообщений и WebSocket

Позже:
- хранение устройств
- offline-сценарии
- offline delivery после повторного подключения WebSocket
- sync непрочитанных сообщений
- unread counters
- delivered/read statuses
- удаление чата должно быть per-user: если пользователь удалил чат у себя, чат пропадает только из его списка, но остается у второго участника, если второй его не удалял
- пустой private chat без сообщений не должен отображаться в списке чатов; желательно не сохранять его как полноценный чат до первого отправленного сообщения
- первое сообщение в новый private chat должно атомарно создать чат, добавить участников и сохранить сообщение, после чего `message_ack` должен вернуть реальный `chat_id`
- настройки видимости телефона
- настройки поиска по телефону
- smart search: `Elena` / `Елена`, `ё/е`, Unicode-normalization, пробелы, транслитерация и возможные опечатки
- anti-abuse/DDoS protection: rate limits для login, search, private chat creation, history refresh и WebSocket; лимиты по IP, user, session token и количеству соединений
- user agreement acceptance: хранить факт принятия пользовательского соглашения, версию и дату; соглашение должно быть доступно в Settings
- FAQ и first-run instruction как будущий продуктовый контент
- anti-spam temporary blocks за массовые сообщения неизвестным пользователям
- user reputation/rating: учитывать spam signals, блокировки, открытые данные, возраст аккаунта и нормальные переписки с контактами
- scam/spam warnings при сообщении от неизвестного, низкорейтингового или spam-suspect пользователя
- talk rooms / ephemeral spaces: сообщения или комнаты с ограниченным временем жизни, возможно зависящим от активности пользователей
- retention policy и scheduled cleanup job для старых revoked/expired `user_sessions`: хранение по сроку жизни или по количеству последних сессий на пользователя, например последние 20
- тесты на API и WebSocket
- линтеры и форматирование
- Alembic migrations
- Docker и базовая инфраструктура
- Redis / broker для нескольких backend-инстансов
- E2EE

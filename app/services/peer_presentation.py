from app.models import User


# Возвращает имя собеседника, которое можно показать текущему пользователю.
# Пока правило простое: display_name, если он есть, иначе username.
def get_peer_display_name(peer_user: User) -> str:
    return peer_user.display_name or peer_user.username

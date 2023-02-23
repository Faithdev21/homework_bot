class StatusError(Exception):
    """Статус кода отличный от 200."""


class MessageError(Exception):
    """Сообщение не было доставлено."""


class CriticalError(Exception):
    """Нет доступа к переменным окружения."""

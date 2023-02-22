class StatusError(Exception):
    """Статус кода отличный от 200."""
    pass


class MessageError(Exception):
    """Сообщение не было доставлено."""
    pass


class CriticalError(Exception):
    """Нет доступа к переменным окружения."""
    pass

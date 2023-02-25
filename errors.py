class StatusError(Exception):
    """Статус кода отличный от 200."""


class MessageError(Exception):
    """Сообщение не было доставлено."""


class UnsupportedStatusError(Exception):
    """Неподдерживаемый статус."""

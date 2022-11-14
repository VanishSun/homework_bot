class HomeworksKeyNotFoundException(Exception):
    """Ключ 'homework' отсутствует."""


class NotImplementedStatusException(Exception):
    """Неизвестный статус ДЗ в ответе API."""


class ServerError(Exception):
    """Не удовлетворительный ответ сервера."""


class StatusKeyError(KeyError):
    """Ответ API не содержит ключа 'status'."""


class NameKeyError(KeyError):
    """Ответ API не содержит ключа 'name'."""


class NotListTypeError(TypeError):
    """В ответ API по ключу попал не список.'"""

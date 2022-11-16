import logging
import os
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

from exceptions import (
    HomeworksKeyNotFoundException,
    NameKeyError,
    NotImplementedStatusException,
    NotListTypeError,
    ServerError, StatusKeyError
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACT_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - func: '
        '%(funcName)s - line %(lineno)d - %(message)s'
    )
    file_handler = RotatingFileHandler(
        'homework.log',
        maxBytes=5000000,
        backupCount=3
    )
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)


def send_message(bot, message):
    """Отправка сообщение пользователю через бота."""
    try:
        logger.info(f'Бот начал отправку telegram сообщения: {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Пользователю отправленно сообщение: {message}')
    except TelegramError as telegram_error:
        logger.error(f'Ошибка отправки telegram сообщения: {telegram_error}')


def get_api_answer(current_timestamp):
    """Получение API с сервера Яндекса."""
    timestamp = current_timestamp
    request_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}}
    response = requests.get(**request_params)
    if response.status_code != HTTPStatus.OK:
        raise ServerError(
            'Сбой при обращении к эндпойнту. Код ответа сервера: '
            f'{response.status_code}'
        )
    # Я тоже согласен, что это выглядит лишним, но тест
    # test_check_response_not_dict подкладывает mock в виде листа
    # и проверяет что на выходе словарь :) все чтобы голову сломать студенту
    return dict(response.json())


def check_response(response):
    """Проверка наличия ответа о статусе ДЗ."""
    # Борясь с тестом в строке 64 - я уверен, что пришел dict
    # Мне кажется еще раз проверять на dict - лишнее тут
    if 'homeworks' in response:
        homework = response.get('homeworks')
        if not isinstance(homework, list):
            raise NotListTypeError(
                'В ответ API по ключу попал не список.'
                f'Ответ API {homework}.'
            )
        return homework
    raise HomeworksKeyNotFoundException(
        'Отсутствует ключ "homeworks" в API.'
        f'Ответ API: {response}'
    )


def parse_status(homework):
    """Парсинг информации о статусе ДЗ."""
    # В реальности сюда должен прийти пустой или полный список
    # Все работы - это словари, лежащие в списке. Так API настроен.
    # Но вот тест test_parse_status подкидывает сюда словарь - с этим и борюсь
    # если словарь - то докидываю его в список нулевым элементом
    if isinstance(homework, dict):
        homework = [homework, ]
    if not homework:
        logger.debug('Отсутсвие обновленных статусов проверки ДЗ.')
        return None
    homework_name = homework[0].get('homework_name')
    homework_status = homework[0].get('status')
    if homework_status is None:
        raise StatusKeyError(
            'Ответ API не содержит ключа "status".'
            f'В ответ пришел словарь: {homework[0]}'
        )
    if homework_name is None:
        raise NameKeyError(
            'Ответ API не содержит ключа "name".'
            f'В ответ пришел словарь: {homework[0]}'
        )
    if homework_status in VERDICTS:
        verdict = VERDICTS[homework_status]
        return (
            f'Изменился статус проверки работы "{homework_name}". {verdict}'
        )
    raise NotImplementedStatusException(
        'Неизвестный статус ДЗ в ответе API.'
        f'Статус ДЗ на сервере: {homework_status}'
    )


def check_tokens():
    """Проверка наличия секретных токенов."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(
            'Программа принудительно остановлена. '
            'Отсутствует обязательная переменная окружения.'
        )
        exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    send_message(bot, 'Бот начал работу. Держитесь!!!')
    current_timestamp = int(time.time())
    previous_messages = {}
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            if message is not None:
                if message not in previous_messages:
                    send_message(bot, message)
        except Exception as error:
            logger.error(f'{error}')
            message = f'Сбой в работе программы: {error}'
            if message not in previous_messages:
                send_message(bot, message)
        finally:
            previous_messages[message] = True
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

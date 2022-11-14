import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

from exceptions import (HomeworksKeyNotFoundException,
                        NotImplementedStatusException,
                        ServerError,
                        StatusKeyError,
                        NameKeyError,
                        NotListTypeError
                        )

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACT_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Пользователю отправленно сообщение: {message}')
    except TelegramError as telegram_error:
        logger.error(f'Ошибка отправки telegram сообщения: {telegram_error}')


def get_api_answer(current_timestamp):
    """Получение API с сервера Яндекса."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code == 505:
        logger.error('Ошибка 505: cервер недоступен.')
        raise ServerError('Ошибка 505: cервер недоступен.')
    if homework_statuses.status_code != 200:
        logger.error('Сбой при обращении к эндпойнту.')
        raise ServerError('Сбой при обращении к эндпойнту.')
    response = dict(homework_statuses.json())
    return response


def check_response(response):
    """Проверка наличия ответа о статусе ДЗ."""
    if 'homeworks' in response.keys():
        homework = response.get('homeworks')
        if not isinstance(homework, list):
            raise NotListTypeError('В ответ API по ключу попал не список.')
        return homework
    logger.error('Отсутствует ключ "homeworks" в API.')
    raise HomeworksKeyNotFoundException('Отсутствует ключ "homeworks" в API.')


def parse_status(homework):
    """Парсинг информации о статусе ДЗ."""
    if isinstance(homework, dict):
        logger.info('Словарь в ответе API.')
        homework = [homework, ]
    if homework == []:
        logger.debug('Отсутсвие обновленных статусов проверки ДЗ.')
        return None
    homework_name = homework[0].get('homework_name')
    homework_status = homework[0].get('status')
    if homework_status is None:
        logger.error('Ответ API не содержит ключа "status".')
        raise StatusKeyError('Ответ API не содержит ключа "status".')
    if homework_name is None:
        logger.error('Ответ API не содержит ключа "name".')
        raise NameKeyError('Ответ API не содержит ключа "name".')
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
        return (f'Изменился статус проверки работы "{homework_name}".'
                f'{verdict}')
    logger.error('Неизвестный статус ДЗ в ответе API.')
    raise NotImplementedStatusException('Неизвестный статус ДЗ в ответе API.')


def check_tokens():
    """Проверка наличия секретных токенов."""
    error_msg = (
        'Программа принудительно остановлена. '
        'Отсутствует обязательная переменная окружения:')
    tokens_bool_flag = True
    if PRACTICUM_TOKEN is None:
        tokens_bool_flag = False
        logger.critical(f'{error_msg} PRACTICUM_TOKEN')
    if TELEGRAM_TOKEN is None:
        tokens_bool_flag = False
        logger.critical(f'{error_msg} TELEGRAM_TOKEN')
    if TELEGRAM_CHAT_ID is None:
        tokens_bool_flag = False
        logger.critical(f'{error_msg} TELEGRAM_CHAT_ID')
    return tokens_bool_flag


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    send_message(bot, 'Бот начал работу. Держитесь!!!')
    current_timestamp = int(time.time())
    error_1 = None
    error_queue = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = int(time.time())
            homework = check_response(response)
            message = parse_status(homework)
            if message is not None:
                send_message(bot, message)
            error_queue = ''
            time.sleep(RETRY_TIME)

        except Exception as error:
            if error_queue != error_1:
                error_1 = f'Сбой в работе программы: {error}'
                send_message(bot, error_1)
            error_queue = error_1
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

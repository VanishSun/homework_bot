import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from telegram import Bot

from exceptions import (HomeworksKeyNotFoundException,
                        NotImplementedStatusException,
                        ServerError,
                        TokensNotImplementedException,
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
    except Exception:
        logger.error('Ошибка отправки сообщения пользователю.')


def get_api_answer(current_timestamp):
    """Получение API с сервера Яндекса."""
    timestamp = current_timestamp
    params = {'from_date': timestamp }
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code == 505:
        logger.error('Ошибка 500: cервер недоступен.')
        raise ServerError('Ошибка 500: cервер недоступен.')
    if homework_statuses.status_code != 200:
        logger.error('Сбой при обращении к эндпойнту.')
        raise ServerError('Сбой при обращении к эндпойнту.')
    response = dict(homework_statuses.json())
    return response


def check_response(response):
    """Проверка наличия ответа о статусе ДЗ."""
    if response.get('homeworks'):
        homework = response.get('homeworks')
        if homework is dict:
            homework_list: list
            homework_list[0] = homework
            return homework_list
        return homework
    logger.error('Отсутствует ключ "homeworks" в API.')
    if response is dict:
        return None
    raise HomeworksKeyNotFoundException('Токены недоступны')


def parse_status(homework):
    """Парсинг информации о статусе ДЗ."""
    if len(homework) > 0:
        homework_name = homework[0].get('homework_name')
        homework_status = homework[0].get('status')

        if homework_status in HOMEWORK_STATUSES:
            verdict = homework_status
            return (f'Изменился статус проверки работы "{homework_name}".'
                    f'{verdict}')
        logger.error('Неизвестный статус ДЗ в ответе API.')
        raise NotImplementedStatusException(
            'Неизвестный статус ДЗ в ответе API.'
        )
    logger.debug('Отсутсвие обновленных статусов проверки ДЗ.')
    return None


def check_tokens():
    """Проверка наличия секретных токенов."""
    if PRACTICUM_TOKEN:
        if TELEGRAM_TOKEN:
            if TELEGRAM_CHAT_ID:
                return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    check_status = check_tokens()
    if check_status is False:
        logger.critical('отсутствует обязательная переменная окружения')
        raise TokensNotImplementedException('Токены недоступны')

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    message1 = None
    message_queue = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            if message is not None:
                send_message(bot, message)
            message_queue = ''
            time.sleep(RETRY_TIME)

        except Exception as error:
            if message_queue != message1:
                message1 = f'Сбой в работе программы: {error}'
                send_message(bot, message1)
            message_queue = message1
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

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
    ServerError,
    StatusKeyError
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACT_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot: Bot, message: str) -> None:
    """Отправка сообщение пользователю через бота."""
    try:
        logger.info(f'Бот начал отправку telegram сообщения: {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramError as telegram_error:
        logger.error(f'Ошибка отправки telegram сообщения: {telegram_error}')
    else:
        logger.info(f'Пользователю отправленно сообщение: {message}')


def get_api_answer(current_timestamp: int) -> dict:
    """Получение API с сервера Яндекса."""
    timestamp = current_timestamp
    request_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}}
    response = requests.get(**request_params)
    if response.status_code != HTTPStatus.OK:
        raise ServerError(
            'Сбой при обращении к эндпойнту. Ответ сервера: '
            f'{response.status_code}. Reason: {response.reason}. '
            f'Requested Params: {request_params}.'
        )
    return response.json()


def check_response(response: dict) -> list:
    """Проверка наличия ответа о статусе ДЗ."""
    if isinstance(response, dict):
        if 'homeworks' in response:
            new_homework = response.get('homeworks')
            if not isinstance(new_homework, list):
                raise NotListTypeError(
                    'В ответ API по ключу попал не список.'
                    f'Ответ API: {new_homework}.'
                )
            return new_homework
        raise HomeworksKeyNotFoundException(
            'Отсутствует ключ "homeworks" в API.'
            f'Ответ API: {response}'
        )
    raise NotListTypeError(
        'В ответ API попал список.'
        f'Ответ API: {response}.'
    )


def parse_status(homework: dict) -> str:
    """Парсинг информации о статусе ДЗ."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status is None:
        raise StatusKeyError(
            'Ответ API не содержит ключа "status".'
            f'В ответ пришел словарь: {homework}'
        )
    if homework_name is None:
        raise NameKeyError(
            'Ответ API не содержит ключа "name".'
            f'В ответ пришел словарь: {homework}'
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


def check_tokens() -> bool:
    """Проверка наличия секретных токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


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
            new_homework = check_response(response)
            if not new_homework:
                message = 'Отсутсвует обновление статуса проверки ДЗ.'
            else:
                message = parse_status(new_homework[0])
            if message not in previous_messages:
                send_message(bot, message)
        except Exception as error:
            logger.error(f'{error}')
            message = f'Сбой в работе программы: {error}'
            if message not in previous_messages:
                send_message(bot, message)
        finally:
            previous_messages.clear()
            previous_messages[message] = True
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
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

    main()

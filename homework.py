import logging
import os
import sys
import time
from http import HTTPStatus
from typing import Optional

import requests
import telegram
from dotenv import load_dotenv
from requests.exceptions import RequestException
from telegram import TelegramError
from telegram.ext import Updater

from errors import MessageError, StatusError, UnsupportedStatusError

load_dotenv()

PRACTICUM_TOKEN: Optional[str] = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: Optional[str] = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: Optional[str] = os.getenv('TELEGRAM_CHAT_ID')
updater = Updater(token=os.getenv('TELEGRAM_TOKEN'))

RETRY_PERIOD: float = 600
ENDPOINT: Optional[str] = os.getenv('ENDPOINT')
HEADERS: dict = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS: dict = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
CRITICAL_ERROR: str = 'Ошибка доступа к переменным окружения.'
RESPONSE_TYPE: str = 'response должен быть типа dict.'
HOMEWORK_TYPE: str = 'homework должен быть типа list.'
SEC_IN_DAY: int = 86400


def check_tokens() -> bool:
    """Проверка доступности переменных окружения."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID]) or (
        logging.critical(CRITICAL_ERROR))


def send_message(bot: telegram.bot.Bot, message: str) -> None:
    """Функция отправки сообщения."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logging.debug(f'Произошла удачная отправка сообщения {message}.')
    except TelegramError as error:
        error_message: str = (
            'Произошел сбой при отправке сообщения: {}.'.format(error))
        logging.error(error_message)
        raise MessageError(error_message)


def get_api_answer(timestamp: float) -> dict:
    """Делает запрос к эндпоинту."""
    payload: dict = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=payload)
    except RequestException as error:
        logging.error(f'Ошибка в запросе к API: {error}')
        raise ConnectionError(error)
    if response.status_code != HTTPStatus.OK:
        raise StatusError(
            f'Ожидаемый код статуса 200, но был получен {response.status_code}'
        )
    api_answer: dict = response.json()
    return api_answer


def check_response(response: dict) -> list:
    """Проверка ответа API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error(RESPONSE_TYPE)
        raise TypeError(RESPONSE_TYPE)
    if 'homeworks' not in response:
        logging.error('В полученном словаре нет ключа homeworks.')

    if not isinstance(response.get('homeworks'), list):
        logging.error(HOMEWORK_TYPE)
        raise TypeError(HOMEWORK_TYPE)
    return response['homeworks']


def parse_status(homework: dict) -> str:
    """Получение информации о конкретной домашней работе."""
    homework_name: str = homework.get('homework_name')
    status: str = homework.get('status')
    verdict: str = HOMEWORK_VERDICTS.get(status)
    if 'homework_name' not in homework:
        logging.error('В API домашней работы нет ключа homework_name')
        raise KeyError('Отсутствует ключ homework_name')
    if status not in HOMEWORK_VERDICTS:
        status_not_found: str = (
            'В базовом списке нет статуса {}.'.format(status))
        logging.error(status_not_found)
        raise UnsupportedStatusError(status_not_found)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit(
            'Работа программы прервана по причине'
            'отсутствия доступа к переменным окружения.'
        )
    bot: telegram.bot.Bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp: int = int(time.time()) - SEC_IN_DAY
    message: str = ''
    previous_message: str = ''
    while True:
        try:
            response: dict = get_api_answer(timestamp)
            homeworks: list = check_response(response)
            try:
                message: str = parse_status(homeworks[0])
            except IndexError:
                logging.info(
                    'Обновления отсутствуют.'
                    'Программа работает корректно.'
                )
            if homeworks and message != previous_message:
                send_message(bot, message)
                previous_message: str = message
            timestamp: int = int(time.time()) - SEC_IN_DAY
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s, %(name)s, %(levelname)s, %(message)s',
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ])
    main()

import logging
import os
import sys
import time
from typing import Optional

import requests
import telegram
from dotenv import load_dotenv
from requests.exceptions import RequestException
from telegram.ext import Updater

from errors import CriticalError, MessageError, StatusError

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


def check_tokens() -> bool:
    """Проверка доступности переменных окружения."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID]) or (
        logging.critical('Ошибка доступа к переменным окружения.'))


def send_message(bot, message: str) -> None:
    """Функция отправки сообщения."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logging.debug(f'Произошла удачная отправка сообщения {message}.')
    except Exception as error:
        logging.error(f'Произошел сбой при отправке сообщения: {error}.')
        raise MessageError(f'Произошел сбой при отправке сообщения {error}.')


def get_api_answer(timestamp: float) -> dict:
    """Делает запрос к эндпоинту."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=payload)
    except RequestException as error:
        logging.error(f'Ошибка в запросе к API: {error}')
        raise ConnectionError(error)
    if response.status_code != 200:
        raise StatusError(
            f'Ожидаемый код статуса 200, но был получен {response.status_code}'
        )
    api_answer: dict = response.json()
    return api_answer


def check_response(response: dict) -> list:
    """Проверка ответа API на соответствие документации."""
    if type(response) is not dict:
        logging.error('response должен быть типа типа dict.')
        raise TypeError('response должен быть типа типа dict.')
    if 'homeworks' not in response:
        logging.error('В полученном словаре нет ключа homeworks.')

    if type(response.get('homeworks')) is not list:
        logging.error('homeworks должен быть типа list.')
        raise TypeError('homeworks должен быть типа list.')
    return response.get('homeworks')


def parse_status(homework: dict) -> str:
    """Получение информации о конкретной домашней работе."""
    homework_name: str = homework.get('homework_name')
    status: str = homework.get('status')
    verdict: str = HOMEWORK_VERDICTS.get(status)
    if 'homework_name' not in homework:
        logging.error('В API домашней работы нет ключа homework_name')
        raise KeyError('Отсутствует ключ homework_name')
    if status not in HOMEWORK_VERDICTS:
        logging.error(f'В базовом списке нет статуса {status}')
        raise TypeError('TypeError')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        raise CriticalError('Ошибка доступа к переменным окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp: int = int(time.time())
    message: str = ''
    previous_message: str = ''
    while True:
        try:
            response: dict = get_api_answer(timestamp)
            homeworks: list = check_response(response)
            message: str = parse_status(homeworks[0])
            if homeworks and message != previous_message:
                send_message(bot, message)
                previous_message: str = message
            timestamp: int = int(time.time())
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

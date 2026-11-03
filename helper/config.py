from runtime_config import required_env
from aiogram import types
import datetime

TOKEN = required_env('TELEGRAM_BOT_TOKEN')

INVOICE_TOKEN = required_env('TELEGRAM_INVOICE_TOKEN')
PRICE = types.LabeledPrice(label='Ну купи пожалуйста!!!', amount=9900)

ADMIN = [235519518]

CHANNELS = {'pukton': -1001619177503, 'testo': -1001763723294}
CHANNEL_IDS = [-1001619177503, -1001763723294]

CHATS = {'pukton': -1001800983569, 'testo': -1001882385234}
CHAT_IDS = [-1001800983569, -1001882385234]

DEFAULT_DATE = datetime.date(1, 1, 1)
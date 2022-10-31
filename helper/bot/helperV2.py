from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, ChatType
from aiogram.utils import executor
from aiogram.dispatcher.filters import IsReplyFilter, IDFilter
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ContentType
from random import choice
import sqlite3
import datetime
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from yookassa import Payment

from config import *


logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
scheduler = AsyncIOScheduler()
scheduler.start()


rates = []
for i in range(1, 6):
    i = str(i)
    rates.append(InlineKeyboardButton(i, callback_data=i))

role = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton('пуктон', callback_data='pukton'), InlineKeyboardButton('тесто', callback_data='testo'))
rate_kb = InlineKeyboardMarkup(row_width=3).add(*rates)
rate_kb.add(InlineKeyboardButton('Пропустить', callback_data='no_rate'))


class Form(StatesGroup):
    question = State() 


def db():
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (user INTEGER, paid INTEGER DEFAULT 0, role TEXT DEFAULT "No", expiration DATE DEFAULT NULL)')
    cur.execute('CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY, role TEXT, text TEXT, user INTEGER, helper TEXT, status INTEGER DEFAULT 0, rating INTEGER DEFAULT 0, msg INTEGER)')
    cur.execute('CREATE TABLE IF NOT EXISTS site (id TEXT, username TEXT)')
    con.commit()
    con.close()

def get_type(message):
    entities = message.entities or message.caption_entities
    if not entities or entities[-1].type != "hashtag":
        return None, "No hashtags found"
    hashtag = entities[-1].get_text(message.text or message.caption)
    return hashtag[3:], None

async def setchbf():
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    cur.execute('UPDATE users SET paid = 0 WHERE expiration < ?', (datetime.date.today(),))
    con.commit()
    data = cur.execute('SELECT id, username FROM site').fetchall()
    for i in data:
        payment = Payment.find_one(i[0])
        if payment.status == 'canceled':
            cur.execute('DELETE FROM site WHERE id = ?', (i[0],))
    con.close()

def set_false_job():
    scheduler.add_job(setchbf, 'interval', days=1)


@dp.message_handler(commands='start')
async def start(message: types.Message):
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT user FROM users WHERE user = ?', (message.from_user.id,)).fetchall()
    if not data:
        cur.execute('INSERT INTO users (user, expiration) VALUES (?, ?)', (message.from_user.id, DEFAULT_DATE,))
        con.commit()
        con.close()
        await message.answer("Select your role", reply_markup=role)
        return
    con.close()
    await message.answer('Я думаю вам нужна помощь, используйте команду /help')

@dp.message_handler(commands='help')
async def help(message: types.Message):
    await message.answer('/start - запустить бота\n\
/subscription - показать подписку\n\
/change_role или /chr - сменить роль\n\
/question или /q - задать вопрос'
    )

@dp.message_handler(commands='subscription')
async def subscription(message: types.Message):
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT user, paid, expiration FROM users WHERE user = ?', (message.from_user.id,)).fetchone()
    con.close()
    if not data:
        await message.answer('Вы не зарегистрированы, испльзуйте команду /start')
        return

    if data[2] == DEFAULT_DATE:
        await message.answer('У вас нету подписки')

    text = 'Пожалуйста приобретите подписку используя команду /buy, потому что ваша подписка закончилась в: ' if data[1] == 0 else 'Ваша подписка закончится в: '
    text += str(data[2])

    await message.answer(text)

@dp.message_handler(commands=['change_role', 'chr'])
async def change_role(message: types.Message):
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT user FROM users WHERE user = ?', (message.from_user.id,)).fetchall()
    con.close()
    if not data:
        await message.answer('Вы не зарегистрированы, испльзуйте команду /start')
        return
    await message.answer("Выберите свою роль", reply_markup=role)

@dp.callback_query_handler(Text(equals='pukton'))
async def pukton(call: types.CallbackQuery):
    await call.answer()
    await bot.delete_message(call.from_user.id, call.message.message_id)
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT user FROM users WHERE user = ?', (call.from_user.id,)).fetchall()
    if not data:
        await bot.send_message(call.from_user.id, 'Вы не зарегистрированы, испльзуйте команду /start')
        con.close()
        return
    cur.execute('UPDATE users SET role = ? WHERE user = ?', ('pukton', call.from_user.id,))
    con.commit()
    con.close()
    await bot.send_message(call.from_user.id, 'Теперь ваша роль пуктон, вы можете задать вопрос используя команду /question')

@dp.callback_query_handler(Text(equals='testo'))
async def testo(call: types.CallbackQuery):
    await call.answer()
    await bot.delete_message(call.from_user.id, call.message.message_id)
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT user FROM users WHERE user = ?', (call.from_user.id,)).fetchall()
    if not data:
        await bot.send_message(call.from_user.id, 'Вы не зарегистрированы, испльзуйте команду /start')
        con.close()
        return
    cur.execute('UPDATE users SET role = ? WHERE user = ?', ('testo', call.from_user.id,))
    con.commit()
    con.close()
    await bot.send_message(call.from_user.id, 'Теперь ваша роль тесто, вы можете задать вопрос используя команду /question')

@dp.message_handler(IsReplyFilter(is_reply=True), IDFilter(chat_id=CHAT_IDS), commands=['answerer', 'a'])
async def set_helper(message: types.Message):
    id, err = get_type(message.reply_to_message)
    if id is None:
        print(err)
        return
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT id, user, status FROM questions WHERE id = ?', (int(id),)).fetchone()
    if not data:
        await message.answer('Вопрос не найден')
        con.close()
        return
    if data[2] == 1 or data[2] == 2:
        await message.answer('Вопрос закрыт')
        con.close()
        return
    
    args = message.get_args()
    if not args:
        nick = message.from_user.username if message.from_user.username is not None else message.from_user.id
        cur.execute('UPDATE questions SET helper = ? WHERE id = ?', (nick, int(id),))
    else:
        cur.execute('UPDATE questions SET helper = ? WHERE id = ?', (args, int(id),))
    con.commit()
    con.close()
    await message.reply('Отвечающий установлен')

@dp.message_handler(IsReplyFilter(is_reply=True), IDFilter(chat_id=CHAT_IDS), commands=['close', 'c'])
async def close_question(message: types.Message):
    id, err = get_type(message.reply_to_message)
    if id is None:
        await message.answer(err)
        return
    
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT id, user, status FROM questions WHERE id = ?', (int(id),)).fetchone()
    user = data[1]

    if not data:
        await message.answer('Вопрос не найден')
        con.close()
        return
    
    if data[2] == 1 or data[2] == 2:
        await message.answer('Вопрос закрыт')
        con.close()
        return
    
    cur.execute('UPDATE questions SET status = ? WHERE id = ?', (2, int(id),))
    con.commit()
    con.close()
    await message.reply('Вы закрыли этот вопрос')
    await bot.send_message(user, f'Оцените нас от 1 до 5', reply_markup=rate_kb)

@dp.message_handler(IsReplyFilter(is_reply=True), IDFilter(chat_id=CHAT_IDS), commands=['no_rate_close', 'nrc'])
async def close_question_no_rate(message: types.Message):
    id, err = get_type(message.reply_to_message)
    if id is None:
        await message.answer(err)
        return
    
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT id, user, status FROM questions WHERE id = ?', (int(id),)).fetchone()
    user = data[1]

    if not data:
        await message.answer('Вопрос не найден')
        con.close()
        return
    
    if data[2] == 1 or data[2] == 2:
        await message.answer('Вопрос закрыт')
        con.close()
        return
    
    cur.execute('UPDATE questions SET status = ? WHERE id = ?', (1, int(id),))
    con.commit()
    con.close()
    await message.reply('Вы закрыли вопрос без рейтинга')

@dp.message_handler(IDFilter(chat_id=CHAT_IDS), commands=['stats'])
async def question_stats(message: types.Message):
    chat = 'pukton' if message.chat.id == -1001800983569 else 'testo' if message.chat.id -1001882385234 else None
    chats = {'pukton': 1800983569, 'testo': 1882385234}
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    no_help = cur.execute('SELECT id, helper, msg FROM questions WHERE status = ? AND role = ? AND helper IS NULL', (0, chat)).fetchall()
    helping = cur.execute('SELECT id, helper, msg FROM questions WHERE status = ? AND role = ? AND helper IS NOT NULL', (0, chat)).fetchall()
    con.close()
    txt = ''
    
    if len(no_help) < 1 and len(helping) < 1:
        await message.reply('Не нашлось открытых вопросов по этой роли')
        return
    
    if len(no_help) > 0:
        txt += 'Свободные вопросы:\n'
        for n, i in enumerate(no_help, 1):
            txt += f'{n}. id: {i[0]}; ссылка: t.me/c/{chats[chat]}/{i[2]}\n'
    
    if len(helping) > 0:
        txt += '\nЗанятые вопросы:\n'
        for n, i in enumerate(helping, 1):
            txt += f'{n}. id: {i[0]}; отвечающий: {i[1]}; ссылка: t.me/c/{chats[chat]}/{i[2]}\n'
    
    await message.reply(txt)

@dp.callback_query_handler(Text(equals=['1', '2', '3', '4', '5', 'no_rate']))
async def rate(call: types.CallbackQuery):
    await call.answer()
    await bot.delete_message(call.from_user.id, call.message.message_id)
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    quest = cur.execute('SELECT id FROM questions WHERE user = ? AND status = ?', (call.from_user.id, 2,)).fetchone()
    
    if not quest:
        await bot.send_message(call.from_user.id, 'Вопрос не найден')
        con.close()
        return
    
    data = cur.execute('SELECT msg, role FROM questions WHERE id = ?', (quest[0],)).fetchone()
    
    if call.data != 'no_rate':
        cur.execute('UPDATE questions SET rating = ? WHERE id = ?', (int(call.data), quest[0],))
        await bot.send_message(CHATS[data[1]], f'Пользователь оценил ответ на {call.data}', reply_to_message_id=data[0])
    
    if call.data == 'no_rate':
        await bot.send_message(CHATS[data[1]], 'Пользователь предпочел не оценивать', reply_to_message_id=data[0])
    
    cur.execute('UPDATE questions SET status = ? WHERE id = ?', (1, quest[0],))
    con.commit()
    con.close()
    await bot.send_message(call.from_user.id, 'Спасибо!')

@dp.message_handler(chat_type=ChatType.PRIVATE, content_types='any')
async def send_msg(message: types.Message):
    username = message.from_user.username.lower()

    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data3 = cur.execute('SELECT paid FROM users WHERE user = ?', (message.from_user.id,)).fetchone()
    if data3[0] == 0:
        data2 = cur.execute('SELECT id, username FROM site WHERE username = ?', (username,)).fetchall()
        if not data2:
            await message.answer('Payment not found')
            con.close()
            return

        payment = Payment.find_one(data2[0][0])

        if payment.status == 'succeeded':
            to_exp = datetime.date.today() + datetime.timedelta(days=30)
    
            cur.execute('UPDATE users SET expiration = ? WHERE user = ?', (to_exp, message.from_user.id,))
            cur.execute('UPDATE users SET paid = ? WHERE user = ?', (1, message.from_user.id,))
            cur.execute('DELETE FROM site WHERE id = ?', (data2[0][0],))
            con.commit()

            await bot.send_message(message.chat.id, 'Вы успешно приобрели подписку\nВы можете посмотреть подписку используя команду /subscription')
    con.close()

    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT role, msg FROM questions WHERE user = ? AND status = ?', (message.from_user.id, 0,)).fetchone()
    data1 = cur.execute('SELECT user, role, paid FROM users WHERE user = ?', (message.from_user.id,)).fetchone()
    rated_quest = cur.execute('SELECT id FROM questions WHERE user = ? AND status = ?', (message.from_user.id, 2,)).fetchone()
    #open_quest = cur.execute('SELECT id FROM questions WHERE user = ? AND status = ?', (message.from_user.id, 0,)).fetchone()
    con.close()

    if not data1:
        await bot.send_message(message.from_user.id, 'Вы не зарегистрированы, испльзуйте команду /start')
        return
    
    if data1[1] == "No":
        await bot.send_message(message.from_user.id, 'У вас нету роли, установите его с помощью команды /change_role')
        return
    
    if data1[2] == 0:
        await message.answer('Купите подписку используя команду /buy, чтобы задавать вопросы')
        return
    
    if rated_quest:
        await message.answer(f'Перед тем как задать вопрос, пожалуйста оцените нас от 1 до 5, если же вы не хотите оценивать, то просто пропустите', reply_markup=rate_kb)
        return

    if not data:
        text = message.text or message.caption
        con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        cur = con.cursor()
        data = cur.execute('SELECT role FROM users WHERE user = ?', (message.from_user.id,)).fetchone()
        cur.execute('INSERT INTO questions (role, text, user, helper) VALUES (?, ?, ?, NULL) RETURNING id', (data[0], text, message.from_user.id))
        row = cur.fetchone()
        id = row[0] if row else None
        username =  '@'+message.from_user.username if message.from_user.username is not None else 'нету юзернейма'
        txt = f'Новый вопрос от {username}\n{text}\n#id{id}'
        if message.content_type == 'photo' or message.content_type == 'video':
            await message.copy_to(CHANNELS[data[0]], caption=txt)
        else:
            await bot.send_message(CHANNELS[data[0]], txt)
        await message.answer(f'Вы можете общаться с теми кто отвечает, просто пришлите мне что-то, и я перешлю это им')
        con.commit()
        con.close()

        return

    await message.copy_to(CHATS[data[0]], reply_to_message_id=data[1])

@dp.message_handler(IDFilter(chat_id=CHAT_IDS), IsReplyFilter(is_reply=True), content_types='any')
async def answer_question(message: types.Message):
    id, err = get_type(message.reply_to_message)
    if id is None:
        await message.answer(err)
        return
    
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT id, user, status FROM questions WHERE id = ?', (int(id),)).fetchone()
    con.close()

    if not data:
        await message.answer('Вопрос не найден')
        return
    
    if data[2] == 1 or data[2] == 2:
        await message.answer('Вопрос закрыт')
        return
    
    await message.copy_to(data[1])

@dp.message_handler(IDFilter(chat_id=CHAT_IDS), content_types='any')
async def set_msg_id(message: types.Message):
    if message.from_user.id == 777000 and message.sender_chat.id in CHANNEL_IDS:
        id, err = get_type(message)
        if id is None:
            print(err)
            return
        
        con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        cur = con.cursor()
        cur.execute('UPDATE questions SET msg = ? WHERE id = ?', (message.message_id, int(id),))
        con.commit()
        con.close()


if __name__ == '__main__':
    db()
    set_false_job()
    executor.start_polling(dp, skip_updates=True)
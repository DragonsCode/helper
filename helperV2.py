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
import asyncio
import json
import requests
import datetime
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler


INVOICE_TOKEN = '381764678:TEST:41002'
ADMIN = [235519518]
CHANNELS = {'pukton': -1001619177503, 'testo': -1001763723294}
CHANNEL_IDS = [-1001619177503, -1001763723294]
CHATS = {'pukton': -1001800983569, 'testo': -1001882385234}
CHAT_IDS = [-1001800983569, -1001882385234]
DEFAULT_DATE = datetime.date(1, 1, 1)
PRICE = types.LabeledPrice(label='Come on, buy it!', amount=9900)


logging.basicConfig(level=logging.INFO)
bot = Bot(token='1682322424:AAEdZRXr0FKSdeqrkG5h4zuHNTZnkuveh_o')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
scheduler = AsyncIOScheduler()
scheduler.start()


rates = []
for i in range(1, 6):
    i = str(i)
    rates.append(InlineKeyboardButton(i, callback_data=i))

role = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton('pukton', callback_data='pukton'), InlineKeyboardButton('testo', callback_data='testo'))
rate_kb = InlineKeyboardMarkup(row_width=3).add(*rates)
rate_kb.add(InlineKeyboardButton('Skip', callback_data='no_rate'))


class Form(StatesGroup):
    question = State() 


def db():
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (user INTEGER, paid INTEGER DEFAULT 0, role TEXT DEFAULT "No", expiration DATE DEFAULT NULL)')
    cur.execute('CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY, role TEXT, text TEXT, user INTEGER, helper TEXT, status INTEGER DEFAULT 0, rating INTEGER DEFAULT 0, msg INTEGER)')
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
    cur.execute('UPDATE users SET paid = 0 WHERE expiration < ?', (datetime.date.today()))
    con.commit()
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
    await message.answer('I think you need some /help')

@dp.message_handler(commands='help')
async def help(message: types.Message):
    await message.answer('/start - start this bot\n\
/buy - buy a full version of bot\n\
/subscription - show your subscription\n\
/change_role or /chr - change your role\n\
/question or /q - ask a question'
    )

@dp.message_handler(commands=['buy'])
async def process_buy_command(message: types.Message):
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT user, paid FROM users WHERE user = ?', (message.from_user.id,)).fetchone()
    con.close()
    if data[1] == 1:
        await message.answer('You already have /subscription')
        return
    if INVOICE_TOKEN.split(':')[1] == 'TEST':
        await bot.send_message(message.chat.id, 'This is a test payment, use this card: `1111 1111 1111 1026`, CVC 000, 12/22')
    await bot.send_invoice(
        message.chat.id,
        title='GIVE ME YOUR MONEY',
        description='JUST BUY IT',
        provider_token=INVOICE_TOKEN,
        currency='rub',
        is_flexible=False,  # True если конечная цена зависит от способа доставки
        prices=[PRICE],
        start_parameter='full-bot',
        payload='some-invoice-payload-for-our-internal-use'
    )

@dp.pre_checkout_query_handler(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: types.Message):
    print('successful_payment:')
    pmnt = message.successful_payment.to_python()
    for key, val in pmnt.items():
        print(f'{key} = {val}')
    
    to_exp = datetime.date.today() + datetime.timedelta(days=1)
    
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    cur.execute('UPDATE users SET expiration = ? WHERE user = ?', (to_exp, message.from_user.id,))
    cur.execute('UPDATE users SET paid = ? WHERE user = ?', (1, message.from_user.id,))
    con.commit()
    con.close()

    await bot.send_message(
        message.chat.id,
        'You have successfully purcheased full version of this bot! `{total_amount} {currency}`\nYou can see your /subscription'.format(
            total_amount=message.successful_payment.total_amount // 100,
            currency=message.successful_payment.currency
        )
    )

@dp.message_handler(commands='subscription')
async def subscription(message: types.Message):
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT user, paid, expiration FROM users WHERE user = ?', (message.from_user.id,)).fetchone()
    con.close()
    if not data:
        await message.answer('You are not registered yet, use /start command')
        return

    if data[2] == DEFAULT_DATE:
        await message.answer('You do not have purchuased a subscription')

    text = 'Please /buy subscription, because your subscription is expired in: ' if data[1] == 0 else 'Your subscription expires in: '
    text += str(data[2])

    await message.answer(text)

@dp.message_handler(commands=['change_role', 'chr'])
async def change_role(message: types.Message):
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT user FROM users WHERE user = ?', (message.from_user.id,)).fetchall()
    con.close()
    if not data:
        await message.answer('You are not registered yet, use /start command')
        return
    await message.answer("Select your role", reply_markup=role)

@dp.callback_query_handler(Text(equals='pukton'))
async def pukton(call: types.CallbackQuery):
    await call.answer()
    await bot.delete_message(call.from_user.id, call.message.message_id)
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT user FROM users WHERE user = ?', (call.from_user.id,)).fetchall()
    if not data:
        await bot.send_message(call.from_user.id, 'You are not registered yet, use /start command')
        con.close()
        return
    cur.execute('UPDATE users SET role = ? WHERE user = ?', ('pukton', call.from_user.id,))
    con.commit()
    con.close()
    await bot.send_message(call.from_user.id, 'Now your role is pukton, your questions will be redirected to puktoners, use /question command in order to ask something')

@dp.callback_query_handler(Text(equals='testo'))
async def testo(call: types.CallbackQuery):
    await call.answer()
    await bot.delete_message(call.from_user.id, call.message.message_id)
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT user FROM users WHERE user = ?', (call.from_user.id,)).fetchall()
    if not data:
        await bot.send_message(call.from_user.id, 'You are not registered yet, use /start command')
        con.close()
        return
    cur.execute('UPDATE users SET role = ? WHERE user = ?', ('testo', call.from_user.id,))
    con.commit()
    con.close()
    await bot.send_message(call.from_user.id, 'Now your role is testo, your questions will be redirected to testoners, use /question command in order to ask something')

@dp.message_handler(commands=['q', 'question'])
async def question(message: types.Message):
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT user, role, paid FROM users WHERE user = ?', (message.from_user.id,)).fetchone()
    rated_quest = cur.execute('SELECT id FROM questions WHERE user = ? AND status = ?', (message.from_user.id, 2,)).fetchone()
    open_quest = cur.execute('SELECT id FROM questions WHERE user = ? AND status = ?', (message.from_user.id, 0,)).fetchone()
    con.close()

    if not data:
        await bot.send_message(message.from_user.id, 'You are not registered yet, use /start command')
        return
    
    if data[1] == "No":
        await bot.send_message(message.from_user.id, 'You do not have a role, use /change_role command')
        return
    
    if data[2] == 0:
        await message.answer('/buy full version of this bot, to ask a question')
        return
    
    if rated_quest:
        await message.answer(f'Before asking neew question, please rate us from 1 to 5. If you do not want to rate our system, you can easily skip it', reply_markup=rate_kb)
        return
    
    if open_quest:
        await message.answer('You cannot ask a new question, until your last question is closed')
        return

    await Form.question.set()
    await message.answer('Write your question, which is related to your role, if you did not wanted ask a question use /cancel')

@dp.message_handler(state='*', commands='cancel')
#@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.answer('Canceled')

@dp.message_handler(state=Form.question, content_types=[ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO])
async def send_question(message: types.Message, state: FSMContext):
    text = message.text or message.caption
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT role FROM users WHERE user = ?', (message.from_user.id,)).fetchone()
    cur.execute('INSERT INTO questions (role, text, user, helper) VALUES (?, ?, ?, NULL) RETURNING id', (data[0], text, message.from_user.id))
    row = cur.fetchone()
    id = row[0] if row else None
    username =  '@'+message.from_user.username if message.from_user.username is not None else 'no username'
    txt = f'New question from {username}\n{text}\n#id{id}'
    if message.content_type == 'photo' or message.content_type == 'video':
        await message.copy_to(CHANNELS[data[0]], caption=txt)
    else:
        await bot.send_message(CHANNELS[data[0]], txt)
    await message.answer(f'You can text to your answerers, just send me something, and I will resend it to the answerers')
    await state.finish()
    con.commit()
    con.close()

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
        await message.answer('Question is not found')
        con.close()
        return
    if data[2] == 1 or data[2] == 2:
        await message.answer('Question is closed')
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
    await message.reply('Answerer set')

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
        await message.answer('Question is not found')
        con.close()
        return
    
    if data[2] == 1 or data[2] == 2:
        await message.answer('Question is closed')
        con.close()
        return
    
    cur.execute('UPDATE questions SET status = ? WHERE id = ?', (2, int(id),))
    con.commit()
    con.close()
    await message.reply('You have closed this question')
    await bot.send_message(user, f'Rate us from 1 to 5', reply_markup=rate_kb)

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
        await message.answer('Question is not found')
        con.close()
        return
    
    if data[2] == 1 or data[2] == 2:
        await message.answer('Question is closed')
        con.close()
        return
    
    cur.execute('UPDATE questions SET status = ? WHERE id = ?', (1, int(id),))
    con.commit()
    con.close()
    await message.reply('You have closed this question without rating')

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
        await message.answer('There are no open questions')
        return
    
    if len(no_help) > 0:
        txt += 'Questions without answerers:\n'
        for n, i in enumerate(no_help, 1):
            txt += f'{n}. id: {i[0]}; link: t.me/c/{chats[chat]}/{i[2]}\n'
    
    if len(helping) > 0:
        txt += '\nQuestions with answerers:\n'
        for n, i in enumerate(helping, 1):
            txt += f'{n}. id: {i[0]}; answerer: {i[1]}; link: t.me/c/{chats[chat]}/{i[2]}\n'
    
    await message.answer(txt)

@dp.callback_query_handler(Text(equals=['1', '2', '3', '4', '5', 'no_rate']))
async def rate(call: types.CallbackQuery):
    await call.answer()
    await bot.delete_message(call.from_user.id, call.message.message_id)
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    quest = cur.execute('SELECT id FROM questions WHERE user = ? AND status = ?', (call.from_user.id, 2,)).fetchone()
    
    if not quest:
        await bot.send_message(call.from_user.id, 'Question is not found')
        con.close()
        return
    
    data = cur.execute('SELECT msg, role FROM questions WHERE id = ?', (quest[0],)).fetchone()
    
    if call.data != 'no_rate':
        cur.execute('UPDATE questions SET rating = ? WHERE id = ?', (int(call.data), quest[0],))
        await bot.send_message(CHATS[data[1]], f'User rated the answer for {call.data}', reply_to_message_id=data[0])
    
    if call.data == 'no_rate':
        await bot.send_message(CHATS[data[1]], 'User prefered not to rate us', reply_to_message_id=data[0])
    
    cur.execute('UPDATE questions SET status = ? WHERE id = ?', (1, quest[0],))
    con.commit()
    con.close()
    await bot.send_message(call.from_user.id, 'Thank you!')

@dp.message_handler(chat_type=ChatType.PRIVATE, content_types='any')
async def send_msg(message: types.Message):    
    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT role, msg FROM questions WHERE user = ? AND status = ?', (message.from_user.id, 0,)).fetchone()
    con.close()

    if not data:
        await message.answer('Ask me something')
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
        await message.answer('Question is not found')
        return
    
    if data[2] == 1 or data[2] == 2:
        await message.answer('Question is closed')
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
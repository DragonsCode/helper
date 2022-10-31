from fastapi import FastAPI
from aiogram import types, Dispatcher, Bot
from bot.helperV2 import dp, bot
from config import TOKEN
from yookassa import Configuration, Payment
import uuid
import sqlite3

Configuration.account_id = '953671'
Configuration.secret_key = 'test_6Pc60gJhmMl5XTko-HwI7vdc5kdzy34Yt3hdaDq1qlw'


app = FastAPI()
WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = "https://757b-84-54-84-124.eu.ngrok.io" + WEBHOOK_PATH


@app.on_event("startup")
async def on_startup():
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await bot.set_webhook(
            url=WEBHOOK_URL
        )


@app.post(WEBHOOK_PATH)
async def bot_webhook(update: dict):
    telegram_update = types.Update(**update)
    Dispatcher.set_current(dp)
    Bot.set_current(bot)
    await dp.process_update(telegram_update)


@app.get("/pay")
async def pay(username: str):
    if not username and len(username) < 4:
        return {"error": "invalid username"}
    
    username = username.lower()
    payment = Payment.create({
        "amount": {
            "value": "100.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://www.example.com/return_url"
        },
        "capture": True,
        "description": "Payment"
    }, uuid.uuid4()) 

    con = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    data = cur.execute('SELECT username FROM site WHERE username = ?', (username,)).fetchall()

    if not data:
        cur.execute('INSERT INTO site (id, username) VALUES (?, ?)', (payment.id, username,))
    else:
        cur.execute('UPDATE site SET id = ? WHERE username = ?', (payment.id, username,))
    
    con.commit()
    con.close()
    return payment.confirmation.confirmation_url


@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
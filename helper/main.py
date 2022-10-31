import uvicorn
import logging

from bot.helperV2 import db, set_false_job, scheduler


logging.basicConfig(level=logging.INFO)


def start():
    uvicorn.run("api.app:app", reload=True)


if __name__ == '__main__':
    db()
    set_false_job()
    start()
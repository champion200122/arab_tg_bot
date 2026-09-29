import os

from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from handlers import router as bot_router

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

dp.include_router(bot_router)

@app.get("/health")
async def health():
    return {"status": "ok"}


missing = [v for v in ("BOT_TOKEN", "WEBHOOK_URL", "WEBHOOK_SECRET")
           if not os.environ.get(v)]
if missing:
    raise SystemExit(f"Не заданы переменные окружения: {missing}")


@app.on_event("startup")
async def startup():
    try:
        await bot.set_webhook(url=WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
        print("WEBHOOK OK:", WEBHOOK_URL)
    except Exception as e:
        print("WEBHOOK SETUP ERROR:", repr(e))


@app.on_event("shutdown")
async def shutdown():
    await bot.session.close()

@app.post("/webhook")
async def webhook(request: Request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")

    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Bad secret token")

    data = await request.json()
    update = Update.model_validate(data)

    await dp.feed_update(bot, update)

    return {"ok": True}

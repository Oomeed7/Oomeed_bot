import sqlite3
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
import asyncio
from openai import OpenAI
from datetime import date

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_API_KEY)

# ===== База данных =====
conn = sqlite3.connect("calories.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS meals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    meal_date TEXT,
    calories INTEGER
)
""")
conn.commit()

# ===== /start =====
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "📸 Отправь фото еды с описанием"
    )

# ===== Фото =====
@dp.message(lambda m: m.photo)
async def handle_photo(message: Message):

    if not message.caption:
        await message.answer("❗️ Добавь описание еды")
        return

    text = message.caption

    response = client.chat.completions.create(
        model="gpt-5.2",
        messages=[
            {
                "role": "user",
                "content": f"Посчитай калории: {text}. Ответь только числом."
            }
        ],
    )

    kcal = int(response.choices[0].message.content.strip())

    today = str(date.today())

    cursor.execute(
        "INSERT INTO meals (user_id, meal_date, calories) VALUES (?, ?, ?)",
        (message.from_user.id, today, kcal)
    )
    conn.commit()

    cursor.execute(
        "SELECT SUM(calories) FROM meals WHERE user_id=? AND meal_date=?",
        (message.from_user.id, today)
    )

    total = cursor.fetchone()[0] or 0

    await message.answer(
        f"🔥 Приём пищи: {kcal} ккал\n"
        f"📊 Сегодня: {total} ккал"
    )

# ===== /today =====
@dp.message(Command("today"))
async def today(message: Message):

    today = str(date.today())

    cursor.execute(
        "SELECT SUM(calories) FROM meals WHERE user_id=? AND meal_date=?",
        (message.from_user.id, today)
    )

    total = cursor.fetchone()[0] or 0

    await message.answer(f"📊 Сегодня: {total} ккал")

# ===== Запуск =====
async def main():
    await dp.start_polling(bot)

if name == "__main__":
    asyncio.run(main())

import sqlite3
import os
import base64
import requests
from aiogram import Bot, Dispatcher, F
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
    await message.answer("📸 Отправь фото еды (можно с описанием)")

# ===== Фото + AI анализ =====
@dp.message(F.photo)
async def handle_photo(message: Message):

    caption = message.caption or ""

    # 📥 Скачать фото
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = file.file_path
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

    image_bytes = requests.get(file_url).content
    image_base64 = base64.b64encode(image_bytes).decode()

    # 🧠 AI анализ
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты эксперт по питанию. Определи блюдо на фото, "
                    "разбей на ингредиенты и оцени калорийность каждого. "
                    "В конце укажи общую калорийность."
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Комментарий пользователя: {caption}"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        },
                    },
                ],
            },
        ],
    )

    result = response.choices[0].message.content

    # 🧮 Попробуем извлечь итоговые ккал
    import re
    numbers = re.findall(r"\d+", result)
    kcal = int(numbers[-1]) if numbers else 0

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
        f"{result}\n\n"
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

if __name__ == "__main__":
    asyncio.run(main())

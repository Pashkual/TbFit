
import os
import json
import logging
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Токен из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

# Путь к базе данных
DATA_PATH = "data/user_data.json"

# Логирование
logging.basicConfig(level=logging.INFO)

# Главное меню
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton("🏋 Тренировка сегодня"))
main_menu.add(KeyboardButton("📊 Мой прогресс"), KeyboardButton("📆 Расписание"))
main_menu.add(KeyboardButton("ℹ Помощь"), KeyboardButton("🔄 Сбросить прогресс"))

# План тренировок
WORKOUTS = {
    "Пн": "Отжимания 3x12, Приседания 3x15, Планка 3x30 сек",
    "Вт": "Кардио (прыжки, бег на месте) 15 мин, пресс 3x20",
    "Ср": "Отдых или растяжка 10 мин",
    "Чт": "Приседания 3x20, Отжимания 3x10, Планка 3x40 сек",
    "Пт": "Кардио 15 мин, пресс 3x25",
    "Сб": "Йога/растяжка 15 мин",
    "Вс": "Отдых или прогулка 30 мин"
}

def load_data():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=2)

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я твой фитнес-тренер 💪", reply_markup=main_menu)

@dp.message_handler(lambda m: m.text == "🏋 Тренировка сегодня")
async def handle_today(message: types.Message):
    today = datetime.now().strftime("%a")
    day = {"Mon": "Пн", "Tue": "Вт", "Wed": "Ср", "Thu": "Чт", "Fri": "Пт", "Sat": "Сб", "Sun": "Вс"}[today]
    plan = WORKOUTS.get(day, "Отдых")
    await message.answer(f"📅 Сегодня: {day}

{plan}")

    data = load_data()
    uid = str(message.from_user.id)
    user = data.setdefault(uid, {"done": []})
    user["done"].append(datetime.now().strftime("%Y-%m-%d"))
    save_data(data)

@dp.message_handler(lambda m: m.text == "📆 Расписание")
async def show_schedule(message: types.Message):
    text = "\n".join([f"{day}: {plan}" for day, plan in WORKOUTS.items()])
    await message.answer(f"🗓 План недели:\n\n{text}")

@dp.message_handler(lambda m: m.text == "📊 Мой прогресс")
async def send_weekly_graph(message: types.Message):
    data = load_data()
    uid = str(message.from_user.id)
    user = data.get(uid, {"done": []})

    today = datetime.now()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    counts = [user["done"].count(day.strftime("%Y-%m-%d")) for day in days]
    labels = [day.strftime("%a") for day in days]

    plt.figure(figsize=(8, 4))
    plt.bar(labels, counts, color="skyblue")
    plt.title("Активность за последнюю неделю")
    plt.xlabel("День")
    plt.ylabel("Тренировки")
    plt.tight_layout()
    path = f"data/{uid}_graph.png"
    plt.savefig(path)
    plt.close()
    with open(path, "rb") as img:
        await message.answer_photo(img)

@dp.message_handler(lambda m: m.text == "ℹ Помощь")
async def help_msg(message: types.Message):
    await message.answer(
        "Я помогу тебе следить за тренировками 🚴‍♂️\n\n"
        "Команды:\n"
        "🏋 — показать тренировку сегодня\n"
        "📊 — показать прогресс\n"
        "📆 — показать расписание\n"
        "🔄 — сбросить прогресс\n"
        "/start — перезапустить бота"
    )

@dp.message_handler(lambda m: m.text == "🔄 Сбросить прогресс")
async def reset_data(message: types.Message):
    data = load_data()
    uid = str(message.from_user.id)
    if uid in data:
        data[uid]["done"] = []
        save_data(data)
    await message.answer("Прогресс сброшен. Начинаем с чистого листа!")

async def scheduled_check():
    now = datetime.now()
    if now.hour == 9:
        data = load_data()
        for uid in data:
            await bot.send_message(uid, "🕘 Напоминание: не забудь про тренировку сегодня!")

if __name__ == "__main__":
    scheduler.add_job(scheduled_check, "interval", hours=1)
    scheduler.start()
    executor.start_polling(dp, skip_updates=True)

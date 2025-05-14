import sqlite3
import logging
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import csv
import os
import matplotlib.pyplot as plt
import random

from dotenv import load_dotenv
# Загружаем переменные окружения
load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
USER_ID = 1337650743

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
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
    "Пн": "Разминка 5 мин (ходьба/прыжки на месте), Приседания с медленным опусканием 3x15, Отжимания от пола/кровати 3x10, Планка 3x30 сек, Заминка (растяжка ног/груди) 5 мин",

    "Вт": "Разминка 5 мин (кардио на месте), Кардио-комплекс: 5 раундов — 30 сек берпи, 30 сек бег на месте, 30 сек прыжки на месте, Пресс: подъёмы ног лёжа 3x15, Планка с подъёмом ноги 3x20 сек на сторону",

    "Ср": "Активное восстановление: Йога-комплекс 15 мин (кошка-корова, поза ребёнка, наклоны стоя, растяжка бёдер), Дыхательные упражнения 5 мин (глубокое диафрагмальное дыхание стоя)",

    "Чт": "Разминка 5 мин (маховые движения руками, ходьба), Комплекс силы: Приседания на одной ноге у стены 3x8 (на каждую), Отжимания узким хватом 3x8, Планка с касанием плеч 3x20 сек, Заминка 5 мин",

    "Пт": "Интервальный кардио-комплекс: 30 сек быстрый шаг на месте + 30 сек ускорения (8 раундов), Упражнение 'велосипед' 3x20, Подъёмы таза лёжа 3x20, Наклоны в стороны с удержанием 3x30 сек",

    "Сб": "Растяжка всего тела: шея, плечи, грудь, спина, ноги (комплекс на 20 минут), Йога: поза собаки мордой вниз, голубь, скрутки лёжа, дыхание через нос, отдых",

    "Вс": "Активный отдых: Прогулка по палубе или марш на месте 30 мин с контролем пульса, Динамическая разминка и мягкая растяжка (5–10 мин)"
}

def load_data():
    if not os.path.exists("data.json"):
        return {}

    with open("data.json", "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
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
    await message.answer(f"📅 Сегодня: {day}\n\n{plan}")

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

import telebot
import threading
import time
import json
import os
from datetime import datetime, date
TOKEN = "" # вставьте сюда токен вашего бота, который вы получили от BotFather (Тут до этого был токен, я его удалил для безопасности)
bot = telebot.TeleBot(TOKEN)
DATA_FILE = "water_data.json"
LOCK = threading.Lock()
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
def today_str():
    return date.today().isoformat()
def ensure_user(data, user_id: int):
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"goal_ml": 2000, "drank_ml": 0, "last_day": today_str()}
        return
    if data[uid].get("last_day") != today_str():
        data[uid]["drank_ml"] = 0
        data[uid]["last_day"] = today_str()
def parse_amount_to_ml(text: str):
    s = text.strip().lower().replace(",", ".")
    s = s.replace(" ", "")
    s = s.replace("мл", "ml").replace("л", "l")

    if s.endswith("ml"):
        num = s[:-2]
        val = float(num)
        return int(val)

    if s.endswith("l"):
        num = s[:-1]
        val = float(num)
        return int(val * 1000)
    val = float(s)
    return int(val)

def format_progress(goal_ml, drank_ml):
    left = max(goal_ml - drank_ml, 0)
    return f"Цель: {goal_ml} мл\nВыпито: {drank_ml} мл\nОсталось: {left} мл"
def schedule_one_time_reminder(chat_id: int, hours: float):
    seconds = int(hours * 3600)

    def worker():
        time.sleep(seconds)
        try:
            bot.send_message(chat_id, "💧 Пора попить воды!")
        except Exception:
            pass

    t = threading.Thread(target=worker, daemon=True)
    t.start()
@bot.message_handler(commands=["start", "help"])
def start_help(message):
    text = (
        "Привет! Я бот напоминалка воды 💧\n\n"
        "Команды:\n"
        "/setreminder X — напомнить через X часов (пример: /setreminder 2)\n"
        "/goal N — цель на день (в мл или л). Примеры: /goal 2000, /goal 2l\n"
        "/drank N — добавить выпитое (в мл или л). Примеры: /drank 250, /drank 0.5l\n"
        "/status — показать прогресс\n\n"
        "По умолчанию цель 2000 мл."
    )
    bot.send_message(message.chat.id, text)
@bot.message_handler(commands=["setreminder"])
def setreminder(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Напиши так: /setreminder 2 (это 2 часа)")
        return
    try:
        hours = float(parts[1].strip().replace(",", "."))
        if hours <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "X должно быть числом больше 0. Пример: /setreminder 1.5")
        return
    schedule_one_time_reminder(message.chat.id, hours)
    bot.send_message(message.chat.id, f"Ок! Напомню через {hours} ч ⏳")
@bot.message_handler(commands=["goal"])
def goal(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Напиши так: /goal 2000 или /goal 2l")
        return
    try:
        goal_ml = parse_amount_to_ml(parts[1])
        if goal_ml <= 0:
            raise ValueError
    except Exception:
        bot.send_message(message.chat.id, "Не понял число. Пример: /goal 2000 или /goal 2l")
        return
    with LOCK:
        data = load_data()
        ensure_user(data, message.from_user.id)
        uid = str(message.from_user.id)
        data[uid]["goal_ml"] = goal_ml
        save_data(data)
    bot.send_message(message.chat.id, f"✅ Цель на сегодня установлена: {goal_ml} мл")
@bot.message_handler(commands=["drank"])
def drank(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Напиши так: /drank 250 или /drank 0.5l")
        return
    try:
        add_ml = parse_amount_to_ml(parts[1])
        if add_ml <= 0:
            raise ValueError
    except Exception:
        bot.send_message(message.chat.id, "Не понял число. Пример: /drank 250 или /drank 0.5l")
        return
    with LOCK:
        data = load_data()
        ensure_user(data, message.from_user.id)
        uid = str(message.from_user.id)

        data[uid]["drank_ml"] += add_ml
        goal_ml = data[uid]["goal_ml"]
        drank_ml = data[uid]["drank_ml"]
        save_data(data)
    left = max(goal_ml - drank_ml, 0)
    msg = (
        f"🥤 Добавил: {add_ml} мл\n"
        f"{format_progress(goal_ml, drank_ml)}"
    )
    if left == 0:
        msg += "\n\n🎉 Ты закрыл цель на сегодня! Красавчик."
    bot.send_message(message.chat.id, msg)
@bot.message_handler(commands=["status"])
def status(message):
    with LOCK:
        data = load_data()
        ensure_user(data, message.from_user.id)
        uid = str(message.from_user.id)
        goal_ml = data[uid]["goal_ml"]
        drank_ml = data[uid]["drank_ml"]
        save_data(data)
    bot.send_message(message.chat.id, "📊 Статус:\n" + format_progress(goal_ml, drank_ml))
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()

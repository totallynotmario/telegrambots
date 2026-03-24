import os
import telebot
from telebot import types
import requests
TOKEN = "" # вставьте сюда токен вашего бота, который вы получили от BotFather (Тут был до этого токен, я его удалил для безопасности)
FX_API_KEY = "" # вставьте сюда ваш API-ключ от https://www.exchangerate-api.com/
BASE_URL = "https://v6.exchangerate-api.com/v6/{key}/latest/{base}"
bot = telebot.TeleBot(TOKEN)
POPULAR = ["USD", "EUR", "KZT", "RUB", "GBP", "CNY"]
state = {}
I18N = {
    "ru": {
        "welcome": "Привет! Выбери язык и валюты кнопками ниже, затем отправь сумму числом (например 1500).",
        "help": "Как пользоваться:\n• Выбери базовую валюту\n• Выбери валюту назначения\n• Отправь сумму числом\n\nКоманды: /start, /help, /lang",
        "choose_base": "Выбери базовую валюту:",
        "choose_quote": "Выбери валюту назначения:",
        "current_pair": "Текущая пара: {base} → {quote}. Теперь отправь сумму.",
        "enter_amount": "Отправь сумму числом (например 1500).",
        "bad_amount": "Не понял сумму. Напиши число, например 1500 или 1500.50",
        "rate_line": "💱 {amount:g} {base} = {result:g} {quote}\nКурс: 1 {base} = {rate:g} {quote}",
        "api_error": "Не получилось получить курс 😕 Попробуй позже.",
        "btn_base": "База",
        "btn_quote": "В",
        "btn_lang": "Язык",
        "btn_help": "Помощь",
        "btn_back": "Назад",
        "choose_lang": "Выбери язык:",
        "lang_set": "Язык установлен: {lang_name}",
        "lang_names": {"ru": "Русский", "en": "English", "kk": "Қазақша"},
    },
    "en": {
        "welcome": "Hi! Choose language and currencies below, then send an amount (e.g. 1500).",
        "help": "How to use:\n• Choose base currency\n• Choose target currency\n• Send an amount\n\nCommands: /start, /help, /lang",
        "choose_base": "Choose base currency:",
        "choose_quote": "Choose target currency:",
        "current_pair": "Current pair: {base} → {quote}. Now send an amount.",
        "enter_amount": "Send an amount (e.g. 1500).",
        "bad_amount": "I couldn't parse the amount. Send a number like 1500 or 1500.50",
        "rate_line": "💱 {amount:g} {base} = {result:g} {quote}\nRate: 1 {base} = {rate:g} {quote}",
        "api_error": "Couldn't fetch the rate 😕 Try again later.",
        "btn_base": "Base",
        "btn_quote": "To",
        "btn_lang": "Language",
        "btn_help": "Help",
        "btn_back": "Back",
        "choose_lang": "Choose a language:",
        "lang_set": "Language set: {lang_name}",
        "lang_names": {"ru": "Russian", "en": "English", "kk": "Kazakh"},
    },
    "kk": {
        "welcome": "Сәлем! Тілді және валюталарды төменнен таңда, сосын соманы санмен жібер (мысалы 1500).",
        "help": "Қолдану:\n• Негізгі валютаны таңда\n• Қай валютаға ауыстыратынын таңда\n• Соманы санмен жібер\n\nКомандалар: /start, /help, /lang",
        "choose_base": "Негізгі валютаны таңда:",
        "choose_quote": "Қай валютаға ауыстыратынын таңда:",
        "current_pair": "Ағымдағы жұп: {base} → {quote}. Енді соманы жібер.",
        "enter_amount": "Соманы санмен жібер (мысалы 1500).",
        "bad_amount": "Соманы түсінбедім. 1500 немесе 1500.50 сияқты сан жібер.",
        "rate_line": "💱 {amount:g} {base} = {result:g} {quote}\nКурс: 1 {base} = {rate:g} {quote}",
        "api_error": "Курсты ала алмадым 😕 Кейінірек қайтала.",
        "btn_base": "Негізгі",
        "btn_quote": "Кімге",
        "btn_lang": "Тіл",
        "btn_help": "Көмек",
        "btn_back": "Артқа",
        "choose_lang": "Тілді таңда:",
        "lang_set": "Тіл орнатылды: {lang_name}",
        "lang_names": {"ru": "Орысша", "en": "Ағылшынша", "kk": "Қазақша"},
    }
}
def get_lang(chat_id: int, message=None) -> str:
    if chat_id in state and "lang" in state[chat_id]:
        return state[chat_id]["lang"]
    if message and getattr(message.from_user, "language_code", None):
        code = message.from_user.language_code.lower()
        if code.startswith("ru"):
            return "ru"
        if code.startswith("en"):
            return "en"
        if code.startswith("kk") or code.startswith("kz"):
            return "kk"
    return "ru"

def t(chat_id: int, key: str, message=None, **kwargs) -> str:
    lang = get_lang(chat_id, message)
    text = I18N[lang][key].format(**kwargs)
    return text
def ensure_state(chat_id: int, message=None):
    lang = get_lang(chat_id, message)
    state.setdefault(chat_id, {"lang": lang, "base": "USD", "quote": "KZT"})
def api_rate(base: str, quote: str) -> float:
    url = BASE_URL.format(key=FX_API_KEY, base=base)
    r = requests.get(url, timeout=10)
    data = r.json()
    return float(data["conversion_rates"][quote])
def menu_kb(chat_id: int, message=None) -> types.InlineKeyboardMarkup:
    ensure_state(chat_id, message)
    lang = get_lang(chat_id, message)
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(f"{I18N[lang]['btn_base']} ({state[chat_id]['base']})", callback_data="menu:base"),
        types.InlineKeyboardButton(f"{I18N[lang]['btn_quote']} ({state[chat_id]['quote']})", callback_data="menu:quote"),
    )
    kb.add(
        types.InlineKeyboardButton(I18N[lang]["btn_lang"], callback_data="menu:lang"),
        types.InlineKeyboardButton(I18N[lang]["btn_help"], callback_data="menu:help"),
    )
    return kb
def currencies_kb(prefix: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=3)
    for c in POPULAR:
        kb.add(types.InlineKeyboardButton(c, callback_data=f"{prefix}:{c}"))
    kb.add(types.InlineKeyboardButton("⬅️", callback_data="menu:back"))
    return kb
def lang_kb(chat_id: int, message=None) -> types.InlineKeyboardMarkup:
    ensure_state(chat_id, message)
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(
        types.InlineKeyboardButton("Русский", callback_data="lang:ru"),
        types.InlineKeyboardButton("English", callback_data="lang:en"),
        types.InlineKeyboardButton("Қазақша", callback_data="lang:kk"),
    )
    kb.add(types.InlineKeyboardButton("⬅️", callback_data="menu:back"))
    return kb
@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    ensure_state(chat_id, message)
    bot.send_message(
        chat_id,
        t(chat_id, "welcome", message),
        reply_markup=menu_kb(chat_id, message)
    )
@bot.message_handler(commands=["help"])
def help_cmd(message):
    chat_id = message.chat.id
    ensure_state(chat_id, message)
    bot.send_message(chat_id, t(chat_id, "help", message), reply_markup=menu_kb(chat_id, message))
@bot.message_handler(commands=["lang"])
def lang_cmd(message):
    chat_id = message.chat.id
    ensure_state(chat_id, message)
    bot.send_message(chat_id, t(chat_id, "choose_lang", message), reply_markup=lang_kb(chat_id, message))
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    chat_id = call.message.chat.id
    ensure_state(chat_id)
    lang = get_lang(chat_id)
    data = call.data
    if data == "menu:base":
        bot.edit_message_text(
            t(chat_id, "choose_base"),
            chat_id,
            call.message.message_id,
            reply_markup=currencies_kb("setbase")
        )
        return
    if data == "menu:quote":
        bot.edit_message_text(
            t(chat_id, "choose_quote"),
            chat_id,
            call.message.message_id,
            reply_markup=currencies_kb("setquote")
        )
        return
    if data == "menu:lang":
        bot.edit_message_text(
            t(chat_id, "choose_lang"),
            chat_id,
            call.message.message_id,
            reply_markup=lang_kb(chat_id)
        )
        return
    if data == "menu:help":
        bot.edit_message_text(
            I18N[lang]["help"],
            chat_id,
            call.message.message_id,
            reply_markup=menu_kb(chat_id)
        )
        return
    if data == "menu:back":
        bot.edit_message_text(
            t(chat_id, "current_pair", base=state[chat_id]["base"], quote=state[chat_id]["quote"]),
            chat_id,
            call.message.message_id,
            reply_markup=menu_kb(chat_id)
        )
        return
    if data.startswith("setbase:"):
        base = data.split(":")[1]
        state[chat_id]["base"] = base
        bot.edit_message_text(
            t(chat_id, "current_pair", base=state[chat_id]["base"], quote=state[chat_id]["quote"]),
            chat_id,
            call.message.message_id,
            reply_markup=menu_kb(chat_id)
        )
        return
    if data.startswith("setquote:"):
        quote = data.split(":")[1]
        state[chat_id]["quote"] = quote
        bot.edit_message_text(
            t(chat_id, "current_pair", base=state[chat_id]["base"], quote=state[chat_id]["quote"]),
            chat_id,
            call.message.message_id,
            reply_markup=menu_kb(chat_id)
        )
        return
    if data.startswith("lang:"):
        new_lang = data.split(":")[1]
        state[chat_id]["lang"] = new_lang
        lang_name = I18N[new_lang]["lang_names"][new_lang]
        bot.edit_message_text(
            I18N[new_lang]["lang_set"].format(lang_name=lang_name) + "\n" +
            I18N[new_lang]["current_pair"].format(base=state[chat_id]["base"], quote=state[chat_id]["quote"]),
            chat_id,
            call.message.message_id,
            reply_markup=menu_kb(chat_id)
        )
        return
@bot.message_handler(content_types=["text"])
def on_amount(message):
    chat_id = message.chat.id
    ensure_state(chat_id, message)
    text = message.text.strip().replace(" ", "").replace(",", ".")
    try:
        amount = float(text)
    except ValueError:
        bot.send_message(chat_id, t(chat_id, "bad_amount", message), reply_markup=menu_kb(chat_id, message))
        return
    base = state[chat_id]["base"]
    quote = state[chat_id]["quote"]
    try:
        rate = api_rate(base, quote)
        result = amount * rate
        bot.send_message(
            chat_id,
            t(chat_id, "rate_line", message, amount=amount, base=base, quote=quote, rate=rate, result=result),
            reply_markup=menu_kb(chat_id, message)
        )
    except Exception:
        bot.send_message(chat_id, t(chat_id, "api_error", message), reply_markup=menu_kb(chat_id, message))
bot.infinity_polling()
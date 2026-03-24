import time
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

import telebot
from openai import OpenAI
TELEGRAM_TOKEN = ""
OPENROUTER_API_KEY = ""

if not TELEGRAM_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_BOT_TOKEN в переменных окружения.")
if not OPENROUTER_API_KEY:
    raise RuntimeError("Не найден OPENROUTER_API_KEY в переменных окружения.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

MODEL_NAME = "gpt-oss-120b"

Mode = Literal["tutor", "solution"]
Step = Literal["idle", "intake", "diagnose", "try_user", "final"]
@dataclass
class UserState:
    mode: Mode = "tutor"
    step: Step = "idle"
    goal: Optional[str] = None
    context: List[dict] = field(default_factory=list) 
    last_active: float = field(default_factory=time.time)

user_states: Dict[int, UserState] = {}

def get_state(chat_id: int) -> UserState:
    st = user_states.get(chat_id)
    if st is None:
        st = UserState()
        user_states[chat_id] = st
    st.last_active = time.time()
    return st

def trim_history(messages: List[dict], max_turns: int = 14) -> List[dict]:
    if not messages:
        return messages
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]
    non_system = non_system[-max_turns:]
    if system_msgs:
        return [system_msgs[0]] + non_system
    return non_system

SYSTEM_TUTOR = (
    "Ты — Telegram-бот-наставник для начинающих разработчиков на Python.\n"
    "Твоя цель — НАУЧИТЬ, а не выдать готовое решение сразу.\n"
    "Правила:\n"
    "1) Сначала уточни вводные: цель, входные/выходные данные, ограничения, что уже пробовал.\n"
    "2) Затем дай план/подсказки + учебные материалы/ссылки (текстом, без URL, но можно указывать названия сайтов).\n"
    "3) Попроси пользователя попробовать и прислать попытку/ошибку.\n"
    "4) Только если пользователь явно попросит 'дай решение' или включён режим solution — давай полный код.\n"
    "5) Всегда объясняй ключевые шаги, типичные ошибки, и как проверить результат.\n"
    "6) Если пользователь присылает код/traceback — сначала диагностируй и укажи 1-3 наиболее вероятные причины.\n"
    "Формат ответа (в режиме tutor):\n"
    "- 2–4 уточняющих вопроса\n"
    "- Короткий план\n"
    "- 2–5 подсказок\n"
    "- 2–4 источника (название ресурса + что там искать)\n"
    "- 'Твой ход' — что прислать дальше\n"
)

SYSTEM_SOLUTION = (
    "Ты — помощник по Python. Дай прямое решение, но всё равно добавь краткое объяснение и как проверить."
)

TOPIC_LIBRARY = {
    "списки": [
        "Python Docs: data structures (list) — методы append/extend/pop, срезы",
        "Real Python: Python Lists and Tuples — примеры и задачи",
        "LearnPython.org: Lists — короткие упражнения",
    ],
    "словарь": [
        "Python Docs: dict — методы get/items, перебор ключей/значений",
        "Real Python: Dictionaries in Python — частые паттерны",
        "Stepik: основы словарей — практические задания",
    ],
    "исключения": [
        "Python Docs: errors and exceptions — try/except, raise",
        "Real Python: Python Exceptions — типичные ошибки новичков",
        "Stack Overflow: 'python traceback' — как читать трассировку",
    ],
    "функции": [
        "Python Docs: defining functions — args/kwargs, return",
        "Real Python: Functions in Python — примеры",
        "Stepik: функции — упражнения",
    ],
    "ооп": [
        "Python Docs: classes — методы, __init__, self",
        "Real Python: Object-Oriented Programming in Python",
        "Stepik: ООП основы — тренировка",
    ],
}

def suggest_topics(query: str) -> List[str]:
    q = query.lower()
    hits = []
    for k in TOPIC_LIBRARY.keys():
        if k in q:
            hits.append(k)
    return hits[:3]
def llm_reply(state: UserState, user_text: str) -> str:
    system = SYSTEM_TUTOR if state.mode == "tutor" else SYSTEM_SOLUTION

    if not state.context:
        state.context.append({"role": "system", "content": system})
    else:
        # Ensure system matches mode
        if state.context[0].get("role") == "system":
            state.context[0]["content"] = system
        else:
            state.context.insert(0, {"role": "system", "content": system})

    state.context.append({"role": "user", "content": user_text})
    state.context = trim_history(state.context, max_turns=16)

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=state.context,
        temperature=0.6 if state.mode == "tutor" else 0.4,
        max_tokens=900,
    )

    text = (resp.choices[0].message.content or "").strip()
    state.context.append({"role": "assistant", "content": text})
    state.context = trim_history(state.context, max_turns=16)
    return text or "Пустой ответ. Сформулируй вопрос иначе."
def chunk_send(chat_id: int, text: str):
    if len(text) <= 4000:
        bot.send_message(chat_id, text)
        return
    for i in range(0, len(text), 4000):
        bot.send_message(chat_id, text[i:i+4000])

def intro_text() -> str:
    return (
        "Привет! Я бот-наставник по Python 🐍\n\n"
        "Я не буду сразу выдавать готовый код — сначала помогу разобраться: уточню задачу, дам подсказки и материалы, "
        "попрошу твою попытку. Если нужно решение — можно переключить режим.\n\n"
        "Команды:\n"
        "/mode tutor — режим наставника (по умолчанию)\n"
        "/mode solution — быстрые решения\n"
        "/debug — разбор ошибки/traceback\n"
        "/topic <тема> — материалы по теме (например: /topic списки)\n"
        "/challenge — мини-задачка\n"
        "/reset — сброс контекста\n"
        "/status — текущий режим/шаг\n\n"
        "Напиши, с чем ты сейчас борешься 🙂"
    )

@bot.message_handler(commands=["start"])
def cmd_start(message):
    st = get_state(message.chat.id)
    st.step = "idle"
    st.goal = None
    st.context.clear()
    bot.reply_to(message, intro_text())

@bot.message_handler(commands=["reset"])
def cmd_reset(message):
    st = get_state(message.chat.id)
    st.step = "idle"
    st.goal = None
    st.context.clear()
    bot.reply_to(message, "Контекст сброшен. Опиши задачу или проблему заново 🙂")

@bot.message_handler(commands=["status"])
def cmd_status(message):
    st = get_state(message.chat.id)
    bot.reply_to(message, f"Режим: {st.mode}\nШаг: {st.step}\nЦель: {st.goal or '—'}")

@bot.message_handler(commands=["mode"])
def cmd_mode(message):
    st = get_state(message.chat.id)
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Использование: /mode tutor или /mode solution")
        return
    m = parts[1].strip().lower()
    if m not in ("tutor", "solution"):
        bot.reply_to(message, "Доступно: tutor, solution")
        return
    st.mode = m 
    st.context.clear()
    bot.reply_to(message, f"Ок! Режим теперь: {st.mode}")

@bot.message_handler(commands=["topic"])
def cmd_topic(message):
    st = get_state(message.chat.id)
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        topics = ", ".join(sorted(TOPIC_LIBRARY.keys()))
        bot.reply_to(message, f"Напиши так: /topic <тема>\nДоступные темы: {topics}")
        return
    topic = parts[1].strip().lower()
    if topic in TOPIC_LIBRARY:
        lines = "\n".join([f"- {x}" for x in TOPIC_LIBRARY[topic]])
        bot.reply_to(message, f"Материалы по теме «{topic}»:\n{lines}\n\nХочешь — дай задачу по этой теме, и я проведу тебя шагами.")
    else:
        guess = suggest_topics(topic)
        if guess:
            bot.reply_to(message, f"Точной темы нет. Возможно ты имел в виду: {', '.join(guess)}\nНапиши: /topic <одно_из_них>")
        else:
            bot.reply_to(message, "Такой темы у меня нет. Попробуй: /topic списки | словарь | исключения | функции | ооп")

@bot.message_handler(commands=["debug"])
def cmd_debug(message):
    st = get_state(message.chat.id)
    st.step = "diagnose"
    st.goal = "Разбор ошибки/багов"
    st.context.clear()
    bot.reply_to(
        message,
        "Ок, давай дебажить.\n\n"
        "Пришли, пожалуйста:\n"
        "1) Текст ошибки/traceback (целиком)\n"
        "2) Код (минимальный фрагмент, который воспроизводит ошибку)\n"
        "3) Что ты ожидал увидеть и что получилось"
    )

@bot.message_handler(commands=["challenge"])
def cmd_challenge(message):
    st = get_state(message.chat.id)
    st.step = "try_user"
    st.goal = "Мини-задача"
    st.context.clear()
    bot.reply_to(
        message,
        "Мини-задача #1 (уровень: новичок)\n"
        "Напиши функцию `count_vowels(s)`, которая считает количество гласных букв в строке.\n\n"
        "Условия:\n"
        "- Гласные: aeiou (можешь добавить русские, если хочешь)\n"
        "- Регистр не важен\n\n"
        "Сначала пришли план/идею (2–5 строк), потом код. Я дам подсказки и улучшу решение."
    )

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    st = get_state(message.chat.id)
    text = (message.text or "").strip()

    if not text:
        bot.reply_to(message, "Пришли текст 🙂")
        return
    low = text.lower()

    wants_solution = any(x in low for x in ["дай решение", "готовый код", "полный код", "решение полностью", "сразу ответ", "просто ответ"])

    if st.mode == "tutor" and wants_solution:
        st.mode = "solution"
        st.context.clear()

    if st.step == "idle":
        st.step = "intake"
        st.goal = None
        st.context.clear()

        topics = suggest_topics(text)
        extra = ""
        if topics:
            extra = "\n\nПохоже, это связано с темами: " + ", ".join(topics) + ". Хочешь — могу дать материалы командой /topic."

        prompt = (
            "Пользователь описал проблему/задачу:\n"
            f"{text}\n\n"
            "Сгенерируй наставнический ответ по правилам."
            + extra
        )
        reply = llm_reply(st, prompt)
        chunk_send(message.chat.id, reply)
        st.step = "try_user"
        return

    if st.step in ("diagnose", "try_user", "final"):
        reply = llm_reply(st, text)
        chunk_send(message.chat.id, reply)
        return

    reply = llm_reply(st, text)
    chunk_send(message.chat.id, reply)

if __name__ == "__main__":
    print("Mentor bot started (OpenRouter | gpt-oss-120b)")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)

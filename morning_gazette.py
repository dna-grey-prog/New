#!/usr/bin/env python3
"""
🌙 Газета Холодной Луны
Ежедневная утренняя рассылка в Telegram.

Использование:
  python3 morning_gazette.py            — отправить газетку
  python3 morning_gazette.py --get-id    — узнать свой chat_id
"""

import json
import os
import random
import sys
import urllib.request
import urllib.parse
import re
from datetime import datetime

# ════════════════════════════════════════
#  НАСТРОЙКИ
# ════════════════════════════════════════
BOT_TOKEN = "8934023629:AAFlM3KW_B7eG0EkZ32Ulc7iqmREd1kvfVE"
CHAT_ID   = "1284823603"

DATA_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SEPARATOR = "━━━━━━━━━━━━━━━━━━"

# ════════════════════════════════════════
#  СЕЗОНЫ
# ════════════════════════════════════════
def get_season(month):
    if month in (12, 1, 2):   return "winter"
    if month in (3, 4, 5):    return "spring"
    if month in (6, 7, 8):    return "summer"
    return "autumn"

# ════════════════════════════════════════
#  ЗАГРУЗКА БАЗ ДАННЫХ
# ════════════════════════════════════════
def load_lines(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith("#")]
    return lines

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ════════════════════════════════════════
#  ВЕБ-ЗАПРОСЫ
# ════════════════════════════════════════
def fetch_url(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[WARN] Не удалось загрузить {url}: {e}")
        return ""

# ════════════════════════════════════════
#  ДЕНЬ В ИСТОРИИ (с calend.ru)
# ════════════════════════════════════════
def get_history_events(day, month):
    url = f"https://www.calend.ru/day/{day}-{month}/"
    html = fetch_url(url)
    if not html:
        return "Сегодня нет данных о событиях. Загляните позже!"

    events = []
    # Ищем блоки с событиями
    blocks = re.findall(r'<div class="thing-anonce">\s*(.*?)\s*</div>', html, re.DOTALL)
    for block in blocks[:6]:
        text = re.sub(r'<[^>]+>', '', block).strip()
        text = re.sub(r'\s+', ' ', text)
        if len(text) > 20:
            # Ограничиваем длину
            if len(text) > 200:
                text = text[:197] + "..."
            events.append(text)

    if not events:
        # Альтернативный паттерн
        blocks = re.findall(r'<span class="title">\s*(.*?)\s*</span>', html, re.DOTALL)
        for block in blocks[:6]:
            text = re.sub(r'<[^>]+>', '', block).strip()
            text = re.sub(r'\s+', ' ', text)
            if len(text) > 20:
                if len(text) > 200:
                    text = text[:197] + "..."
                events.append(text)

    return "\n\n".join(f"📜 {e}" for e in events) if events else "Сегодня нет данных о событиях."

# ════════════════════════════════════════
#  ПРАЗДНИКИ (с calend.ru)
# ════════════════════════════════════════
def get_holidays(day, month):
    url = f"https://www.calend.ru/day/{day}-{month}/"
    html = fetch_url(url)
    if not html:
        return ""

    holidays = []
    # Ищем праздники
    blocks = re.findall(r'<div class="famous-anonce">\s*(.*?)\s*</div>', html, re.DOTALL)
    for block in blocks[:5]:
        text = re.sub(r'<[^>]+>', '', block).strip()
        text = re.sub(r'\s+', ' ', text)
        if len(text) > 5:
            holidays.append(text)

    if not holidays:
        blocks = re.findall(r'class=" CelebrateDay"[^>]*>\s*(.*?)\s*</a>', html, re.DOTALL)
        for block in blocks[:5]:
            text = re.sub(r'<[^>]+>', '', block).strip()
            if len(text) > 5:
                holidays.append(text)

    return " · ".join(holidays) if holidays else ""

# ════════════════════════════════════════
#  НАРОДНЫЕ ПРИМЕТЫ (с calend.ru)
# ════════════════════════════════════════
def get_omens(day, month):
    url = f"https://www.calend.ru/day/{day}-{month}/"
    html = fetch_url(url)
    if not html:
        return "Приметы сегодня недоступны."

    # Ищем блок с народными приметами
    match = re.search(r'Народные приметы[^<]*</h\d?>(.*?)(?:<h\d|<div class="block",|</section)', html, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1)
        text = re.sub(r'<[^>]+>', '', text).strip()
        text = re.sub(r'\s+', ' ', text)
        if len(text) > 20:
            return text[:500]

    # Альтернативный поиск
    match = re.search(r'примет[а-я]*[^<]*</[^>]+>(.*?)(?:<h\d|</section|<div class="block)', html, re.DOTALL | re.IGNORECASE)
    if match:
        text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
        text = re.sub(r'\s+', ' ', text)
        if len(text) > 20:
            return text[:500]

    return "Сегодня нет данных о приметах."

# ════════════════════════════════════════
#  ИМЕНИНЫ (с my-calend.ru)
# ════════════════════════════════════════
def get_namedays(day, month):
    url = f"https://my-calend.ru/name-days/{day}-{month:02d}"
    html = fetch_url(url)
    if not html:
        return ""

    match = re.search(r'именины[^<]*</h\d?>(.*?)(?:<h\d|</article|</section)', html, re.DOTALL | re.IGNORECASE)
    if match:
        text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
        names = re.findall(r'[А-Яа-яЁё]{3,}', text)
        # Очищаем от мусора
        stop_words = {"именины", "сегодня", "справочник", "календарь", "января", "февраля",
                       "марта", "апреля", "мая", "июня", "июля", "августа",
                       "сентября", "октября", "ноября", "декабря"}
        names = [n for n in names if n.lower() not in stop_words]
        if names:
            # Убираем дубликаты, сохраняя порядок
            seen = set()
            unique = []
            for n in names:
                if n not in seen:
                    seen.add(n)
                    unique.append(n)
            return ", ".join(unique[:20])

    return ""

# ════════════════════════════════════════
#  ФОРМАТИРОВАНИЕ ЧЕТВОРОСТИШИЙ
# ════════════════════════════════════════
def format_poem(text, emoji_start="🌅", emoji_end="🍂"):
    """Каждое четверостишие: каждая строка с новой строки."""
    lines = text.strip().split("\n")
    formatted = f"{emoji_start}\n"
    for line in lines:
        line = line.strip()
        if line:
            # Первая буква заглавная
            if line[0].islower():
                line = line[0].upper() + line[1:]
            formatted += f"*{line}*\n"
    formatted += f"{emoji_end}"
    return formatted

def format_closing_poem(text, emoji_start="☀️", emoji_end="😊"):
    lines = text.strip().split("\n")
    formatted = f"{emoji_start}\n"
    for line in lines:
        line = line.strip()
        if line:
            if line[0].islower():
                line = line[0].upper() + line[1:]
            formatted += f"*{line}*\n"
    formatted += f"{emoji_end}"
    return formatted

# ════════════════════════════════════════
#  ЧИСЛО ДНЯ
# ════════════════════════════════════════
def get_day_number():
    now = datetime.now()
    day_of_year = now.timetuple().tm_yday
    days_left = 365 - day_of_year
    if now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0):
        days_left = 366 - day_of_year
    return day_of_year, days_left

# ════════════════════════════════════════
#  СБОРКА ГАЗЕТКИ
# ════════════════════════════════════════
def build_gazette():
    now = datetime.now()
    day = now.day
    month = now.month
    season = get_season(month)
    weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    weekday = weekdays[now.weekday()]
    months_gen = ["января", "февраля", "марта", "апреля", "мая", "июня",
                  "июля", "августа", "сентября", "октября", "ноября", "декабря"]

    # Заголовок
    parts = []
    parts.append("🌙 *Газета Холодной Луны*\n")
    parts.append(f"📅 Выпуск от {day} {months_gen[month-1]} {now.year} года · {weekday}")
    parts.append(SEPARATOR)

    # Приветственное четверостишие
    poems_data = load_json("poems.json")
    if season in poems_data and poems_data[season]:
        poem = random.choice(poems_data[season])
    else:
        poem = "Утро настало, день начался,\nСветом наполнен мир вокруг.\nПусть этот день добром отозвался,\nПусть будет другом ваш круг!"
    parts.append(format_poem(poem))
    parts.append(SEPARATOR)

    # День в истории
    parts.append(f"### 📅 День в истории — {day} {months_gen[month-1]}\n")
    history = get_history_events(day, month)
    parts.append(history)

    # Праздники
    holidays = get_holidays(day, month)
    if holidays:
        parts.append(f"\n🎉 Сегодня также: {holidays}")

    parts.append(SEPARATOR)

    # Интересный факт
    facts = load_lines("facts.txt")
    if facts:
        fact = random.choice(facts)
    else:
        fact = "Каждый день узнавать новое — уже факт!"
    parts.append(f"### 🔢 Интересный факт дня 🦋\n\n{fact}")
    parts.append(SEPARATOR)

    # Афоризм
    aphorisms = load_lines("aphorisms.txt")
    if aphorisms:
        aph = random.choice(aphorisms)
    else:
        aph = "Жизнь — это то, что с тобой происходит, пока ты строишь другие планы. — Джон Леннон"
    parts.append(f"### 💬 Афоризм дня 📝\n\n> 🍁 *{aph}*")
    parts.append(SEPARATOR)

    # Народные приметы
    omens = get_omens(day, month)
    parts.append(f"### 🌿 Народные приметы — {day} {months_gen[month-1]} 🌾\n\n{omens}")
    parts.append(SEPARATOR)

    # Именинники
    namedays = get_namedays(day, month)
    parts.append("### 🎂 Поздравляем именинников! 🎉\n")
    if namedays:
        parts.append(f"🥳 Сегодня свой день отмечают: *{namedays}* 🎊")
    else:
        parts.append("🥳 Сегодня именинников нет в базе 🎊")
    parts.append(SEPARATOR)

    # Загадка дня
    riddles_data = load_json("riddles.json")
    if riddles_data and "riddles" in riddles_data and riddles_data["riddles"]:
        riddle = random.choice(riddles_data["riddles"])
        question = riddle.get("question", "")
        answer = riddle.get("answer", "")
        parts.append(f"### 🧩 Загадка дня 🤔\n\n🍃\n*{question}*\n\n*Ответ в самом конце газетки...* 🤫")
        parts.append(SEPARATOR)

    # Анекдот
    jokes = load_lines("jokes.txt")
    if jokes:
        joke = random.choice(jokes)
    else:
        joke = "Жизнь — это тоже анекдот, просто длинный."
    parts.append(f"### 😄 Анекдот дня 😂\n\n{joke}")
    parts.append(SEPARATOR)

    # Число дня
    day_num, days_left = get_day_number()
    parts.append(f"### 📊 Число дня 🔢\n\n📅 Сегодня *{day_num}-й* день года. До Нового года осталось *{days_left} дней*! 🎄⏳")
    parts.append(SEPARATOR)

    # Финальное четверостишие-пожелание
    closing_data = load_json("closing_poems.json")
    if season in closing_data and closing_data[season]:
        closing = random.choice(closing_data[season])
    else:
        closing = "Пусть этот день вам радость несёт,\nСветлые мысли и тёплые встречи.\nПусть отступают печаль и заботы —\nУлыбка пусть в сердце всю ночь светит!"
    parts.append(format_closing_poem(closing))
    parts.append(SEPARATOR)

    # Ответ на загадку
    if riddles_data and "riddles" in riddles_data and riddles_data["riddles"]:
        parts.append(f"🔑 **Ответ на загадку:** {answer} 🍂")

    return "\n\n".join(parts)

# ════════════════════════════════════════
#  ОТПРАВКА В TELEGRAM
# ════════════════════════════════════════
def send_telegram(text):
    # Telegram ограничивает сообщение 4096 символами
    if len(text) <= 4096:
        _send_single(text)
    else:
        # Разбиваем по разделителям
        chunks = text.split(SEPARATOR)
        current = ""
        for i, chunk in enumerate(chunks):
            if i < len(chunks) - 1:
                chunk += SEPARATOR
            if len(current) + len(chunk) > 4000 and current:
                _send_single(current)
                current = chunk
            else:
                current += chunk + ("\n\n" if i < len(chunks) - 1 else "")
        if current:
            _send_single(current)

def _send_single(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if not result.get("ok"):
                print(f"[ERROR] Telegram API: {result}")
            else:
                print("[OK] Сообщение отправлено!")
    except Exception as e:
        print(f"[ERROR] Не удалось отправить: {e}")

# ════════════════════════════════════════
#  ПОЛУЧЕНИЕ CHAT_ID
# ════════════════════════════════════════
def get_chat_id():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    msg = update.get("message") or update.get("edited_message")
                    if msg and msg.get("chat"):
                        chat = msg["chat"]
                        print(f"\n✅ Найден chat_id: {chat['id']}")
                        print(f"   Имя: {chat.get('first_name', '')} {chat.get('last_name', '')}")
                        print(f"   Тип: {chat.get('type', '')}")
                        print(f"\nВпишите это значение в CHAT_ID в начале скрипта.")
                        return chat['id']
            print("\n⚠️  Не найдено сообщений. Отправьте боту /start в Telegram, затем запустите снова.")
    except Exception as e:
        print(f"[ERROR] {e}")

# ════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════
def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--get-id":
        get_chat_id()
        return

    if "ВСТАВЬТЕ" in BOT_TOKEN or "ВСТАВЬТЕ" in CHAT_ID:
        print("⚠️  Сначала впишите BOT_TOKEN и CHAT_ID в начале скрипта!")
        print("   1. Создайте бота в @BotFather, получите токен")
        print("   2. Отправьте боту /start в Telegram")
        print("   3. Запустите: python3 morning_gazette.py --get-id")
        print("   4. Впишите токен и chat_id в скрипт")
        return

    print("📅 Собираю газетку...")
    text = build_gazette()
    print(f"📝 Размер: {len(text)} символов")
    print("📨 Отправляю в Telegram...")
    send_telegram(text)

if __name__ == "__main__":
    main()

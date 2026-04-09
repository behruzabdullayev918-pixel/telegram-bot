import random
import sqlite3
import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN .env faylda topilmadi!")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def db_connect():
    conn = sqlite3.connect("bot_data.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                uid       INTEGER PRIMARY KEY,
                name      TEXT,
                username  TEXT,
                score     INTEGER DEFAULT 0,
                games     INTEGER DEFAULT 0,
                quizzes   INTEGER DEFAULT 0,
                joined_at TEXT
            )
        """)
        conn.commit()

def get_user(uid):
    with db_connect() as conn:
        return conn.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()

def upsert_user(uid, name, username):
    with db_connect() as conn:
        ex = conn.execute("SELECT uid FROM users WHERE uid=?", (uid,)).fetchone()
        if not ex:
            conn.execute(
                "INSERT INTO users (uid,name,username,joined_at) VALUES (?,?,?,?)",
                (uid, name, username, datetime.now().isoformat())
            )
        else:
            conn.execute("UPDATE users SET name=?,username=? WHERE uid=?", (name, username, uid))
        conn.commit()

def add_score(uid, pts=1):
    with db_connect() as conn:
        conn.execute("UPDATE users SET score=score+? WHERE uid=?", (pts, uid))
        conn.commit()

def inc_stat(uid, field):
    with db_connect() as conn:
        conn.execute(f"UPDATE users SET {field}={field}+1 WHERE uid=?", (uid,))
        conn.commit()

def get_top(limit=10):
    with db_connect() as conn:
        return conn.execute(
            "SELECT name, score, games, quizzes FROM users ORDER BY score DESC LIMIT ?", (limit,)
        ).fetchall()

QUIZ_QUESTIONS = [
    {"q": "O'zbekistonning poytaxti qaysi shahar?", "options": ["Samarqand", "Toshkent", "Buxoro", "Namangan"], "a": "B"},
    {"q": "Dunyoning eng baland tog'i qaysi?", "options": ["K2", "Kilimanjaro", "Everest", "Elbrus"], "a": "C"},
    {"q": "Nil daryosi qaysi qit'ada?", "options": ["Osiyo", "Yevropa", "Afrika", "Amerika"], "a": "C"},
    {"q": "Qaysi mamlakat aholisi eng ko'p?", "options": ["Rossiya", "Amerika", "Hindiston", "Xitoy"], "a": "D"},
    {"q": "Qaysi okean eng katta?", "options": ["Atlantik", "Hind", "Arktika", "Tinch"], "a": "D"},
    {"q": "O'zbekiston necha viloyatdan iborat?", "options": ["10", "12", "14", "16"], "a": "C"},
    {"q": "Samarqand qaysi daryoning bo'yida?", "options": ["Amudaryo", "Sirdaryo", "Zarafshon", "Chirchiq"], "a": "C"},
    {"q": "Qaysi davlat 'Quyosh chiqadigan mamlakat' deb ataladi?", "options": ["Xitoy", "Hindiston", "Koreya", "Yaponiya"], "a": "D"},
    {"q": "Evropaning eng uzun daryosi?", "options": ["Dunay", "Volga", "Reyn", "Temza"], "a": "B"},
    {"q": "Amir Temur qaysi yili tug'ilgan?", "options": ["1320", "1336", "1350", "1370"], "a": "B"},
    {"q": "Birinchi Jahon urushi qaysi yilda boshlangan?", "options": ["1910", "1912", "1914", "1916"], "a": "C"},
    {"q": "O'zbekiston mustaqillikni qachon oldi?", "options": ["1989", "1990", "1991", "1992"], "a": "C"},
    {"q": "Ulug'bek rasadxonasi qaysi shaharda?", "options": ["Buxoro", "Toshkent", "Samarqand", "Xiva"], "a": "C"},
    {"q": "Ikkinchi Jahon urushi qachon tugadi?", "options": ["1943", "1944", "1945", "1946"], "a": "C"},
    {"q": "Ibn Sino qaysi sohada mashhur?", "options": ["Astronomiya", "Matematika", "Tibbiyot", "Adabiyot"], "a": "C"},
    {"q": "Suv necha gradusda qaynaydi?", "options": ["90C", "95C", "100C", "105C"], "a": "C"},
    {"q": "Quyosh sistemasida nechta sayyora bor?", "options": ["7", "8", "9", "10"], "a": "B"},
    {"q": "Inson tanasida nechta suyak bor?", "options": ["186", "206", "226", "246"], "a": "B"},
    {"q": "Eng yirik hayvon qaysi?", "options": ["Fil", "Karkidon", "Ko'k kit", "Hipopotam"], "a": "C"},
    {"q": "Yorug'lik tezligi taxminan qancha?", "options": ["200 000 km/s", "300 000 km/s", "400 000 km/s", "500 000 km/s"], "a": "B"},
    {"q": "Qaysi element eng yengil?", "options": ["Geliy", "Vodorod", "Litiy", "Neon"], "a": "B"},
    {"q": "Futbol jamoasida nechta o'yinchi?", "options": ["9", "10", "11", "12"], "a": "C"},
    {"q": "Olimpiya o'yinlari necha yilda bir marta?", "options": ["2", "3", "4", "5"], "a": "C"},
    {"q": "2018 yil Jahon chempionati qayerda?", "options": ["Braziliya", "Germaniya", "Rossiya", "Qatar"], "a": "C"},
    {"q": "Shatranjda bir tomonda nechta dona?", "options": ["14", "16", "18", "20"], "a": "B"},
    {"q": "Internet qaysi yilda ixtiro qilingan?", "options": ["1969", "1979", "1989", "1999"], "a": "A"},
    {"q": "iPhone birinchi marta qaysi yilda chiqdi?", "options": ["2005", "2006", "2007", "2008"], "a": "C"},
    {"q": "Google qaysi yilda tashkil topgan?", "options": ["1996", "1997", "1998", "1999"], "a": "C"},
    {"q": "1 GB necha MB?", "options": ["512 MB", "1000 MB", "1024 MB", "2048 MB"], "a": "C"},
    {"q": "Python kim tomonidan yaratilgan?", "options": ["Bill Gates", "Guido van Rossum", "Linus Torvalds", "Dennis Ritchie"], "a": "B"},
    {"q": "O'zbekistonning milliy guli?", "options": ["Lola", "Nilufar", "Atirgul", "Boychechak"], "a": "B"},
    {"q": "Registon maydoni qaysi shaharda?", "options": ["Toshkent", "Buxoro", "Samarqand", "Xiva"], "a": "C"},
    {"q": "O'zbekistonning milliy valyutasi?", "options": ["Rubl", "Dollar", "Som", "Tenge"], "a": "C"},
    {"q": "Al-Xorazmiy qaysi soha olimi?", "options": ["Tibbiyot", "Fizika", "Matematika", "Kimyo"], "a": "C"},
    {"q": "Navro'z bayramining tarixi necha yillik?", "options": ["1000+", "2000+", "3000+", "500+"], "a": "C"},
    {"q": "Qaysi shahar uch din uchun muqaddas?", "options": ["Makka", "Rim", "Quddus", "Madina"], "a": "C"},
    {"q": "Eng tez yuguradigan hayvon?", "options": ["Sher", "Gepard", "Ot", "Quyon"], "a": "B"},
    {"q": "Qaysi vitamin quyosh nuri orqali hosil bo'ladi?", "options": ["A", "B", "C", "D"], "a": "D"},
    {"q": "Amerika mustaqillikni qaysi yilda e'lon qilgan?", "options": ["1770", "1774", "1776", "1780"], "a": "C"},
    {"q": "Dunyo bo'yicha eng ko'p gapiriluvchi til?", "options": ["Ingliz", "Ispan", "Mandarin", "Arab"], "a": "C"},
    {"q": "Qaysi planet Quyoshga eng yaqin?", "options": ["Venera", "Merkuriy", "Mars", "Yer"], "a": "B"},
    {"q": "Insonning normal tana harorati qancha?", "options": ["35.6", "36.6", "37.6", "38.6"], "a": "B"},
    {"q": "Dengiz suvining o'rtacha sho'rligi qancha?", "options": ["1.5%", "2.5%", "3.5%", "4.5%"], "a": "C"},
    {"q": "Qaysi mamlakat pizzani ixtiro qilgan?", "options": ["Fransiya", "Ispaniya", "Italiya", "Gretsiya"], "a": "C"},
    {"q": "Bakteriyalarni kim kashf etgan?", "options": ["Pastyor", "Flemming", "Leeuwenhoek", "Koch"], "a": "C"},
    {"q": "Yer yuzasining necha foizi suv?", "options": ["51%", "61%", "71%", "81%"], "a": "C"},
    {"q": "Qaysi hayvon eng uzoq yashaydi?", "options": ["Fil", "Toshbaqa", "Kit", "Timsoh"], "a": "B"},
    {"q": "Futbolda penalti qancha metrdan uriladi?", "options": ["9 m", "11 m", "12 m", "15 m"], "a": "B"},
    {"q": "Qaysi mamlakat Ayers Rock (Uluru)ga ega?", "options": ["Yangi Zelandiya", "Janubiy Afrika", "Avstraliya", "Braziliya"], "a": "C"},
]

WORD_CATEGORIES = {
    "Hayvonlar": ["sher", "fil", "ot", "it", "mushuk", "quyon", "bori", "tulki",
                  "ayiq", "maymun", "zebra", "gepard", "karkidon", "eshak",
                  "sigir", "echki", "qoy", "tovuq", "burgut", "ilon", "toshbaqa"],
    "Mevalar": ["olma", "nok", "orik", "shaftoli", "uzum", "qovun", "tarvuz",
                "anor", "anjir", "behi", "gilos", "olcha", "limon", "apelsin",
                "mandarin", "banan", "ananas", "mango", "kivi", "xurmo"],
    "Shaharlar": ["toshkent", "samarqand", "buxoro", "namangan", "andijon",
                  "fargona", "nukus", "qarshi", "termiz", "jizzax",
                  "navoiy", "urganch", "xiva", "moskva", "london", "parij",
                  "berlin", "dubai", "tokio", "pekin"],
    "Kasblar": ["shifokor", "oqituvchi", "muhandis", "haydovchi", "oshpaz",
                "dehqon", "dasturchi", "arxitektor", "rassom",
                "musiqachi", "sportchi", "jurnalist", "advokat", "pilot"],
    "Davlatlar": ["rossiya", "xitoy", "hindiston", "yaponiya", "germaniya",
                  "fransiya", "italiya", "ispaniya", "braziliya",
                  "kanada", "avstraliya", "turkiya", "eron", "qozogiston"],
}

MAIN_KB = ReplyKeyboardMarkup(
    [["O'yin", "Quiz"], ["Kino", "Reyting"], ["Natijam", "Yordam"]],
    resize_keyboard=True
)
LANG_KB = ReplyKeyboardMarkup([["O'zbek"]], resize_keyboard=True)
WORD_CAT_KB = ReplyKeyboardMarkup(
    [["Hayvonlar", "Mevalar"], ["Shaharlar", "Kasblar"], ["Davlatlar"], ["Orqaga"]],
    resize_keyboard=True
)

user_state = {}
quiz_data = {}
word_data = {}

def word_display(uid):
    d = word_data[uid]
    word = d["word"]
    displayed = " ".join([ch if ch in d["guessed"] else "_" for ch in word])
    lives = d["max_wrong"] - len(d["wrong"])
    wrong_str = ", ".join(d["wrong"]).upper() if d["wrong"] else "---"
    return (
        f"Kategoriya: {d['category']}\n"
        f"Harf soni: {len(word)}\n\n"
        f"Soz: {displayed.upper()}\n\n"
        f"Hayot: {'X' * len(d['wrong'])}{'O' * lives} ({lives} ta qoldi)\n"
        f"Xato harflar: {wrong_str}\n\n"
        f"Harf kiriting:"
    )

def word_is_solved(uid):
    d = word_data[uid]
    return all(ch in d["guessed"] for ch in d["word"])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    upsert_user(user.id, user.first_name, user.username or "")
    await update.message.reply_text("Tilni tanlang:", reply_markup=LANG_KB)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot qo'llanmasi\n\n"
        "O'yin - Soz topish (kategoriya tanlang, harflarni taxmin qiling) +3 ball\n"
        "Quiz - A/B/C/D variantli savollar +2 ball\n"
        "Kino - Kino qidirish\n"
        "Reyting - TOP 10\n"
        "Natijam - Statistika",
        reply_markup=MAIN_KB
    )

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    txt_lower = txt.lower().strip()
    user = update.message.from_user
    uid = user.id
    upsert_user(uid, user.first_name, user.username or "")

    if txt_lower in ["o'zbek", "/start"]:
        await update.message.reply_text(f"Salom, {user.first_name}! Nima qilamiz?", reply_markup=MAIN_KB)
        user_state.pop(uid, None)
        return

    if txt_lower == "orqaga":
        user_state.pop(uid, None)
        word_data.pop(uid, None)
        await update.message.reply_text("Asosiy menyu:", reply_markup=MAIN_KB)
        return

    if txt_lower == "o'yin":
        user_state[uid] = "word_cat"
        await update.message.reply_text("Soz topish o'yini!\nKategoriya tanlang:", reply_markup=WORD_CAT_KB)
        return

    cat_map = {"hayvonlar": "Hayvonlar", "mevalar": "Mevalar", "shaharlar": "Shaharlar",
               "kasblar": "Kasblar", "davlatlar": "Davlatlar"}

    if txt_lower in cat_map and user_state.get(uid) in ["word_cat", "word"]:
        category = cat_map[txt_lower]
        word = random.choice(WORD_CATEGORIES[category])
        word_data[uid] = {"category": category, "word": word, "guessed": set(), "wrong": [], "max_wrong": 6}
        user_state[uid] = "word"
        await update.message.reply_text(
            word_display(uid),
            reply_markup=ReplyKeyboardMarkup([["Orqaga"]], resize_keyboard=True)
        )
        return

    if user_state.get(uid) == "word":
        letter = txt_lower.strip()
        if len(letter) != 1 or not letter.isalpha():
            await update.message.reply_text("Faqat bitta harf kiriting!")
            return
        d = word_data[uid]
        if letter in d["guessed"] or letter in d["wrong"]:
            await update.message.reply_text("Bu harfni allaqachon kiritgansiz!")
            return
        if letter in d["word"]:
            d["guessed"].add(letter)
            if word_is_solved(uid):
                add_score(uid, 3)
                inc_stat(uid, "games")
                u = get_user(uid)
                user_state[uid] = "word_cat"
                await update.message.reply_text(
                    f"Barakalla! Soz: {d['word'].upper()}\n+3 ball! Jami: {u['score']} ball",
                    reply_markup=WORD_CAT_KB
                )
            else:
                await update.message.reply_text("To'g'ri harf!\n\n" + word_display(uid))
        else:
            d["wrong"].append(letter)
            if d["max_wrong"] - len(d["wrong"]) <= 0:
                inc_stat(uid, "games")
                user_state[uid] = "word_cat"
                await update.message.reply_text(f"Yutqazdingiz! Soz: {d['word'].upper()} edi.", reply_markup=WORD_CAT_KB)
            else:
                await update.message.reply_text("Xato harf!\n\n" + word_display(uid))
        return

    if txt_lower == "quiz":
        q = random.choice(QUIZ_QUESTIONS)
        quiz_data[uid] = dict(q)
        user_state[uid] = "quiz"
        opts = q["options"]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("A", callback_data=f"qz_{uid}_A"), InlineKeyboardButton("B", callback_data=f"qz_{uid}_B")],
            [InlineKeyboardButton("C", callback_data=f"qz_{uid}_C"), InlineKeyboardButton("D", callback_data=f"qz_{uid}_D")],
        ])
        await update.message.reply_text(
            f"Quiz savoli:\n\n{q['q']}\n\nA) {opts[0]}\nB) {opts[1]}\nC) {opts[2]}\nD) {opts[3]}",
            reply_markup=kb
        )
        return

    if txt_lower == "kino":
        user_state[uid] = "movie"
        await update.message.reply_text("Kino nomini yozing:")
        return

    if txt_lower == "reyting":
        top = get_top(10)
        if not top:
            await update.message.reply_text("Hali hech kim o'ynamagan.")
            return
        msg = "TOP 10 O'yinchilar\n\n"
        for i, row in enumerate(top):
            msg += f"{i+1}. {row['name']} - {row['score']} ball\n"
        await update.message.reply_text(msg)
        return

    if txt_lower == "natijam":
        u = get_user(uid)
        if not u:
            await update.message.reply_text("Avval /start bosing.")
            return
        await update.message.reply_text(
            f"{u['name']} - Statistika\n\nBall: {u['score']}\nOyinlar: {u['games']}\nQuiz: {u['quizzes']}\nQoshilgan: {u['joined_at'][:10]}"
        )
        return

    if txt_lower == "yordam":
        await help_cmd(update, context)
        return

    if user_state.get(uid) == "movie":
        encoded = txt.strip().replace(" ", "+")
        await update.message.reply_text(
            f"Havolalar:\n\nKinogo: https://kinogo.la/search/{encoded}\nHDRezka: https://rezka.ag/search/?do=search&subaction=search&q={encoded}\nGoogle: https://www.google.com/search?q={encoded}+kino",
            reply_markup=MAIN_KB, disable_web_page_preview=True
        )
        user_state.pop(uid, None)
        return

    await update.message.reply_text("Tugmalardan birini bosing:", reply_markup=MAIN_KB)

async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    if len(parts) != 3:
        return
    _, uid_str, chosen = parts
    uid = int(uid_str)
    if uid not in quiz_data:
        await query.message.reply_text("Savol topilmadi.")
        return
    q = quiz_data[uid]
    correct = q["a"]
    opts = q["options"]
    labels = ["A", "B", "C", "D"]
    correct_text = opts[labels.index(correct)]
    if chosen == correct:
        add_score(uid, 2)
        inc_stat(uid, "quizzes")
        u = get_user(uid)
        result = f"To'g'ri! +2 ball\nJami: {u['score']} ball"
    else:
        result = f"Xato!\nTo'g'ri javob: {correct}) {correct_text}"
    new_buttons = []
    for i in range(0, 4, 2):
        row = []
        for j in range(2):
            idx = i + j
            lbl = labels[idx]
            prefix = "V " if lbl == correct else ("X " if lbl == chosen else "")
            row.append(InlineKeyboardButton(f"{prefix}{lbl}) {opts[idx]}", callback_data="done"))
        new_buttons.append(row)
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(new_buttons))
    except Exception:
        pass
    await query.message.reply_text(result, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Keyingi savol -->", callback_data=f"next_{uid}")]]))
    quiz_data.pop(uid, None)
    user_state.pop(uid, None)

async def next_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = int(query.data.split("_")[1])
    q = random.choice(QUIZ_QUESTIONS)
    quiz_data[uid] = dict(q)
    opts = q["options"]
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("A", callback_data=f"qz_{uid}_A"), InlineKeyboardButton("B", callback_data=f"qz_{uid}_B")],
        [InlineKeyboardButton("C", callback_data=f"qz_{uid}_C"), InlineKeyboardButton("D", callback_data=f"qz_{uid}_D")],
    ])
    await query.message.reply_text(
        f"Quiz savoli:\n\n{q['q']}\n\nA) {opts[0]}\nB) {opts[1]}\nC) {opts[2]}\nD) {opts[3]}",
        reply_markup=kb
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_state.pop(uid, None)
    quiz_data.pop(uid, None)
    word_data.pop(uid, None)
    await update.message.reply_text("Toxtatildi.", reply_markup=MAIN_KB)

def main():
    init_db()
    logger.info("Bot ishga tushmoqda...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CallbackQueryHandler(next_quiz_callback, pattern=r"^next_"))
    app.add_handler(CallbackQueryHandler(quiz_callback, pattern=r"^qz_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    logger.info("Bot tayyor!")
    app.run_polling()

if __name__ == "__main__":
    main()
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
                uid INTEGER PRIMARY KEY, name TEXT, username TEXT,
                score INTEGER DEFAULT 0, games INTEGER DEFAULT 0,
                quizzes INTEGER DEFAULT 0, joined_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS asked_questions (
                uid INTEGER, qid INTEGER,
                PRIMARY KEY (uid, qid)
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
            conn.execute("INSERT INTO users (uid,name,username,joined_at) VALUES (?,?,?,?)",
                (uid, name, username, datetime.now().isoformat()))
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
 
def get_asked(uid):
    with db_connect() as conn:
        rows = conn.execute("SELECT qid FROM asked_questions WHERE uid=?", (uid,)).fetchall()
        return set(r["qid"] for r in rows)
 
def mark_asked(uid, qid):
    with db_connect() as conn:
        conn.execute("INSERT OR IGNORE INTO asked_questions (uid, qid) VALUES (?,?)", (uid, qid))
        conn.commit()
 
def reset_asked(uid):
    with db_connect() as conn:
        conn.execute("DELETE FROM asked_questions WHERE uid=?", (uid,))
        conn.commit()
 
def get_next_question(uid):
    asked = get_asked(uid)
    available = [i for i in range(len(QUIZ_QUESTIONS)) if i not in asked]
    if not available:
        reset_asked(uid)
        available = list(range(len(QUIZ_QUESTIONS)))
    idx = random.choice(available)
    mark_asked(uid, idx)
    return idx, QUIZ_QUESTIONS[idx]
 
# ─────────────────────────────────────────
# 200 TA QUIZ SAVOLI
# ─────────────────────────────────────────
QUIZ_QUESTIONS = [
    # GEOGRAFIYA (1-40)
    {"q": "O'zbekistonning poytaxti qaysi shahar?", "options": ["Samarqand", "Toshkent", "Buxoro", "Namangan"], "a": "B"},
    {"q": "Dunyoning eng baland tog'i qaysi?", "options": ["K2", "Kilimanjaro", "Everest", "Elbrus"], "a": "C"},
    {"q": "Nil daryosi qaysi qit'ada joylashgan?", "options": ["Osiyo", "Yevropa", "Afrika", "Amerika"], "a": "C"},
    {"q": "Qaysi mamlakat aholisi eng ko'p?", "options": ["Rossiya", "Amerika", "Hindiston", "Xitoy"], "a": "D"},
    {"q": "Qaysi okean eng katta?", "options": ["Atlantik", "Hind", "Arktika", "Tinch"], "a": "D"},
    {"q": "O'zbekiston necha viloyatdan iborat?", "options": ["10", "12", "14", "16"], "a": "C"},
    {"q": "Samarqand qaysi daryoning bo'yida joylashgan?", "options": ["Amudaryo", "Sirdaryo", "Zarafshon", "Chirchiq"], "a": "C"},
    {"q": "Qaysi davlat 'Quyosh chiqadigan mamlakat' deb ataladi?", "options": ["Xitoy", "Hindiston", "Koreya", "Yaponiya"], "a": "D"},
    {"q": "Evropaning eng uzun daryosi qaysi?", "options": ["Dunay", "Volga", "Reyn", "Temza"], "a": "B"},
    {"q": "Dunyodagi eng katta cho'l qaysi?", "options": ["Gobi", "Sahara", "Kalahari", "Arabiston"], "a": "B"},
    {"q": "Braziliyaning poytaxti qaysi shahar?", "options": ["Rio de Janeiro", "San-Paulo", "Braziliya", "Salvador"], "a": "C"},
    {"q": "Qaysi mamlakat dunyodagi eng katta?", "options": ["Kanada", "Xitoy", "Amerika", "Rossiya"], "a": "D"},
    {"q": "Kavkaz tog'larining eng baland cho'qqisi?", "options": ["Kazbek", "Elbrus", "Ararat", "Shuxa"], "a": "B"},
    {"q": "Hindiston qaysi okean yonida joylashgan?", "options": ["Atlantik", "Tinch", "Hind", "Arktika"], "a": "C"},
    {"q": "Qaysi qit'ada aholi eng kam?", "options": ["Afrika", "Antarktida", "Janubiy Amerika", "Avstraliya"], "a": "B"},
    {"q": "O'rta dengiz qaysi qit'alar orasida joylashgan?", "options": ["Osiyo-Afrika", "Yevropa-Afrika-Osiyo", "Yevropa-Amerika", "Osiyo-Amerika"], "a": "B"},
    {"q": "Yangi Zelandiya qaysi okean orolida joylashgan?", "options": ["Atlantik", "Hind", "Tinch", "Arktika"], "a": "C"},
    {"q": "Qaysi mamlakat Skandinaviya yarim orolida joylashgan?", "options": ["Finlandiya", "Daniya", "Shvetsiya", "Islandiya"], "a": "C"},
    {"q": "Amazon daryosi qaysi mamlakatda joylashgan?", "options": ["Argentina", "Braziliya", "Kolumbiya", "Peru"], "a": "B"},
    {"q": "Qaysi shahar Fransiyaning poytaxti?", "options": ["Lion", "Parij", "Marsel", "Bordo"], "a": "B"},
    {"q": "Qaysi dengiz dunyoda eng sho'r?", "options": ["Qizil dengiz", "O'lik dengiz", "Kaspiy", "Qora dengiz"], "a": "B"},
    {"q": "Ispaniyaning poytaxti qaysi shahar?", "options": ["Barselona", "Valensiya", "Madrid", "Sevilla"], "a": "C"},
    {"q": "Qaysi mamlakat ikkita qit'ada joylashgan?", "options": ["Rossiya", "Turkiya", "Eron", "Xitoy"], "a": "B"},
    {"q": "Buyuk Britaniyaning poytaxti?", "options": ["Manchester", "Birmingem", "London", "Glazgo"], "a": "C"},
    {"q": "Dunyo bo'yicha eng katta orol qaysi?", "options": ["Grenvladiya", "Borneo", "Madagaskar", "Yangi Gvineya"], "a": "A"},
    {"q": "O'zbekiston qaysi dengizga chiqishi yo'q?", "options": ["Kaspiy", "Orol", "Qora", "Barcha dengizlarga"], "a": "D"},
    {"q": "Qaysi shahar Italiyaning poytaxti?", "options": ["Milan", "Venetsiya", "Rim", "Florensiya"], "a": "C"},
    {"q": "Niderlandiyaning poytaxti qaysi shahar?", "options": ["Rotterdam", "Gaga", "Amsterdam", "Leyden"], "a": "C"},
    {"q": "Qaysi mamlakatda Nil daryosi boshlanadi?", "options": ["Misr", "Sudan", "Efiopiya", "Uganda"], "a": "C"},
    {"q": "Dunyo bo'yicha eng baland shahar qaysi?", "options": ["Bogota", "La-Pas", "Kito", "Addis-Abeba"], "a": "B"},
    {"q": "Qaysi qit'ada Sahara cho'li joylashgan?", "options": ["Osiyo", "Yevropa", "Afrika", "Amerika"], "a": "C"},
    {"q": "Germaniyaning poytaxti qaysi shahar?", "options": ["Myunxen", "Frankfurt", "Berlin", "Gamburg"], "a": "C"},
    {"q": "Qaysi mamlakat Skandinaviyada joylashgan emas?", "options": ["Norvegiya", "Finlandiya", "Daniya", "Islandiya"], "a": "D"},
    {"q": "O'zbekistonning eng baland tog'i qaysi?", "options": ["Chimyon", "Xazrat Sultan", "Beshtor", "Muztog'"], "a": "B"},
    {"q": "Xitoyning poytaxti qaysi shahar?", "options": ["Shanxay", "Pekin", "Guangzhou", "Chongqing"], "a": "B"},
    {"q": "Qaysi daryo dunyoda eng uzun?", "options": ["Amazon", "Nil", "Yanszee", "Missisipi"], "a": "B"},
    {"q": "Kanada qaysi mamlakatga chegaradosh?", "options": ["Meksika", "Amerika", "Braziliya", "Argentina"], "a": "B"},
    {"q": "Avstraliyaning poytaxti qaysi shahar?", "options": ["Sidney", "Melburn", "Kanberra", "Brisben"], "a": "C"},
    {"q": "Qaysi shahar Toshkent bilan birlashtirilgan qadimiy shahar?", "options": ["Shosh", "Mavrannahr", "Turon", "Sohibqiron"], "a": "A"},
    {"q": "O'zbekiston qaysi yilda mustaqil bo'ldi?", "options": ["1989", "1990", "1991", "1992"], "a": "C"},
 
    # TARIX (41-80)
    {"q": "Amir Temur qaysi yili tug'ilgan?", "options": ["1320", "1336", "1350", "1370"], "a": "B"},
    {"q": "Birinchi Jahon urushi qaysi yilda boshlangan?", "options": ["1910", "1912", "1914", "1916"], "a": "C"},
    {"q": "Ikkinchi Jahon urushi qaysi yilda tugagan?", "options": ["1943", "1944", "1945", "1946"], "a": "C"},
    {"q": "Ulug'bek rasadxonasi qaysi shaharda qurilgan?", "options": ["Buxoro", "Toshkent", "Samarqand", "Xiva"], "a": "C"},
    {"q": "Qaysi imperator Buyuk Xitoy devorini qurdirgan?", "options": ["Chingizxon", "Qin Shi Huangdi", "Xubilayxon", "Temurxon"], "a": "B"},
    {"q": "Amerika qaysi yili mustaqilligini e'lon qilgan?", "options": ["1770", "1774", "1776", "1780"], "a": "C"},
    {"q": "Ibn Sino qaysi sohada mashhur?", "options": ["Astronomiya", "Matematika", "Tibbiyot", "Adabiyot"], "a": "C"},
    {"q": "Navro'z bayramining tarixi necha yillik?", "options": ["1000+", "2000+", "3000+", "500+"], "a": "C"},
    {"q": "Qaysi shahar uch din uchun muqaddas?", "options": ["Makka", "Rim", "Quddus", "Madina"], "a": "C"},
    {"q": "Al-Xorazmiy qaysi soha olimi?", "options": ["Tibbiyot", "Fizika", "Matematika", "Kimyo"], "a": "C"},
    {"q": "Bobur Mirzo qaysi shaharda tug'ilgan?", "options": ["Samarqand", "Andijon", "Buxoro", "Farg'ona"], "a": "B"},
    {"q": "Fransuz inqilobi qaysi yilda bo'lgan?", "options": ["1779", "1789", "1799", "1809"], "a": "B"},
    {"q": "Olimpiya o'yinlari qaysi mamlakatda boshlangan?", "options": ["Rim", "Gretsiya", "Misrda", "Xitoyda"], "a": "B"},
    {"q": "Chingizxon qaysi yili tug'ilgan?", "options": ["1152", "1162", "1172", "1182"], "a": "B"},
    {"q": "Qaysi davlat dunyoda birinchi bo'lib ayollarga ovoz berish huquqi bergan?", "options": ["Amerika", "Yangi Zelandiya", "Britaniya", "Fransiya"], "a": "B"},
    {"q": "Berlin devori qaysi yili qurilgan?", "options": ["1959", "1961", "1963", "1965"], "a": "B"},
    {"q": "Berlin devori qaysi yili qulab tushdi?", "options": ["1987", "1988", "1989", "1990"], "a": "C"},
    {"q": "Kolumb Amerikani qaysi yilda kashf etgan?", "options": ["1490", "1492", "1494", "1496"], "a": "B"},
    {"q": "Birinchi kosmosga chiqqan inson kim?", "options": ["Nil Armstrong", "Yuriy Gagarin", "Buzz Oldrin", "Alan Shepard"], "a": "B"},
    {"q": "Oyga birinchi qadam qo'ygan inson kim?", "options": ["Yuriy Gagarin", "Nil Armstrong", "Buzz Oldrin", "Alan Shepard"], "a": "B"},
    {"q": "Qaysi yilda birinchi kompyuter ixtiro qilingan?", "options": ["1936", "1941", "1946", "1951"], "a": "C"},
    {"q": "Temir yo'l qaysi mamlakatda ixtiro qilingan?", "options": ["Fransiya", "Amerika", "Germaniya", "Britaniya"], "a": "D"},
    {"q": "Gutenberg kimni kashf etgan?", "options": ["Telefon", "Bosma stanok", "Telegraf", "Radiot"], "a": "B"},
    {"q": "Qaysi yilda Birinchi Jahon urushi tugagan?", "options": ["1916", "1917", "1918", "1919"], "a": "C"},
    {"q": "Natsist Germaniyasi qaysi yilda mag'lub bo'lgan?", "options": ["1943", "1944", "1945", "1946"], "a": "C"},
    {"q": "Britaniya imperiyasi o'z cho'qqisida qancha aholini boshqargan?", "options": ["100 mln", "300 mln", "500 mln", "700 mln"], "a": "C"},
    {"q": "Qaysi yilda birinchi atom bombasi portlatilgan?", "options": ["1943", "1944", "1945", "1946"], "a": "C"},
    {"q": "Qaysi podshoh Magna Carta hujjatini imzolagan?", "options": ["Richard I", "Ioann I", "Genrix VIII", "Eduard I"], "a": "B"},
    {"q": "Rim imperiyasi qaysi yilda qulab tushgan?", "options": ["376", "476", "576", "676"], "a": "B"},
    {"q": "Qaysi yilda Rossiya inqilobi bo'lgan?", "options": ["1915", "1916", "1917", "1918"], "a": "C"},
    {"q": "Napoleon qaysi mamlakatda mag'lub bo'lgan?", "options": ["Angliya", "Rossiya", "Avstriya", "Prussiya"], "a": "B"},
    {"q": "Qaysi yilda Hindiston mustaqillikka erishgan?", "options": ["1945", "1946", "1947", "1948"], "a": "C"},
    {"q": "Temur imperiyasi poytaxti qaysi shahar?", "options": ["Buxoro", "Samarqand", "Toshkent", "Hirot"], "a": "B"},
    {"q": "Qaysi yilda Xitoy kommunistik davlatga aylangan?", "options": ["1947", "1948", "1949", "1950"], "a": "C"},
    {"q": "Qaysi yilda Ikkinchi Jahon urushi boshlangan?", "options": ["1937", "1938", "1939", "1940"], "a": "C"},
    {"q": "Kleopatra qaysi mamlakatda hukm surgan?", "options": ["Rim", "Gretsiya", "Misr", "Suriya"], "a": "C"},
    {"q": "Qaysi imperiya tarixda eng katta bo'lgan?", "options": ["Rim", "Mo'g'ul", "Britaniya", "Usmoniy"], "a": "C"},
    {"q": "Birinchi jahon urushida Germaniya kimga qarshi urush ochgan?", "options": ["Britaniya", "Fransiya", "Serbiya", "Rossiya"], "a": "C"},
    {"q": "Qaysi yilda NASA tashkil topgan?", "options": ["1956", "1957", "1958", "1959"], "a": "C"},
    {"q": "O'zbekistonda islom dini qachon tarqalgan?", "options": ["VII asr", "VIII asr", "IX asr", "X asr"], "a": "B"},
 
    # FAN VA TABIAT (81-120)
    {"q": "Suv necha gradusda qaynaydi?", "options": ["90C", "95C", "100C", "105C"], "a": "C"},
    {"q": "Quyosh sistemasida nechta sayyora bor?", "options": ["7", "8", "9", "10"], "a": "B"},
    {"q": "Inson tanasida nechta suyak bor?", "options": ["186", "206", "226", "246"], "a": "B"},
    {"q": "Eng yirik hayvon qaysi?", "options": ["Fil", "Karkidon", "Ko'k kit", "Hipopotam"], "a": "C"},
    {"q": "Yorug'lik tezligi taxminan qancha?", "options": ["200 000 km/s", "300 000 km/s", "400 000 km/s", "500 000 km/s"], "a": "B"},
    {"q": "DNA nima degani?", "options": ["Dinamik Nuklein Asidi", "Dezoksiribonuklein Asidi", "Dinatrium Asidi", "Dinamik Neyron Asidi"], "a": "B"},
    {"q": "Qaysi element eng yengil?", "options": ["Geliy", "Vodorod", "Litiy", "Neon"], "a": "B"},
    {"q": "Yer quyosh atrofida bir marta aylanishiga qancha vaqt ketadi?", "options": ["364 kun", "365 kun", "366 kun", "367 kun"], "a": "B"},
    {"q": "Qaysi vitamin quyosh nuri orqali hosil bo'ladi?", "options": ["Vitamin A", "Vitamin B", "Vitamin C", "Vitamin D"], "a": "D"},
    {"q": "Eng tez yuguradigan quruqlik hayvoni qaysi?", "options": ["Sher", "Gepard", "Ot", "Quyon"], "a": "B"},
    {"q": "Insonning normal tana harorati qancha?", "options": ["35.6", "36.6", "37.6", "38.6"], "a": "B"},
    {"q": "Qaysi planet Quyoshga eng yaqin?", "options": ["Venera", "Merkuriy", "Mars", "Yer"], "a": "B"},
    {"q": "Dengiz suvining o'rtacha sho'rligi qancha?", "options": ["1.5%", "2.5%", "3.5%", "4.5%"], "a": "C"},
    {"q": "Qaysi hayvon eng uzoq yashaydi?", "options": ["Fil", "Toshbaqa", "Kit", "Timsoh"], "a": "B"},
    {"q": "Quyosh sistemasining eng katta sayyorasi qaysi?", "options": ["Saturn", "Uran", "Neptun", "Yupiter"], "a": "D"},
    {"q": "Suv qanday formulaga ega?", "options": ["H2O2", "HO2", "H2O", "H3O"], "a": "C"},
    {"q": "Inson miyasi qancha foiz suvdan iborat?", "options": ["60%", "70%", "80%", "90%"], "a": "C"},
    {"q": "Qaysi element oltin deb ataladi?", "options": ["Ag", "Au", "Fe", "Cu"], "a": "B"},
    {"q": "Yorug'lik bir yilda qancha masofa bosib o'tadi?", "options": ["9.5 trillion km", "9.5 milliard km", "9.5 million km", "95 trillion km"], "a": "A"},
    {"q": "Qaysi gas atmosferada eng ko'p?", "options": ["Kislorod", "Vodorod", "Azot", "CO2"], "a": "C"},
    {"q": "Yer yuzasining necha foizi suv?", "options": ["51%", "61%", "71%", "81%"], "a": "C"},
    {"q": "Qaysi hayvon eng og'ir?", "options": ["Fil afrikasi", "Ko'k kit", "Karkidon", "Hipopotam"], "a": "B"},
    {"q": "Qaysi element simvoli Fe?", "options": ["Fosfor", "Ftor", "Temir", "Ferrum"], "a": "C"},
    {"q": "Qancha tezlikda tovush tarqaladi?", "options": ["243 m/s", "343 m/s", "443 m/s", "543 m/s"], "a": "B"},
    {"q": "Qaysi vitamin ko'rish uchun muhim?", "options": ["Vitamin A", "Vitamin B", "Vitamin C", "Vitamin D"], "a": "A"},
    {"q": "Insonning nechta dishi bor?", "options": ["28", "30", "32", "34"], "a": "C"},
    {"q": "Qaysi o'simlik dunyodagi eng baland?", "options": ["Sekoya", "Baobab", "Evkalipt", "Bambuk"], "a": "A"},
    {"q": "Qaysi metal eng yaxshi elektr o'tkazadi?", "options": ["Oltin", "Mis", "Kumush", "Alyuminiy"], "a": "C"},
    {"q": "Bir daqiqada yurak necha marta uradi?", "options": ["40-60", "60-80", "80-100", "100-120"], "a": "B"},
    {"q": "Qaysi havo elementi hayot uchun zarur?", "options": ["Azot", "CO2", "Kislorod", "Argon"], "a": "C"},
    {"q": "Qaysi sayyorada qo'ng'ilar bor?", "options": ["Saturn", "Yupiter", "Uran", "Neptun"], "a": "A"},
    {"q": "Gravitatsiya qonunini kim kashf etgan?", "options": ["Eynshteyn", "Nyuton", "Galiley", "Kepler"], "a": "B"},
    {"q": "Qaysi element kimyoviy belgisi Na?", "options": ["Neon", "Natriy", "Nikel", "Niobiy"], "a": "B"},
    {"q": "Bakteriyalarni kim kashf etgan?", "options": ["Pastyor", "Fleming", "Leeuwenhoek", "Koch"], "a": "C"},
    {"q": "Qaysi yilda Darvin evolyutsiya nazariyasini nashr etgan?", "options": ["1849", "1859", "1869", "1879"], "a": "B"},
    {"q": "Insonning nechta o'pkasi bor?", "options": ["1", "2", "3", "4"], "a": "B"},
    {"q": "Qaysi element simvoli Au?", "options": ["Kumush", "Oltin", "Mis", "Alyuminiy"], "a": "B"},
    {"q": "Quyosh necha yoshda?", "options": ["2.5 mlrd", "4.6 mlrd", "6.5 mlrd", "8 mlrd"], "a": "B"},
    {"q": "Qaysi o'simlik tezroq o'sadi?", "options": ["Bambuk", "Terak", "Evkalipt", "Qayin"], "a": "A"},
    {"q": "Qaysi meva aslida sabzavot hisoblanadi?", "options": ["Olma", "Banan", "Pomidor", "Uzum"], "a": "C"},
 
    # SPORT (121-150)
    {"q": "Futbol maydonida nechta o'yinchi bo'ladi (bir jamoada)?", "options": ["9", "10", "11", "12"], "a": "C"},
    {"q": "Olimpiya o'yinlari necha yilda bir marta o'tkaziladi?", "options": ["2", "3", "4", "5"], "a": "C"},
    {"q": "2018 yil Jahon chempionati qayerda bo'lgan?", "options": ["Braziliya", "Germaniya", "Rossiya", "Qatar"], "a": "C"},
    {"q": "2022 yil Jahon chempionati qayerda bo'lgan?", "options": ["Braziliya", "Germaniya", "Rossiya", "Qatar"], "a": "D"},
    {"q": "Shatranjda nechta dona bor (bir tomonda)?", "options": ["14", "16", "18", "20"], "a": "B"},
    {"q": "Voleibolda nechta to'siq qilish mumkin?", "options": ["1", "2", "3", "4"], "a": "C"},
    {"q": "Futbolda penalti qancha metrdan uriladi?", "options": ["9 m", "11 m", "12 m", "15 m"], "a": "B"},
    {"q": "Qaysi mamlakat eng ko'p Olimpiya medalini yutgan?", "options": ["Xitoy", "Rossiya", "Amerika", "Germaniya"], "a": "C"},
    {"q": "Tennis kortida to'r balandligi qancha?", "options": ["0.914 m", "1 m", "1.2 m", "0.5 m"], "a": "A"},
    {"q": "Basketbol to'p nechta bo'limdan iborat?", "options": ["6", "7", "8", "9"], "a": "C"},
    {"q": "Ronaldo qaysi mamlakatdan?", "options": ["Ispaniya", "Braziliya", "Portugaliya", "Argentina"], "a": "C"},
    {"q": "Messi qaysi mamlakatdan?", "options": ["Ispaniya", "Braziliya", "Portugaliya", "Argentina"], "a": "D"},
    {"q": "NBA qaysi mamlakatning basketbol ligasi?", "options": ["Kanada", "Amerika", "Britaniya", "Avstriya"], "a": "B"},
    {"q": "Formula 1 da poyga masofasi taxminan qancha?", "options": ["100 km", "200 km", "300 km", "400 km"], "a": "C"},
    {"q": "Qaysi davlat futbol bo'yicha Jahon chempionini eng ko'p bo'lgan?", "options": ["Germaniya", "Argentina", "Braziliya", "Italiya"], "a": "C"},
    {"q": "Tenniside Grand Slam necha turnirdan iborat?", "options": ["2", "3", "4", "5"], "a": "C"},
    {"q": "Boksda necha raund o'tkaziladi (professional)?", "options": ["8", "10", "12", "15"], "a": "C"},
    {"q": "Qaysi sport turi shlyapasi bilan o'ynaladi?", "options": ["Kriket", "Beysbol", "Regbi", "Xokkey"], "a": "B"},
    {"q": "Olimpiya o'yinlari bayrog'idagi halqalar nechtadan iborat?", "options": ["3", "4", "5", "6"], "a": "C"},
    {"q": "Qaysi mamlakat xokkey bo'yicha kuchliroq?", "options": ["Amerika", "Shvetsiya", "Kanada", "Finlandiya"], "a": "C"},
    {"q": "Suzishda eng mashhur uslub qaysi?", "options": ["Brus", "Krol", "Baqa", "Del'fin"], "a": "B"},
    {"q": "Qaysi sport turida 'hat-trick' degan ibora ishlatiladi?", "options": ["Basketbol", "Voleybol", "Futbol", "Tenis"], "a": "C"},
    {"q": "Wimbledon qaysi sport bo'yicha musobaqa?", "options": ["Golf", "Tennis", "Squash", "Badminton"], "a": "B"},
    {"q": "Qaysi yilda zamonaviy Olimpiya o'yinlari boshlangan?", "options": ["1892", "1896", "1900", "1904"], "a": "B"},
    {"q": "Futbolda o'yin necha daqiqa davom etadi?", "options": ["80", "90", "100", "120"], "a": "B"},
    {"q": "Qaysi mamlakat kriket bo'yicha kuchliroq?", "options": ["Angliya", "Hindiston", "Avstraliya", "Pokiston"], "a": "C"},
    {"q": "Marafon poygasi qancha masofaga?", "options": ["26.2 km", "36.2 km", "42.195 km", "52 km"], "a": "C"},
    {"q": "Qaysi yilda O'zbekiston birinchi Olimpiya medalini qo'lga kiritgan?", "options": ["1992", "1994", "1996", "1998"], "a": "A"},
    {"q": "Regbida jamoada nechta o'yinchi bo'ladi?", "options": ["11", "13", "15", "17"], "a": "C"},
    {"q": "Golf o'yinida nechta o'tish (hole) bo'ladi?", "options": ["9", "18", "27", "36"], "a": "B"},
 
    # TEXNOLOGIYA (151-180)
    {"q": "Internet qaysi yilda ixtiro qilingan?", "options": ["1969", "1979", "1989", "1999"], "a": "A"},
    {"q": "iPhone birinchi marta qaysi yilda chiqdi?", "options": ["2005", "2006", "2007", "2008"], "a": "C"},
    {"q": "Google qaysi yilda tashkil topgan?", "options": ["1996", "1997", "1998", "1999"], "a": "C"},
    {"q": "1 GB necha MB?", "options": ["512 MB", "1000 MB", "1024 MB", "2048 MB"], "a": "C"},
    {"q": "Python dasturlash tili kim tomonidan yaratilgan?", "options": ["Bill Gates", "Guido van Rossum", "Linus Torvalds", "Dennis Ritchie"], "a": "B"},
    {"q": "Birinchi kompyuter virus qaysi yilda paydo bo'lgan?", "options": ["1971", "1981", "1991", "2001"], "a": "A"},
    {"q": "Facebook qaysi yilda tashkil topgan?", "options": ["2002", "2003", "2004", "2005"], "a": "C"},
    {"q": "Microsoft kim tomonidan asos solingan?", "options": ["Stiv Jobs", "Bill Gates", "Mark Zukerberg", "Jeff Bezos"], "a": "B"},
    {"q": "Apple kompaniyasi qaysi yilda tashkil topgan?", "options": ["1974", "1975", "1976", "1977"], "a": "C"},
    {"q": "Linux operatsion tizimini kim yaratgan?", "options": ["Bill Gates", "Stiv Jobs", "Linus Torvalds", "Dennis Ritchie"], "a": "C"},
    {"q": "WWW qisqartmasi nima degani?", "options": ["World Wide Web", "World Wide Wire", "Wide World Web", "Web World Wide"], "a": "A"},
    {"q": "Birinchi smartfon qaysi yilda chiqdi?", "options": ["1992", "1994", "1996", "1998"], "a": "A"},
    {"q": "USB qisqartmasi nima degani?", "options": ["Universal System Bus", "Universal Serial Bus", "Unified Serial Bus", "United System Bus"], "a": "B"},
    {"q": "Amazon.com qaysi yilda tashkil topgan?", "options": ["1993", "1994", "1995", "1996"], "a": "B"},
    {"q": "Telegram ilovasi qaysi yilda yaratilgan?", "options": ["2011", "2012", "2013", "2014"], "a": "C"},
    {"q": "Birinchi sun'iy yo'ldosh qaysi yilda ishga tushirilgan?", "options": ["1955", "1957", "1959", "1961"], "a": "B"},
    {"q": "WiFi nima uchun ishlatiladi?", "options": ["Simsiz internet", "Simsiz telefon", "Simsiz TV", "Simsiz radio"], "a": "A"},
    {"q": "Qaysi kompaniya 'Galaxy' smartfonlar seriyasini chiqaradi?", "options": ["Apple", "Xiaomi", "Samsung", "Huawei"], "a": "C"},
    {"q": "YouTube qaysi yilda tashkil topgan?", "options": ["2003", "2004", "2005", "2006"], "a": "C"},
    {"q": "Qaysi dasturlash tili veb-saytlar uchun asosiy til?", "options": ["Python", "Java", "HTML", "C++"], "a": "C"},
    {"q": "GPS nima uchun ishlatiladi?", "options": ["Navigatsiya", "Aloqa", "Internet", "Kuzatuv"], "a": "A"},
    {"q": "Qaysi kompaniya Windows operatsion tizimini yaratgan?", "options": ["Apple", "Google", "Microsoft", "IBM"], "a": "C"},
    {"q": "Bluetooth qanday texnologiya?", "options": ["Simsiz ma'lumot uzatish", "Simsiz internet", "Simsiz telefon", "Simsiz kamera"], "a": "A"},
    {"q": "Qaysi yilda birinchi elektron pochta yuborilgan?", "options": ["1969", "1971", "1973", "1975"], "a": "B"},
    {"q": "Java dasturlash tilini kim yaratgan?", "options": ["Sun Microsystems", "Microsoft", "IBM", "Oracle"], "a": "A"},
    {"q": "Qaysi kompaniya Android tizimini yaratgan?", "options": ["Apple", "Microsoft", "Google", "Samsung"], "a": "C"},
    {"q": "1 TB necha GB?", "options": ["512 GB", "1000 GB", "1024 GB", "2048 GB"], "a": "C"},
    {"q": "Twitter qaysi yilda tashkil topgan?", "options": ["2004", "2005", "2006", "2007"], "a": "C"},
    {"q": "Qaysi texnologiya pul to'lashda ishlatiladi?", "options": ["Bluetooth", "WiFi", "NFC", "GPS"], "a": "C"},
    {"q": "Qaysi kompaniya PlayStation o'yin konsoli ishlab chiqaradi?", "options": ["Microsoft", "Nintendo", "Sony", "Sega"], "a": "C"},
 
    # O'ZBEKISTON VA MADANIYAT (181-200)
    {"q": "O'zbekistonning milliy guli qaysi?", "options": ["Lola", "Nilufar", "Atirgul", "Boychechak"], "a": "B"},
    {"q": "Registon maydoni qaysi shaharda joylashgan?", "options": ["Toshkent", "Buxoro", "Samarqand", "Xiva"], "a": "C"},
    {"q": "O'zbekistonning milliy valyutasi nima?", "options": ["Rubl", "Dollar", "So'm", "Tenge"], "a": "C"},
    {"q": "O'zbekistonda eng ko'p gaz qaysi viloyatda?", "options": ["Toshkent", "Farg'ona", "Buxoro", "Qashqadaryo"], "a": "D"},
    {"q": "Navoiy Alisher qaysi asarni yozgan?", "options": ["Boburnoma", "Xamsa", "Kutadg'u Bilig", "Devonu lug'otit turk"], "a": "B"},
    {"q": "O'zbekiston bayrog'idagi yulduzlar nechtadan iborat?", "options": ["8", "10", "12", "14"], "a": "C"},
    {"q": "Qaysi qo'shiq O'zbekistonning milliy madhiyasi?", "options": ["Mustaqillik madhiyasi", "O'zbekiston Respublikasining Davlat Madhiyasi", "Vatan madhiyasi", "Ona yurt madhiyasi"], "a": "B"},
    {"q": "O'zbekistonda nechta tabiiy iqlim zonasi bor?", "options": ["2", "3", "4", "5"], "a": "C"},
    {"q": "Toshkent metro qaysi yilda ochildi?", "options": ["1975", "1977", "1979", "1981"], "a": "B"},
    {"q": "O'zbekistonda qaysi sport turi milliy sport hisoblanadi?", "options": ["Futbol", "Ko'rash", "Tennis", "Boks"], "a": "B"},
    {"q": "O'zbekiston paxta ishlab chiqarishda dunyoda nechinchi o'rinda?", "options": ["3-5", "5-7", "7-10", "10-15"], "a": "B"},
    {"q": "Qaysi O'zbek olimi algebra fanini asos solgan?", "options": ["Ibn Sino", "Al-Xorazmiy", "Beruniy", "Ulug'bek"], "a": "B"},
    {"q": "O'zbekiston qaysi tashkilotga a'zo?", "options": ["NATO", "MDH", "EU", "ASEAN"], "a": "B"},
    {"q": "Beruniy qaysi sohada mashhur?", "options": ["Tibbiyot", "Matematika", "Tarix va Geografiya", "Musiqa"], "a": "C"},
    {"q": "O'zbekiston birinchi prezidenti kim?", "options": ["Shavkat Mirziyoyev", "Islam Karimov", "Abdulaziz Komilov", "Erkin Nishonov"], "a": "B"},
    {"q": "O'zbekistonning aholisi taxminan qancha?", "options": ["25 mln", "30 mln", "35 mln", "40 mln"], "a": "C"},
    {"q": "Qaysi O'zbekiston shahri UNESCO ro'yxatiga kiritilgan?", "options": ["Toshkent", "Buxoro", "Namangan", "Andijon"], "a": "B"},
    {"q": "O'zbekistonda milliy bayram — Mustaqillik kuni qaysi sana?", "options": ["1-sentyabr", "31-avgust", "9-may", "8-mart"], "a": "A"},
    {"q": "O'zbekiston nechta qo'shni mamlakatga ega?", "options": ["3", "4", "5", "6"], "a": "C"},
    {"q": "Qaysi O'zbekiston shahri 'Sharq darvozasi' deb ataladi?", "options": ["Samarqand", "Buxoro", "Toshkent", "Termiz"], "a": "A"},
]
 
# TOPISHMOQLAR
RIDDLES = {
    "sher": ("O'rmonda shoh, uni ko'rsa barcha qochadi. Bu kim?", "🦁"),
    "fil": ("Eng katta quruqlik hayvoni, uzun tumshug'i bor. Bu kim?", "🐘"),
    "ot": ("Odamlar minib yuradi, tez yuguradi, kishnavdi. Bu kim?", "🐴"),
    "it": ("Eng sodiq do'st, uyni qo'riqlaydi. Bu kim?", "🐶"),
    "mushuk": ("Miyov deydi, sichqon tutadi. Bu kim?", "🐱"),
    "quyon": ("Uzun quloqli, sakrab yuradi, sabzi yeydi. Bu kim?", "🐰"),
    "bori": ("Qo'ylarni qo'rqitadi, uvlaydi. Bu kim?", "🐺"),
    "tulki": ("Qizil mo'ynali, ayyor hayvon. Bu kim?", "🦊"),
    "ayiq": ("Yo'g'on, kuchli, asal yeydi, qishda uxlaydi. Bu kim?", "🐻"),
    "maymun": ("Daraxtda o'ynaydi, banan yeydi. Bu kim?", "🐵"),
    "zebra": ("Qora-oq chiziqli, otga o'xshaydi. Bu kim?", "🦓"),
    "gepard": ("Eng tez quruqlik hayvoni. Bu kim?", "🐆"),
    "karkidon": ("Burnida shoxi bor, katta hayvon. Bu kim?", "🦏"),
    "eshak": ("Og'ir yuk ko'taradi, ia-ia deydi. Bu kim?", "🫏"),
    "sigir": ("Sut beradi, mo'o deydi. Bu kim?", "🐄"),
    "echki": ("Me-me deydi, tog'da yuradi. Bu kim?", "🐐"),
    "qoy": ("Jun beradi, maa deydi. Bu kim?", "🐑"),
    "tovuq": ("Tuxum qo'yadi, qiq-qiq deydi. Bu kim?", "🐔"),
    "burgut": ("Osmonning shohi, o'tkir ko'zi bor. Bu kim?", "🦅"),
    "ilon": ("Oyoqsiz, sudralib yuradi. Bu kim?", "🐍"),
    "toshbaqa": ("Uyi o'zida, sekin yuradi. Bu kim?", "🐢"),
    "olma": ("Qizil yoki yashil, Newton boshiga tushgan. Bu nima?", "🍎"),
    "nok": ("Shakar kabi shirin, noksimon shakli bor. Bu nima?", "🍐"),
    "orik": ("Sariq, yozda pishadi, qoqi qilinadi. Bu nima?", "🍑"),
    "uzum": ("Tokchalarda osilib turadi. Bu nima?", "🍇"),
    "qovun": ("Sariq, yozda pishadi, ichidan oq va shirin. Bu nima?", "🍈"),
    "tarvuz": ("Yashil tashqi, qizil ichki. Bu nima?", "🍉"),
    "anor": ("Qizil donachali, foydali. Bu nima?", "🍎"),
    "gilos": ("Kichik, qizil, juft-juft osilib turadi. Bu nima?", "🍒"),
    "limon": ("Sariq, nordon, C vitamini ko'p. Bu nima?", "🍋"),
    "apelsin": ("To'q sariq, sharbati mashhur. Bu nima?", "🍊"),
    "banan": ("Sariq, egri, maymun yaxshi ko'radi. Bu nima?", "🍌"),
    "ananas": ("Tikanli po'chog'i, tropik meva. Bu nima?", "🍍"),
    "mango": ("Hindistonning milliy mevasi, juda shirin. Bu nima?", "🥭"),
    "kivi": ("Jigarrang tashqi, yashil ichki. Bu nima?", "🥝"),
    "toshkent": ("O'zbekistonning poytaxti. Bu qaysi shahar?", "🏙️"),
    "samarqand": ("Registon maydoni bor, Amir Temur poytaxti. Bu qaysi shahar?", "🕌"),
    "buxoro": ("Ko'k Gumbaz, madrasalar shahri. Bu qaysi shahar?", "🕌"),
    "xiva": ("Ichon Qala bor, qadimiy devorlar shahri. Bu qaysi shahar?", "🏰"),
    "london": ("Britaniyaning poytaxti, Big Ben bor. Bu qaysi shahar?", "🏙️"),
    "parij": ("Frantsiyaning poytaxti, Eyfel minorasi bor. Bu qaysi shahar?", "🗼"),
    "dubai": ("Burj Xalifa bu yerda. Bu qaysi shahar?", "🏙️"),
    "tokio": ("Yaponiyaning poytaxti. Bu qaysi shahar?", "🏙️"),
    "shifokor": ("Kasallarni davolaydi, oq xalat kiyadi. Bu kim?", "👨‍⚕️"),
    "oqituvchi": ("Bolalarga bilim beradi, maktabda ishlaydi. Bu kim?", "👨‍🏫"),
    "haydovchi": ("Mashina haydaydi, yo'lovchi tashiydi. Bu kim?", "🚗"),
    "oshpaz": ("Ovqat pishiradi, oshxonada ishlaydi. Bu kim?", "👨‍🍳"),
    "dasturchi": ("Kompyuter dasturlari yozadi. Bu kim?", "👨‍💻"),
    "pilot": ("Samolyot uchiradi, osmonda ishlaydi. Bu kim?", "✈️"),
    "rossiya": ("Dunyodagi eng katta mamlakat, poytaxti Moskva. Bu qaysi mamlakat?", "🇷🇺"),
    "xitoy": ("Aholisi eng ko'p, Buyuk devor bor. Bu qaysi mamlakat?", "🇨🇳"),
    "yaponiya": ("Quyosh chiqadigan mamlakat. Bu qaysi mamlakat?", "🇯🇵"),
    "italiya": ("Pizza va pasta vatani, Rim shahri bor. Bu qaysi mamlakat?", "🇮🇹"),
    "avstraliya": ("Kenguru va koala vatani. Bu qaysi mamlakat?", "🇦🇺"),
    "turkiya": ("Ikki qit'ada joylashgan, Istanbul bor. Bu qaysi mamlakat?", "🇹🇷"),
}
 
WORD_CATEGORIES = {
    "Hayvonlar": ["sher","fil","ot","it","mushuk","quyon","bori","tulki","ayiq","maymun","zebra","gepard","karkidon","eshak","sigir","echki","qoy","tovuq","burgut","ilon","toshbaqa"],
    "Mevalar": ["olma","nok","orik","uzum","qovun","tarvuz","anor","gilos","limon","apelsin","banan","ananas","mango","kivi"],
    "Shaharlar": ["toshkent","samarqand","buxoro","xiva","london","parij","dubai","tokio"],
    "Kasblar": ["shifokor","oqituvchi","haydovchi","oshpaz","dasturchi","pilot"],
    "Davlatlar": ["rossiya","xitoy","yaponiya","italiya","avstraliya","turkiya"],
}
 
WIN_ANIMS = ["🎉🎊🎉 BARAKALLA! 🎉🎊🎉","🌟⭐🌟 ZO'R! 🌟⭐🌟","🏆🥇🏆 AJOYIB! 🏆🥇🏆","🔥💫🔥 USTASIZ! 🔥💫🔥","✨🎯✨ MUKAMMAL! ✨🎯✨"]
LOSE_ANIMS = ["😢 Keyingi safar omad! 💪","😔 Ko'p mashq qiling! 📚","🙁 Xafa bo'lmang, yana urining! 🔄"]
OK_STICKERS = ["👍","✅","🎯","💪","🔥","⭐","🌟","🏅"]
BAD_STICKERS = ["❌","😅","🙈","💭","🤔"]
 
MAIN_KB = ReplyKeyboardMarkup(
    [["🎮 O'yin", "❓ Quiz"],["🎬 Kino", "🏆 Reyting"],["📊 Natijam", "ℹ️ Yordam"]],
    resize_keyboard=True
)
LANG_KB = ReplyKeyboardMarkup([["🇺🇿 O'zbek"]], resize_keyboard=True)
WORD_CAT_KB = ReplyKeyboardMarkup(
    [["🐾 Hayvonlar","🍎 Mevalar"],["🏙 Shaharlar","👷 Kasblar"],["🌍 Davlatlar"],["🔙 Orqaga"]],
    resize_keyboard=True
)
 
user_state = {}
quiz_data = {}
word_data = {}
 
def riddle_display(uid):
    d = word_data[uid]
    word = d["word"]
    riddle_text, emoji = RIDDLES.get(word, ("Bu so'zni toping!", "❓"))
    attempts = d.get("attempts", 0)
    max_a = d["max_attempts"]
    remaining = max_a - attempts
    progress = "❤️" * remaining + "🖤" * attempts
    revealed = d.get("revealed", set())
    displayed = " ".join([ch.upper() if ch in revealed else "❓" for ch in word])
    return (
        f"{emoji} *Topishmoq:*\n_{riddle_text}_\n\n"
        f"📝 So'z: `{displayed}`\n"
        f"🔢 Harf soni: *{len(word)}*\n\n"
        f"💓 {progress} (*{remaining}* urinish qoldi)\n\n"
        f"💡 /hint — yordam\nSo'zni yozing:"
    )
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    upsert_user(user.id, user.first_name, user.username or "")
    await update.message.reply_text("🌐 Tilni tanlang:", reply_markup=LANG_KB)
 
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Bot qo'llanmasi*\n\n"
        "🎮 *O'yin* — Topishmoq orqali so'z toping!\n"
        "  /hint — bitta harf ochiladi\n"
        "  To'g'ri topsa +3 ball ⭐\n\n"
        "❓ *Quiz* — 200 ta turli savol!\n"
        "  Savol takrorlanmaydi ✅\n"
        "  To'g'ri javob uchun +2 ball ⭐\n\n"
        "🎬 *Kino* — Kino qidirish\n"
        "🏆 *Reyting* — TOP 10 o'yinchi\n"
        "📊 *Natijam* — Statistikangiz",
        parse_mode="Markdown", reply_markup=MAIN_KB
    )
 
async def hint_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if user_state.get(uid) != "word":
        await update.message.reply_text("❗ Avval o'yin boshlang!")
        return
    d = word_data[uid]
    word = d["word"]
    revealed = d.setdefault("revealed", set())
    hidden = [ch for ch in word if ch not in revealed]
    if not hidden:
        await update.message.reply_text("Barcha harflar allaqachon ochilgan!")
        return
    letter = random.choice(hidden)
    revealed.add(letter)
    d["hints_used"] = d.get("hints_used", 0) + 1
    await update.message.reply_text(
        f"💡 Yordam: *'{letter.upper()}'* harfi ochildi!\n\n" + riddle_display(uid),
        parse_mode="Markdown"
    )
 
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    txt_lower = txt.lower().strip()
    user = update.message.from_user
    uid = user.id
    upsert_user(uid, user.first_name, user.username or "")
 
    if txt_lower in ["🇺🇿 o'zbek", "/start"]:
        await update.message.reply_text(
            f"👋 *Salom, {user.first_name}!* 🎮\nNima o'ynaylik?",
            parse_mode="Markdown", reply_markup=MAIN_KB
        )
        user_state.pop(uid, None)
        return
 
    if txt_lower in ["🔙 orqaga", "orqaga"]:
        user_state.pop(uid, None)
        word_data.pop(uid, None)
        await update.message.reply_text("🏠 Asosiy menyu:", reply_markup=MAIN_KB)
        return
 
    if txt_lower == "🎮 o'yin":
        user_state[uid] = "word_cat"
        await update.message.reply_text(
            "🎮 *Topishmoq o'yini!*\nKategoriya tanlang:",
            parse_mode="Markdown", reply_markup=WORD_CAT_KB
        )
        return
 
    cat_map = {
        "🐾 hayvonlar": "Hayvonlar", "🍎 mevalar": "Mevalar",
        "🏙 shaharlar": "Shaharlar", "👷 kasblar": "Kasblar", "🌍 davlatlar": "Davlatlar",
    }
 
    if txt_lower in cat_map and user_state.get(uid) in ["word_cat", "word"]:
        category = cat_map[txt_lower]
        words = [w for w in WORD_CATEGORIES.get(category, []) if w in RIDDLES]
        if not words:
            await update.message.reply_text("Bu kategoriyada so'z yo'q!")
            return
        word = random.choice(words)
        word_data[uid] = {"category": category, "word": word, "revealed": set(), "hints_used": 0, "attempts": 0, "max_attempts": 5}
        user_state[uid] = "word"
        riddle_text, emoji = RIDDLES[word]
        await update.message.reply_text(
            f"🎯 *Kategoriya:* {category}\n\n"
            f"{emoji} *Topishmoq:*\n_{riddle_text}_\n\n"
            f"📝 So'z: `{'❓ ' * len(word)}`\n"
            f"🔢 Harf soni: *{len(word)}*\n\n"
            f"❤️❤️❤️❤️❤️ (*5* urinish)\n\n"
            f"💡 /hint — yordam\nSo'zni yozing:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True)
        )
        return
 
    if user_state.get(uid) == "word":
        d = word_data[uid]
        word = d["word"]
        guess = txt_lower.strip()
        d["attempts"] = d.get("attempts", 0) + 1
        attempts = d["attempts"]
 
        if guess == word:
            pts = max(1, 4 - d.get("hints_used", 0))
            add_score(uid, pts)
            inc_stat(uid, "games")
            u = get_user(uid)
            _, emoji = RIDDLES.get(word, ("", "🎉"))
            user_state[uid] = "word_cat"
            await update.message.reply_text(
                f"{random.choice(WIN_ANIMS)}\n\n"
                f"{random.choice(OK_STICKERS)} *To'g'ri!* So'z: *{word.upper()}* {emoji}\n\n"
                f"💰 +{pts} ball!\n🏅 Jami: *{u['score']}* ball\n\nYana o'ynaysizmi?",
                parse_mode="Markdown", reply_markup=WORD_CAT_KB
            )
        elif attempts >= d["max_attempts"]:
            _, emoji = RIDDLES.get(word, ("", ""))
            inc_stat(uid, "games")
            user_state[uid] = "word_cat"
            await update.message.reply_text(
                f"{random.choice(LOSE_ANIMS)}\n\n"
                f"❌ *Urinishlar tugadi!*\nTo'g'ri so'z: *{word.upper()}* {emoji}\n\nYana urining! 💪",
                parse_mode="Markdown", reply_markup=WORD_CAT_KB
            )
        else:
            await update.message.reply_text(
                f"{random.choice(BAD_STICKERS)} *Noto'g'ri!* Yana urining.\n\n" + riddle_display(uid),
                parse_mode="Markdown"
            )
        return
 
    if txt_lower == "❓ quiz":
        idx, q = get_next_question(uid)
        quiz_data[uid] = {"idx": idx, **q}
        user_state[uid] = "quiz"
        opts = q["options"]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🅰 " + opts[0], callback_data=f"qz_{uid}_A"),
             InlineKeyboardButton("🅱 " + opts[1], callback_data=f"qz_{uid}_B")],
            [InlineKeyboardButton("🇨 " + opts[2], callback_data=f"qz_{uid}_C"),
             InlineKeyboardButton("🇩 " + opts[3], callback_data=f"qz_{uid}_D")],
        ])
        asked = get_asked(uid)
        total = len(QUIZ_QUESTIONS)
        done = len(asked)
        await update.message.reply_text(
            f"🧠 *Quiz savoli* ({done}/{total}):\n\n❓ {q['q']}\n\n"
            f"*A)* {opts[0]}\n*B)* {opts[1]}\n*C)* {opts[2]}\n*D)* {opts[3]}",
            parse_mode="Markdown", reply_markup=kb
        )
        return
 
    if txt_lower == "🎬 kino":
        user_state[uid] = "movie"
        await update.message.reply_text("🎬 Kino nomini yozing:")
        return
 
    if txt_lower == "🏆 reyting":
        top = get_top(10)
        if not top:
            await update.message.reply_text("Hali hech kim o'ynamagan.")
            return
        medals = ["🥇","🥈","🥉"] + ["🔹"]*7
        msg = "🏆 *TOP 10 O'yinchilar*\n\n"
        for i, row in enumerate(top):
            msg += f"{medals[i]} {row['name']} — *{row['score']}* ball\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return
 
    if txt_lower == "📊 natijam":
        u = get_user(uid)
        if not u:
            await update.message.reply_text("Avval /start bosing.")
            return
        asked = get_asked(uid)
        await update.message.reply_text(
            f"📊 *{u['name']} — Statistika*\n\n"
            f"⭐ Ball: *{u['score']}*\n🎮 O'yinlar: *{u['games']}*\n"
            f"❓ Quiz: *{u['quizzes']}*\n"
            f"📚 Javob berilgan savollar: *{len(asked)}/{len(QUIZ_QUESTIONS)}*\n"
            f"📅 Qo'shilgan: {u['joined_at'][:10]}",
            parse_mode="Markdown"
        )
        return
 
    if txt_lower == "ℹ️ yordam":
        await help_cmd(update, context)
        return
 
    if user_state.get(uid) == "movie":
        encoded = txt.strip().replace(" ", "+")
        await update.message.reply_text(
            f"🎬 *{txt.strip()}* uchun:\n\n"
            f"📺 [Kinogo](https://kinogo.la/search/{encoded})\n"
            f"🎞 [HDRezka](https://rezka.ag/search/?do=search&subaction=search&q={encoded})\n"
            f"🌐 [Google](https://www.google.com/search?q={encoded}+kino+uzbek)",
            parse_mode="Markdown", reply_markup=MAIN_KB, disable_web_page_preview=True
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
    labels = ["A","B","C","D"]
    correct_text = opts[labels.index(correct)]
 
    if chosen == correct:
        add_score(uid, 2)
        inc_stat(uid, "quizzes")
        u = get_user(uid)
        result = (f"{random.choice(WIN_ANIMS)}\n\n"
                  f"{random.choice(OK_STICKERS)} *To'g'ri!* +2 ball\n🏅 Jami: *{u['score']}* ball")
    else:
        result = f"{random.choice(BAD_STICKERS)} *Xato!*\nTo'g'ri javob: *{correct})* {correct_text}"
 
    new_buttons = []
    for i in range(0, 4, 2):
        row = []
        for j in range(2):
            idx = i + j
            lbl = labels[idx]
            prefix = "✅ " if lbl == correct else ("❌ " if lbl == chosen else "")
            row.append(InlineKeyboardButton(f"{prefix}{lbl}) {opts[idx]}", callback_data="done"))
        new_buttons.append(row)
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(new_buttons))
    except Exception:
        pass
 
    await query.message.reply_text(
        result, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Keyingi savol", callback_data=f"next_{uid}")]])
    )
    quiz_data.pop(uid, None)
    user_state.pop(uid, None)
 
async def next_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = int(query.data.split("_")[1])
    idx, q = get_next_question(uid)
    quiz_data[uid] = {"idx": idx, **q}
    user_state[uid] = "quiz"
    opts = q["options"]
    asked = get_asked(uid)
    total = len(QUIZ_QUESTIONS)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🅰 " + opts[0], callback_data=f"qz_{uid}_A"),
         InlineKeyboardButton("🅱 " + opts[1], callback_data=f"qz_{uid}_B")],
        [InlineKeyboardButton("🇨 " + opts[2], callback_data=f"qz_{uid}_C"),
         InlineKeyboardButton("🇩 " + opts[3], callback_data=f"qz_{uid}_D")],
    ])
    await query.message.reply_text(
        f"🧠 *Quiz savoli* ({len(asked)}/{total}):\n\n❓ {q['q']}\n\n"
        f"*A)* {opts[0]}\n*B)* {opts[1]}\n*C)* {opts[2]}\n*D)* {opts[3]}",
        parse_mode="Markdown", reply_markup=kb
    )
 
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_state.pop(uid, None)
    quiz_data.pop(uid, None)
    word_data.pop(uid, None)
    await update.message.reply_text("⏹ To'xtatildi.", reply_markup=MAIN_KB)
 
def main():
    init_db()
    logger.info("Bot ishga tushmoqda...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("hint", hint_cmd))
    app.add_handler(CallbackQueryHandler(next_quiz_callback, pattern=r"^next_"))
    app.add_handler(CallbackQueryHandler(quiz_callback, pattern=r"^qz_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    logger.info("Bot tayyor!")
    app.run_polling()
 
if __name__ == "__main__":
    main()

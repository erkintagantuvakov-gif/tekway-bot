#!/usr/bin/env python3
"""
Dubai Auksion | TEK AUTO MARKET - Telegram Bot v4
  - Sene barlagy (kone maglumat gorkezmeya)
  - Alert ulgamy (duwme + awtomat barlag)
  - USD hasap, unikal kod, WhatsApp deep link
"""
import asyncio
import json
import logging
import os
import re
from pathlib import Path
from urllib.parse import quote
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ============================================================
# SAZLAMALAR
# ============================================================
TOKEN = os.environ.get("BOT_TOKEN", "")
TEKWAY_WHATSAPP = "https://wa.me/971522371195"
TEKWAY_TELEGRAM = "https://t.me/+971522371195"
CARS_DB_FILE = Path("cars_database.json")

# Alert fayllary - Railway Volume bar bolsa /data
_DATA_DIR = Path("/data") if Path("/data").exists() else Path(".")
ALERTS_FILE = _DATA_DIR / "yatlatmas.json"
SENT_FILE = _DATA_DIR / "sent_alerts.json"
USERS_FILE = _DATA_DIR / "users.json"

# Admin - dine su ulanyjy /stats gorup bilya
ADMIN_ID = 8997411258

USD_RATE = 3.67

# --- Thread B: "Oye cenli baha" (Bugalter formulasy) ---
# HAZIR OCHUK. Sebabi: mashyn heniz utulmadyk, anyk baha yok.
# Bugalter anyk formula berende -> SHOW_HOME_PRICE = True et.
HOME_PRICE_EXTRA_USD = 2300
SHOW_HOME_PRICE = False   # True -> kartada gorkezer

DUBAI_TZ = timezone(timedelta(hours=4))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============================================================
# SENE BARLAGY
# ============================================================
def get_today():
    return datetime.now(DUBAI_TZ).strftime("%Y%m%d")


def db_is_fresh(cars):
    if not cars:
        return False
    today = get_today()
    dates = set(str(c.get("date", "")) for c in cars)
    if not dates:
        return False
    return max(dates) == today


NOT_READY_MSG = (
    "⏳ *Bugünki auksion maglumaty entek taýýar däl*\n\n"
    "Adatça her gün irden **07:00-10:00** aralygynda täzelenýär.\n"
    "Biraz soňra ýene synanyşyň.\n\n"
    "📱 Gyssagly sorag bolsa habarlaşyň:"
)


# ============================================================
# AUCTION KODLARY + USD
# ============================================================
AUCTION_CODES = {
    "Al Qaryah Auctions": "AQ",
    "Burj Khaibar Cars Auction": "BK",
    "West Cars Auctions": "WEST",
    "Marhaba Auctions": "MAR",
    "Marhaba Auction": "MAR",
    "Marhaba Auctions (Sajaa)": "MARS",
    "Fadak Cars Auction": "FAD",
    "Nojoom Cars Auction": "NCA",
    "Al Nukhbah Cars Auction": "NUKH",
    "Gulf Cars Auction": "GULF",
    "Al Buraq Cars Auction": "BUR",
    "Al Bashayera Auction": "BASH",
    "KHAT AL JAZEERA CARS AUCTION": "KHAT",
    "HAJI MOHD Cars Auctions": "HAJI",
    "Emirates Auction": "EM",
}


def get_car_code(car):
    """Günüň umumy kody: MMDD-NNN (mysal 0811-013).

    Kody `kod_ber.py` bazasyna ýazýar ("code" meýdany) — şoň üçin
    TikTok karty bilen Telegram bot DEŇ kody görkezýär.
    Müşderi "0811-013 gerek" diýse — botda gözlenip tapylýar.

    Bazada kod ýok bolsa (köne maglumat) — auksion prefiksli köne format.
    """
    code = car.get("code")
    if code:
        return str(code)

    # --- köne format (zapas) ---
    auction = car.get("auction", "")
    date_str = str(car.get("date", ""))
    page = car.get("page", 0)
    ac = AUCTION_CODES.get(auction, "AUCT")
    ds = date_str[4:8] if len(date_str) == 8 else "????"
    try:
        ps = f"{int(page):03d}"
    except (ValueError, TypeError):
        ps = "000"
    return f"{ac}-{ds}-{ps}"


def aed_to_usd(aed):
    try:
        return int(round(int(aed) / USD_RATE))
    except (ValueError, TypeError):
        return 0


# ============================================================
# DÜWMELER
# ============================================================
def contact_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📱 WhatsApp", url=TEKWAY_WHATSAPP),
        InlineKeyboardButton("✈️ Telegram", url=TEKWAY_TELEGRAM),
    ]])


def auction_keyboard_for_car(car):
    year = car.get("year", "")
    brand = car.get("brand", "")
    model = car.get("model", "")
    auction = car.get("auction", "")
    price = car.get("price", 0)
    code = get_car_code(car)

    text = "Salam! Şu maşyny gyzyklanýan:\n"
    text += f"🆔 Kod: {code}\n"
    text += f"🚗 {year} {brand} {model}\n"
    text += f"🏢 {auction}\n"
    if price:
        usd = aed_to_usd(price)
        text += f"💰 Başlanýan bahasy: {usd:,} USD ({price} AED)\n"
        if SHOW_HOME_PRICE:
            text += f"\U0001F3E0 Öýe çenli: ~{usd + HOME_PRICE_EXTRA_USD:,} USD-dan\n"
    img = car.get("image_path", "")
    if img:
        text += f"📸 https://raw.githubusercontent.com/erkintagantuvakov-gif/tekway-bot/main/{img}"

    wa_url = f"https://wa.me/971522371195?text={quote(text)}"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔨 Auksiona gatnaşyp ber", url=wa_url),
    ]])


# ============================================================
# BAZA
# ============================================================
def load_cars():
    if CARS_DB_FILE.exists():
        try:
            with open(CARS_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"DB okalmady: {e}")
    return []


def load_yatlatmas():
    if ALERTS_FILE.exists():
        try:
            with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_yatlatmas(y):
    try:
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(y, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"yatlatmas yazylmady: {e}")


def load_sent():
    if SENT_FILE.exists():
        try:
            with open(SENT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_sent(s):
    try:
        with open(SENT_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"sent yazylmady: {e}")




def load_users():
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_users(u):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(u, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"users yazylmady: {e}")


def track_user(update, query_text=""):
    """Her habar gelende ulanyjyny hasaba al"""
    try:
        u = update.effective_user
        if not u:
            return
        uid = str(u.id)
        users = load_users()
        now = datetime.now(DUBAI_TZ).strftime("%Y-%m-%d %H:%M")
        today = get_today()

        if uid not in users:
            users[uid] = {
                "name": (u.full_name or "")[:60],
                "username": u.username or "",
                "first_seen": now,
                "last_seen": now,
                "searches": 0,
                "days": [],
            }
        users[uid]["last_seen"] = now
        users[uid]["name"] = (u.full_name or "")[:60]
        if u.username:
            users[uid]["username"] = u.username
        if query_text:
            users[uid]["searches"] = users[uid].get("searches", 0) + 1
        days = users[uid].get("days", [])
        if today not in days:
            days.append(today)
            users[uid]["days"] = days[-60:]  # sonky 60 gun

        # Gozleg sozleri
        if query_text:
            q = users[uid].get("queries", [])
            q.append(query_text[:30])
            users[uid]["queries"] = q[-50:]

        save_users(users)
    except Exception as e:
        logger.error(f"track_user: {e}")

# ============================================================
# SURAT UGRATMAK
# ============================================================
def build_caption(car):
    cap = f"🚗 *{car.get('year')} {car.get('brand')} {car.get('model')}*\n"
    cap += f"🏢 {car.get('auction', '')}\n"
    if car.get("price"):
        usd = aed_to_usd(car.get("price"))
        cap += f"💰 Başlanýan bahasy: *{usd:,} USD* ({car.get('price')} AED)\n"
        if SHOW_HOME_PRICE:
            cap += f"\U0001F3E0 Öýe çenli: ~*{usd + HOME_PRICE_EXTRA_USD:,} USD*-dan\n"
    cap += f"🆔 Kod: `{get_car_code(car)}`"
    return cap


async def send_car_with_photo(update_or_message, car, keyboard=None):
    msg = update_or_message if hasattr(update_or_message, "reply_text") else update_or_message.message
    caption = build_caption(car)
    kb = keyboard or auction_keyboard_for_car(car)

    file_id = car.get("telegram_file_id", "")
    if file_id:
        try:
            await msg.reply_photo(photo=file_id, caption=caption, parse_mode="Markdown", reply_markup=kb)
            return
        except Exception as e:
            logger.error(f"file_id surat: {e}")

    image_path = car.get("image_path", "")
    if image_path and Path(image_path).exists():
        try:
            with open(image_path, "rb") as photo:
                await msg.reply_photo(photo=photo, caption=caption, parse_mode="Markdown", reply_markup=kb)
            return
        except Exception as e:
            logger.error(f"Surat ugratmady: {e}")

    await msg.reply_text(caption, parse_mode="Markdown", reply_markup=kb)


async def send_car_to_chat(bot, chat_id, car):
    caption = build_caption(car)
    kb = auction_keyboard_for_car(car)
    image_path = car.get("image_path", "")
    try:
        if image_path and Path(image_path).exists():
            with open(image_path, "rb") as photo:
                await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption,
                                     parse_mode="Markdown", reply_markup=kb)
                return
    except Exception as e:
        logger.error(f"Alert surat: {e}")
    await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown", reply_markup=kb)


# ============================================================
# KOMANDALAR
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚗 Maşyn gözle", callback_data="search")],
        [InlineKeyboardButton("🏢 Auksion gözle", callback_data="auction")],
        [InlineKeyboardButton("🔔 Ýatlatmalarym", callback_data="myalerts")],
        [InlineKeyboardButton("📱 Habarlaşmak", callback_data="contact")],
    ])
    await update.message.reply_text(
        "🚗 *Dubai Auksion | TEK AUTO MARKET*\n\n"
        "Salam! Men şu günki Dubaý auksionlarynyň maşynlaryny gözlemäge kömek edýärin.\n\n"
        "📌 Nähili ulanmaly:\n"
        "• Maşyn adyny ýaz — meselem: *Camry*, *Hilux*, *Elantra*\n"
        "• Auksion adyny ýaz — meselem: *Fadak*, *Marhaba*, *Nojoom*\n"
        "• Maşyn tapylmasa — düwme bilen ýatlatma goý\n"
        "• /help — ähli komandalar",
        parse_mode="Markdown", reply_markup=kb,
    )
    cars = load_cars()
    if not db_is_fresh(cars):
        await update.message.reply_text(NOT_READY_MSG, parse_mode="Markdown", reply_markup=contact_keyboard())
    try:
        asyncio.create_task(check_alerts(context.bot))
    except Exception:
        pass
    try:
        asyncio.create_task(check_alerts(context.bot))
    except Exception:
        pass


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Komandalar:*\n\n"
        "🚗 *Maşyn gözlemek:* `Camry`, `Hilux`, `Elantra`\n"
        "🏢 *Auksion gözlemek:* `Fadak`, `Marhaba`, `Nojoom`\n\n"
        "🔔 *Ýatlatma:* maşyn tapylmasa — düwmä bas\n"
        "📋 */myalerts* — ýatlatmalarym\n"
        "❌ */delalert Camry* — ýatlatmany poz\n"
        "❌ */delalert all* — hemmesini poz\n\n"
        "📊 */today* — şu günki ýagdaý\n"
        "📱 */contact* — habarlaş",
        parse_mode="Markdown",
    )


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cars = load_cars()
    if not cars or not db_is_fresh(cars):
        await update.message.reply_text(NOT_READY_MSG, parse_mode="Markdown", reply_markup=contact_keyboard())
        return
    counts = {}
    for c in cars:
        a = c.get("auction", "Näbelli")
        counts[a] = counts.get(a, 0) + 1
    text = "📅 *Şu günki auksionlar:*\n\n"
    for a, n in sorted(counts.items(), key=lambda x: -x[1]):
        text += f"🏢 *{a}* — {n} maşyn\n"
    text += f"\n✅ Jemi: *{len(cars)} maşyn*"
    await update.message.reply_text(text, parse_mode="Markdown")


async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📱 *TEK AUTO MARKET*\n\nHabarlaş:",
                                    parse_mode="Markdown", reply_markup=contact_keyboard())


async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🔔 `/alert Camry` — Camry çykanda habar ber\n\n"
            "Ýa-da maşyn gözläniňizde tapylmasa — düwmä basyň.",
            parse_mode="Markdown")
        return
    q = " ".join(context.args).upper()
    uid = str(update.effective_user.id)
    y = load_yatlatmas()
    y.setdefault(uid, [])
    if q not in y[uid]:
        y[uid].append(q)
        save_yatlatmas(y)
        await update.message.reply_text(f"✅ Ýatlatma goýuldy: *{q}*", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"ℹ️ Eýýäm bar: *{q}*", parse_mode="Markdown")


async def myalerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    my = load_yatlatmas().get(uid, [])
    if not my:
        await update.message.reply_text(
            "🔔 Sizde ýatlatma ýok.\n\nMaşyn gözläniňizde tapylmasa — düwme bilen goýup bilersiňiz.")
        return
    text = "🔔 *Siziň ýatlatmalaryňyz:*\n\n"
    for i, a in enumerate(my, 1):
        text += f"{i}. {a}\n"
    text += "\n❌ Pozmak: `/delalert <ady>`"
    await update.message.reply_text(text, parse_mode="Markdown")


async def delalert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ `/delalert Camry` — şony pozar\n`/delalert all` — hemmesini", parse_mode="Markdown")
        return
    uid = str(update.effective_user.id)
    y = load_yatlatmas()
    my = y.get(uid, [])
    arg = " ".join(context.args).upper()
    if arg == "ALL":
        y[uid] = []
        save_yatlatmas(y)
        await update.message.reply_text("✅ Ähli ýatlatmalar pozuldy.")
        return
    if arg in my:
        my.remove(arg)
        y[uid] = my
        save_yatlatmas(y)
        await update.message.reply_text(f"✅ Pozuldy: *{arg}*", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ *{arg}* tapylmady.", parse_mode="Markdown")




async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot statistikasy - dine ADMIN ucin"""
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        await update.message.reply_text("⛔ Bu komanda diňe admin üçin.")
        return

    users = load_users()
    if not users:
        await update.message.reply_text("📊 Entek ulanyjy ýok.")
        return

    today = get_today()
    from datetime import timedelta as _td
    now = datetime.now(DUBAI_TZ)
    week_days = set((now - _td(days=i)).strftime("%Y%m%d") for i in range(7))
    month_days = set((now - _td(days=i)).strftime("%Y%m%d") for i in range(30))

    total = len(users)
    today_active = sum(1 for u in users.values() if today in u.get("days", []))
    week_active = sum(1 for u in users.values() if week_days & set(u.get("days", [])))
    month_active = sum(1 for u in users.values() if month_days & set(u.get("days", [])))
    total_searches = sum(u.get("searches", 0) for u in users.values())

    # In kop gozlenen sozler
    from collections import Counter
    qc = Counter()
    for u in users.values():
        for q in u.get("queries", []):
            qc[q.upper()] += 1

    # Yatlatmalar
    y = load_yatlatmas()
    alert_users = sum(1 for v in y.values() if v)
    alert_total = sum(len(v) for v in y.values())

    txt = "📊 *BOT STATISTIKASY*\n\n"
    txt += f"👥 *Jemi ulanyjy:* {total}\n"
    txt += f"🟢 Bugün aktiw: {today_active}\n"
    txt += f"📅 Şu hepde: {week_active}\n"
    txt += f"📆 Şu aý: {month_active}\n\n"
    txt += f"🔍 Jemi gözleg: {total_searches}\n"
    txt += f"🔔 Ýatlatma goýan: {alert_users} ({alert_total} sany)\n"

    if qc:
        txt += "\n🔝 *Iň köp gözlenen:*\n"
        for w, n in qc.most_common(10):
            txt += f"   {w} — {n}\n"

    txt += "\n📋 /users — ulanyjylaryň sanawy"
    await update.message.reply_text(txt, parse_mode="Markdown")


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ulanyjylaryn sanawy - dine ADMIN"""
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        await update.message.reply_text("⛔ Bu komanda diňe admin üçin.")
        return

    users = load_users()
    if not users:
        await update.message.reply_text("📊 Entek ulanyjy ýok.")
        return

    # Sonky gelen boyunca sortla
    items = sorted(users.items(), key=lambda x: x[1].get("last_seen", ""), reverse=True)

    txt = f"👥 *Ulanyjylar ({len(items)}):*\n\n"
    for i, (uid_s, u) in enumerate(items[:40], 1):
        name = u.get("name", "?")
        un = f"@{u['username']}" if u.get("username") else ""
        s = u.get("searches", 0)
        last = u.get("last_seen", "")[:10]
        txt += f"{i}. {name} {un}\n   🔍{s} · {last}\n"

    if len(items) > 40:
        txt += f"\n... ýene {len(items)-40} sany"

    # Telegram habar cakleri - 4096 simwol
    if len(txt) > 3900:
        txt = txt[:3900] + "\n..."
    await update.message.reply_text(txt, parse_mode="Markdown")


# ============================================================
# ALERT BARLAG (background)
# ============================================================
async def check_alerts(bot):
    try:
        cars = load_cars()
        if not cars:
            logger.info("check_alerts: DB bos")
            return
        if not db_is_fresh(cars):
            logger.info(f"check_alerts: DB kone (today={get_today()})")
            return
        y = load_yatlatmas()
        if not y:
            logger.info(f"check_alerts: yatlatma yok ({ALERTS_FILE})")
            return
        logger.info(f"check_alerts: {len(y)} ulanyjy, {len(cars)} masyn")
        sent = load_sent()
        today = get_today()

        for uid, keywords in y.items():
            for kw in (keywords or []):
                kwu = kw.upper()
                matches = [c for c in cars
                           if kwu in f"{c.get('brand','')} {c.get('model','')}".upper()]
                if not matches:
                    continue
                key = f"{uid}|{kwu}|{today}"
                if sent.get(key):
                    continue
                try:
                    await bot.send_message(
                        chat_id=int(uid),
                        text=(f"🔔 *Ýatlatma!*\n\n"
                              f"Siziň gözlän maşynyňyz *{kw}* şu gün auksionda bar!\n"
                              f"Jemi: *{len(matches)}* sany"),
                        parse_mode="Markdown")
                    for car in matches[:5]:
                        await send_car_to_chat(bot, int(uid), car)
                    sent[key] = True
                    save_sent(sent)
                    logger.info(f"Alert: {uid} / {kw} / {len(matches)}")
                except Exception as e:
                    logger.error(f"Alert iberilmedi {uid}/{kw}: {e}")
    except Exception as e:
        logger.error(f"check_alerts: {e}")


async def alert_loop(app):
    await asyncio.sleep(60)
    while True:
        try:
            await check_alerts(app.bot)
        except Exception as e:
            logger.error(f"alert_loop: {e}")
        await asyncio.sleep(600)


async def post_init(app):
    asyncio.create_task(alert_loop(app))
    logger.info("Alert loop isledildi (her 10 min)")




async def checkalerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual alert barlag + debug maglumat"""
    uid = str(update.effective_user.id)
    cars = load_cars()
    y = load_yatlatmas()
    my = y.get(uid, [])
    sent = load_sent()
    today = get_today()

    txt = "🔍 *Alert debug:*\n\n"
    txt += f"📅 Bugün: `{today}`\n"
    txt += f"📦 DB: {len(cars)} maşyn\n"
    txt += f"✅ DB täze: {db_is_fresh(cars)}\n"
    txt += f"💾 Alert fayly: `{ALERTS_FILE}`\n"
    txt += f"🔔 Meniň ýatlatmalarym: {len(my)}\n"
    if my:
        for a in my:
            matches = [c for c in cars if a.upper() in f"{c.get('brand','')} {c.get('model','')}".upper()]
            key = f"{uid}|{a.upper()}|{today}"
            was_sent = "iberildi" if sent.get(key) else "iberilmedi"
            txt += f"   • {a}: {len(matches)} maşyn ({was_sent})\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

    # Hakyky barlag isle
    await check_alerts(context.bot)


# ============================================================
# HABAR
# ============================================================
AUCTIONS = {
    "fadak": "Fadak Cars Auction",
    "marhaba": "Marhaba Auctions",
    "nojoom": "Nojoom Cars Auction",
    "nca": "Nojoom Cars Auction",
    "qaryah": "Al Qaryah Auctions",
    "west": "West Cars Auctions",
    "gulf": "Gulf Cars Auction",
    "burj": "Burj Khaibar Cars Auction",
    "khaibar": "Burj Khaibar Cars Auction",
    "nukhbah": "Al Nukhbah Cars Auction",
    "bashayera": "Al Bashayera Auction",
    "khat": "KHAT AL JAZEERA CARS AUCTION",
    "haji": "HAJI MOHD Cars Auctions",
    "buraq": "Al Buraq Cars Auction",
}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    tl = text.lower()
    tu = text.upper()
    track_user(update, text)
    cars = load_cars()

    # Arka planda alertleri barla (blokirlemeya)
    try:
        asyncio.create_task(check_alerts(context.bot))
    except Exception as e:
        logger.error(f"alert task: {e}")

    # Arka planda alertleri barla (blokirlemeya)
    try:
        asyncio.create_task(check_alerts(context.bot))
    except Exception as e:
        logger.error(f"alert task: {e}")

    if not db_is_fresh(cars):
        await update.message.reply_text(NOT_READY_MSG, parse_mode="Markdown", reply_markup=contact_keyboard())
        return

    # --- KOD boýunça gözleg: "0811-013" ýa "13" ýa "TEK 0811-013" ---
    mcode = re.search(r'\b(\d{4})\s*[-–—/]\s*(\d{1,3})\b', tu)
    if mcode:
        want = f"{mcode.group(1)}-{int(mcode.group(2)):03d}"
        hit = [c for c in cars if str(c.get("code", "")).upper() == want]
        if hit:
            await update.message.reply_text(
                f"🆔 *{want}* — tapyldy:", parse_mode="Markdown")
            for car in hit:
                await send_car_with_photo(update, car)
            return
        await update.message.reply_text(
            f"📭 *{want}* kody bilen maşyn tapylmady.\n\n"
            "Kod her gün täzelenýär — düýnki koda şu gün maşyn ýok bolmagy mümkin.",
            parse_mode="Markdown", reply_markup=contact_keyboard())
        return

    for key, aname in AUCTIONS.items():
        if key in tl:
            ac = [c for c in cars if aname.upper() in c.get("auction", "").upper()]
            if not ac:
                await update.message.reply_text(f"📭 {aname}-da şu gün maşyn ýok.")
                return
            await update.message.reply_text(
                f"🏢 *{aname}* — {len(ac)} maşyn tapyldy:", parse_mode="Markdown")
            for car in ac[:100]:
                await send_car_with_photo(update, car)
            return

    found = [c for c in cars if tu in f"{c.get('brand','')} {c.get('model','')}".upper()]
    if not found:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"🔔 '{text[:30]}' çykanda habar ber",
                                 callback_data=f"alert:{text[:40]}")
        ]])
        await update.message.reply_text(
            f"📭 *'{text}'* şu gün ýok.\n\nÇykanda habar bermegimi isleýäňizmi?",
            parse_mode="Markdown", reply_markup=kb)
        return

    await update.message.reply_text(f"🚗 *'{text}'* — {len(found)} maşyn tapyldy:", parse_mode="Markdown")
    for car in found[:100]:
        await send_car_with_photo(update, car)


# ============================================================
# CALLBACK
# ============================================================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data or ""

    if d.startswith("alert:"):
        st = d[6:].strip()
        uid = str(q.from_user.id)
        y = load_yatlatmas()
        y.setdefault(uid, [])
        k = st.upper()
        if k not in y[uid]:
            y[uid].append(k)
            save_yatlatmas(y)
            await q.message.reply_text(
                f"✅ Ýatlatma goýuldy: *{st}*\n\n"
                f"Şol maşyn çykanda size habar bererin.\n"
                f"Ýatlatmalar: /myalerts",
                parse_mode="Markdown")
        else:
            await q.message.reply_text(f"ℹ️ *{st}* üçin ýatlatma eýýäm bar.", parse_mode="Markdown")

    elif d == "contact":
        await q.message.reply_text("📱 *TEK AUTO MARKET* bilen habarlaş:",
                                   parse_mode="Markdown", reply_markup=contact_keyboard())
    elif d == "search":
        await q.message.reply_text(
            "🚗 Haýsy maşyny gözleýäň? Adyny ýaz\nMeselem: *Camry*, *Hilux*, *Elantra*",
            parse_mode="Markdown")
    elif d == "auction":
        await q.message.reply_text(
            "🏢 Haýsy auksiony gözleýäň? Adyny ýaz\nMeselem: *Fadak*, *Marhaba*, *Nojoom*",
            parse_mode="Markdown")
    elif d == "myalerts":
        uid = str(q.from_user.id)
        my = load_yatlatmas().get(uid, [])
        if not my:
            await q.message.reply_text(
                "🔔 Sizde ýatlatma ýok.\n\nMaşyn gözläniňizde tapylmasa — düwme bilen goýup bilersiňiz.")
        else:
            t = "🔔 *Siziň ýatlatmalaryňyz:*\n\n"
            for i, a in enumerate(my, 1):
                t += f"{i}. {a}\n"
            t += "\n❌ Pozmak: `/delalert <ady>`"
            await q.message.reply_text(t, parse_mode="Markdown")


# ============================================================
# IŞLET
# ============================================================
def main():
    if not TOKEN:
        print("❌ BOT_TOKEN tapylmady!")
        return
    app = Application.builder().token(TOKEN).post_init(post_init).job_queue(None).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("contact", contact_command))
    app.add_handler(CommandHandler("alert", alert_command))
    app.add_handler(CommandHandler("myalerts", myalerts_command))
    app.add_handler(CommandHandler("delalert", delalert_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("checkalerts", checkalerts_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Dubai Auksion | TEK AUTO MARKET boty işläp başlady!")
    app.run_polling()


if __name__ == "__main__":
    main()

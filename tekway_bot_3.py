#!/usr/bin/env python3
"""
Dubai Auksion TEK WAY MOTORS — Telegram Bot v3
"""
import json
import logging
import os
from pathlib import Path
from urllib.parse import quote
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
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
ALERTS_FILE = Path("yatlatmas.json")
USD_RATE = 3.67

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# AUCTION KODLARY + USD
# ============================================================
AUCTION_CODES = {
    "Al Qaryah Auctions": "AQ",
    "Burj Khaibar Cars Auction": "BK",
    "West Cars Auctions": "WEST",
    "Marhaba Auctions": "MAR",
    "Marhaba Auction": "MAR",
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
    auction = car.get("auction", "")
    date_str = str(car.get("date", ""))
    page = car.get("page", 0)
    auction_code = AUCTION_CODES.get(auction, "AUCT")
    date_short = date_str[4:8] if len(date_str) == 8 else "????"
    try:
        page_str = f"{int(page):03d}"
    except (ValueError, TypeError):
        page_str = "000"
    return f"{auction_code}-{date_short}-{page_str}"


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
    """Konkret masyn ucin WhatsApp deep link (prefill text)"""
    year = car.get("year", "")
    brand = car.get("brand", "")
    model = car.get("model", "")
    auction = car.get("auction", "")
    price = car.get("price", 0)
    code = get_car_code(car)

    text = f"Salam! Şu maşyny gyzyklanýan:\n"
    text += f"🔢 Kod: {code}\n"
    text += f"🚗 {year} {brand} {model}\n"
    text += f"🏛 {auction}\n"
    if price:
        usd = aed_to_usd(price)
        text += f"💰 Başlanýan bahasy {price} AED / {usd} USD"

    encoded = quote(text)
    wa_url = f"https://wa.me/971522371195?text={encoded}"

    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔨 Auksiona gatnaşyp ber", url=wa_url),
    ]])


# ============================================================
# BAZA
# ============================================================
def load_cars():
    if CARS_DB_FILE.exists():
        with open(CARS_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_yatlatmas():
    if ALERTS_FILE.exists():
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_yatlatmas(yatlatmas):
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(yatlatmas, f, ensure_ascii=False, indent=2)


# ============================================================
# SURAT UGRATMAK
# ============================================================
async def send_car_with_photo(update_or_message, car, keyboard=None):
    msg = update_or_message if hasattr(update_or_message, "reply_text") else update_or_message.message

    caption = f"🚗 *{car.get('year')} {car.get('brand')} {car.get('model')}*\n"
    caption += f"🏛 {car.get('auction', '')}\n"
    if car.get("price"):
        usd = aed_to_usd(car.get("price"))
        caption += f"💰 Başlanýan bahasy {car.get('price')} AED / {usd} USD\n"
    caption += f"🔢 Kod: `{get_car_code(car)}`"

    kb = keyboard or auction_keyboard_for_car(car)

    file_id = car.get("telegram_file_id", "")
    if file_id:
        try:
            await msg.reply_photo(photo=file_id, caption=caption, parse_mode="Markdown", reply_markup=kb)
            return
        except Exception as e:
            logger.error(f"file_id bilen surat başartmady: {e}")

    image_path = car.get("image_path", "")
    if image_path and Path(image_path).exists():
        try:
            with open(image_path, "rb") as photo:
                await msg.reply_photo(photo=photo, caption=caption, parse_mode="Markdown", reply_markup=kb)
            return
        except Exception as e:
            logger.error(f"Surat ugratmak başartmady: {e}")

    await msg.reply_text(caption, parse_mode="Markdown", reply_markup=kb)


# ============================================================
# KOMANDALAR
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚗 Maşyn gözle", callback_data="search")],
        [InlineKeyboardButton("🏛 Auksion gözle", callback_data="auction")],
        [InlineKeyboardButton("🔔 Ýatlatma goý", callback_data="yatlatma")],
        [InlineKeyboardButton("📱 Habarlaşmak", callback_data="contact")],
    ])
    await update.message.reply_text(
        "🚗 *Dubai Auksion TEK WAY MOTORS*\n\n"
        "Salam! Men şu günki Dubaý auksionlarynyň maşynlaryny gözlemäge kömek edýärin.\n\n"
        "📌 Nähili ulanmaly:\n"
        "• Maşyn adyny ýaz — meselem: *Camry*, *Hilux*, *Elantra*\n"
        "• Auksion adyny ýaz — meselem: *Fadak*, *Marhaba*, *Nojoom*\n"
        "• /help — ähli komandalar",
        parse_mode="Markdown", reply_markup=keyboard,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Komandalar:*\n\n"
        "🚗 *Maşyn gözlemek:* `Camry`, `Hilux`, `Elantra`\n"
        "🏛 *Auksion gözlemek:* `Fadak`, `Marhaba`, `Nojoom`\n"
        "🔔 *Ýatlatma:* `/alert Camry`\n"
        "📊 */today* — şu günki ýagdaý\n"
        "📱 */contact* — habarlaş",
        parse_mode="Markdown",
    )


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cars = load_cars()
    if not cars:
        await update.message.reply_text("📭 Şu gün heniz auksion maglumaty ýok.")
        return
    auctions_today = {}
    for car in cars:
        a = car.get("auction", "Näbelli")
        auctions_today[a] = auctions_today.get(a, 0) + 1
    text = "📅 *Şu günki auksionlar:*\n\n"
    for a, c in auctions_today.items():
        text += f"🏛 *{a}* — {c} maşyn\n"
    text += f"\n✅ Jemi: *{len(cars)} maşyn*"
    await update.message.reply_text(text, parse_mode="Markdown")


async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 *TEK WAY MOTORS*\n\nHabarlaş:", parse_mode="Markdown", reply_markup=contact_keyboard()
    )


async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🔔 `/alert Camry` — Camry çykanda habar ber", parse_mode="Markdown"
        )
        return
    query = " ".join(context.args).upper()
    user_id = str(update.effective_user.id)
    yatlatmas = load_yatlatmas()
    if user_id not in yatlatmas:
        yatlatmas[user_id] = []
    if query not in yatlatmas[user_id]:
        yatlatmas[user_id].append(query)
        save_yatlatmas(yatlatmas)
        await update.message.reply_text(f"✅ Ýatlatma goýuldy: *{query}*", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"ℹ️ Eýýäm bar: *{query}*", parse_mode="Markdown")


# ============================================================
# HABAR
# ============================================================
AUCTIONS = {
    "fadak": "Fadak Cars Auction",
    "marhaba": "Marhaba Auctions",
    "nojoom": "Nojoom Cars Auction",
    "nca": "Nojoom Cars Auction",
    "qaryah": "Al Qaryah Auctions",
    "al qaryah": "Al Qaryah Auctions",
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
    text_lower = text.lower()
    text_upper = text.upper()
    cars = load_cars()

    # Auksion gozle
    for key, auction_name in AUCTIONS.items():
        if key in text_lower:
            auction_cars = [c for c in cars if auction_name.upper() in c.get("auction", "").upper()]
            if not auction_cars:
                await update.message.reply_text(f"📭 {auction_name}-da şu gün maşyn ýok.")
                return
            await update.message.reply_text(
                f"🏛 *{auction_name}* — {len(auction_cars)} maşyn tapyldy:", parse_mode="Markdown"
            )
            for car in auction_cars[:100]:
                await send_car_with_photo(update, car)
            return

    # Masyn gozle
    found = [c for c in cars if text_upper in f"{c.get('brand','')} {c.get('model','')}".upper()]
    if not found:
        await update.message.reply_text(
            f"📭 *'{text}'* şu gün ýok.\n\n🔔 `/alert {text}` ýaz - habar berjek",
            parse_mode="Markdown",
        )
        return
    await update.message.reply_text(
        f"🚗 *'{text}'* — {len(found)} maşyn tapyldy:", parse_mode="Markdown"
    )
    for car in found[:100]:
        await send_car_with_photo(update, car)


# ============================================================
# CALLBACK
# ============================================================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "contact":
        await query.message.reply_text(
            "📱 *TEK WAY MOTORS* bilen habarlaş:", parse_mode="Markdown", reply_markup=contact_keyboard()
        )
    elif query.data == "search":
        await query.message.reply_text(
            "🚗 Haýsy maşyny gözleýäň? Adyny ýaz\nMeselem: *Camry*, *Hilux*, *Elantra*",
            parse_mode="Markdown",
        )
    elif query.data == "auction":
        await query.message.reply_text(
            "🏛 Haýsy auksiony gözleýäň? Adyny ýaz\nMeselem: *Fadak*, *Marhaba*, *Nojoom*",
            parse_mode="Markdown",
        )
    elif query.data == "yatlatma":
        await query.message.reply_text(
            "🔔 `/alert Camry` ýaz — şol maşyn çykanda habar bereýin", parse_mode="Markdown"
        )


# ============================================================
# IŞLET
# ============================================================
def main():
    if not TOKEN:
        print("❌ BOT_TOKEN tapylmady!")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("contact", contact_command))
    app.add_handler(CommandHandler("alert", alert_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Dubai Auksion TEK WAY MOTORS boty işläp başlady!")
    app.run_polling()


if __name__ == "__main__":
    main()

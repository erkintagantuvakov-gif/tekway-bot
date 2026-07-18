#!/usr/bin/env python3
"""
Dubai Auksion TEK WAY MOTORS — Telegram Bot
Surat + maglumat ugradýar
"""

import json
import logging
import os
from pathlib import Path
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
ALERTS_FILE = Path("ýatlatmas.json")

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============================================================
# UNIKAL MASYN KODY
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
    """Auksion + sene + sahypa -> unikal kod (AQ-0718-052)"""
    auction = car.get('auction', '')
    date_str = str(car.get('date', ''))
    page = car.get('page', 0)

    auction_code = AUCTION_CODES.get(auction, 'AUCT')
    date_short = date_str[4:8] if len(date_str) == 8 else '????'

    try:
        page_str = f"{int(page):03d}"
    except (ValueError, TypeError):
        page_str = "000"

    return f"{auction_code}-{date_short}-{page_str}"

# ============================================================
# DÜWMELER
# ============================================================

def contact_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📱 WhatsApp", url=TEKWAY_WHATSAPP),
        InlineKeyboardButton("✈️ Telegram", url=TEKWAY_TELEGRAM),
    ]])

def auction_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔨 Auksiona gatnaşyp ber", callback_data="participate"),
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
    """Maşyny surat bilen ugrat"""
    msg = update_or_message if hasattr(update_or_message, 'reply_text') else update_or_message.message

    caption = (
        f"🚗 *{car.get('year')} {car.get('brand')} {car.get('model')}*\n"
        f"🏛 {car.get('auction', '')}\n"
    )
    if car.get('price'):
        caption += f"💰 Başlangyç baha: {car.get('price'):,} AED\n"
    caption += f"🔢 Kod: `{get_car_code(car)}`\n"

    # 1) telegram_file_id bar bolsa ilki şony ulan (iň çalt)
    file_id = car.get("telegram_file_id", "")
    if file_id:
        try:
            await msg.reply_photo(
                photo=file_id,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=keyboard or auction_keyboard()
            )
            return
        except Exception as e:
            logger.error(f"file_id bilen surat başartmady: {e}")

    # 2) Ýerli faýl bar bolsa
    image_path = car.get("image_path", "")
    if image_path and Path(image_path).exists():
        try:
            with open(image_path, "rb") as photo:
                await msg.reply_photo(
                    photo=photo,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=keyboard or auction_keyboard()
                )
            return
        except Exception as e:
            logger.error(f"Surat ugratmak başartmady: {e}")

    # 3) Surat ýok bolsa — tekst ugrat
    await msg.reply_text(caption, parse_mode="Markdown", reply_markup=keyboard or auction_keyboard())

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
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Komandalar:*\n\n"
        "🚗 *Maşyn gözlemek:*\n"
        "Göni maşyn adyny ýaz: `Camry`, `Hilux`, `Elantra`\n\n"
        "🏛 *Auksion gözlemek:*\n"
        "Auksion adyny ýaz: `Fadak`, `Marhaba`, `Nojoom`\n\n"
        "🔔 *Ýatlatma goýmak:*\n"
        "`/alert Camry` — Camry çykanda habar ber\n\n"
        "📊 *Şu günki ýagdaý:*\n"
        "/today — şu günki auksionlar\n\n"
        "📱 *Habarlaşmak:*\n"
        "/contact — TEK WAY MOTORS bilen habarlaş",
        parse_mode="Markdown"
    )

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cars = load_cars()
    if not cars:
        await update.message.reply_text("📭 Şu gün heniz auksion maglumaty ýok.\nHer gün irden täzelenir.")
        return

    auctions_today = {}
    for car in cars:
        auction = car.get("auction", "Näbelli")
        auctions_today[auction] = auctions_today.get(auction, 0) + 1

    text = "📅 *Şu günki auksionlar:*\n\n"
    for auction, count in auctions_today.items():
        text += f"🏛 *{auction}* — {count} maşyn\n"
    text += f"\n✅ Jemi: *{len(cars)} maşyn*"

    await update.message.reply_text(text, parse_mode="Markdown")

async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 *TEK WAY MOTORS*\n\nMaşyn satyn almak ýa-da sorag üçin habarlaş:",
        parse_mode="Markdown",
        reply_markup=contact_keyboard()
    )

async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🔔 Ýatlatma goýmak üçin:\n"
            "`/alert Camry` — Camry çykanda habar ber",
            parse_mode="Markdown"
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
        await update.message.reply_text(
            f"✅ Ýatlatma goýuldy: *{query}*\nŞol maşyn çykanda habar bereýin!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"ℹ️ Bu ýatlatma eýýäm bar: *{query}*",
            parse_mode="Markdown"
        )

# ============================================================
# HABAR IŞLEMEK
# ============================================================

AUCTIONS = {
    "fadak": "Fadak Cars Auction",
    "marhaba": "Marhaba Auction",
    "nojoom": "Nojoom Cars Auction",
    "emirates": "Emirates Auction",
    "qaryah": "Al Qaryah Auctions",
    "al qaryah": "Al Qaryah Auctions",
    "west": "West Cars Auctions",
    "gulf": "Gulf Cars Auction",
    "burj": "Burj Khaibar Cars Auction",
}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    text_lower = text.lower()
    text_upper = text.upper()
    cars = load_cars()

    # Auksion gözleg
    for key, auction_name in AUCTIONS.items():
        if key in text_lower:
            auction_cars = [c for c in cars if auction_name.upper() in c.get("auction", "").upper()]
            if not auction_cars:
                await update.message.reply_text(f"📭 {auction_name}-da şu gün maşyn ýok.")
                return

            await update.message.reply_text(
                f"🏛 *{auction_name}* — {len(auction_cars)} maşyn tapyldy:",
                parse_mode="Markdown"
            )
            for car in auction_cars[:100]:
                await send_car_with_photo(update, car)
            return

    # Maşyn gözleg
    found = [
        c for c in cars
        if text_upper in f"{c.get('brand','')} {c.get('model','')}".upper()
    ]

    if not found:
        await update.message.reply_text(
            f"📭 *'{text}'* şu gün ýok.\n\n🔔 Ýatlatma goýaýynmy? `/alert {text}` ýaz",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        f"🚗 *'{text}'* — {len(found)} maşyn tapyldy:",
        parse_mode="Markdown"
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
            "📱 *TEK WAY MOTORS* bilen habarlaş:",
            parse_mode="Markdown",
            reply_markup=contact_keyboard()
        )
    elif query.data == "participate":
        await query.message.reply_text(
            "🔨 *Auksiona gatnaşyp bereýin!*\n\nHabarlaş:",
            parse_mode="Markdown",
            reply_markup=contact_keyboard()
        )
    elif query.data == "search":
        await query.message.reply_text(
            "🚗 Haýsy maşyny gözleýäň? Adyny ýaz\nMeselem: *Camry*, *Hilux*, *Elantra*",
            parse_mode="Markdown"
        )
    elif query.data == "auction":
        await query.message.reply_text(
            "🏛 Haýsy auksiony gözleýäň? Adyny ýaz\nMeselem: *Fadak*, *Marhaba*, *Nojoom*",
            parse_mode="Markdown"
        )
    elif query.data == "yatlatma":
        await query.message.reply_text(
            "🔔 `/alert Camry` ýaz — şol maşyn çykanda habar bereýin",
            parse_mode="Markdown"
        )

# ============================================================
# IŞLET
# ============================================================

def main():
    if not TOKEN:
        print("❌ BOT_TOKEN tapylmady! Railway Environment Variables-a gir.")
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

#!/usr/bin/env python3
"""
Dubai Auksion TEK WAY MOTORS — Telegram Bot
"""

import json
import logging
from pathlib import Path
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

TOKEN = "8991271537:AAF1_NDfd1IwmlMuRPSOAixRQBROWEUqFbQ"
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
# HABARLAŞMAK DÜWMELERI
# ============================================================

def contact_keyboard():
    """WhatsApp + Telegram düwmeleri"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📱 WhatsApp", url=TEKWAY_WHATSAPP),
        InlineKeyboardButton("✈️ Telegram", url=TEKWAY_TELEGRAM),
    ]])

def auction_keyboard():
    """Auksiona gatnaşyp ber düwmesi"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔨 Auksiona gatnaşyp ber", callback_data="participate"),
    ]])

# ============================================================
# BAZA FUNKSIÝALARY
# ============================================================

def load_cars():
    if CARS_DB_FILE.exists():
        with open(CARS_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def load_ýatlatmas():
    if ALERTS_FILE.exists():
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_ýatlatmas(ýatlatmas):
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(ýatlatmas, f, ensure_ascii=False, indent=2)

# ============================================================
# AUKSIONLAR
# ============================================================

AUCTIONS = {
    "marhaba": "Marhaba Auction",
    "nojoom": "Nojoom Cars Auction",
    "emirates": "Emirates Auction",
    "al qaryah": "Al Qaryah Auctions",
    "qaryah": "Al Qaryah Auctions",
}

# ============================================================
# BOT KOMANDALAR
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚗 Maşyn gözle", callback_data="search")],
        [InlineKeyboardButton("🏛 Auksion gözle", callback_data="auction")],
        [InlineKeyboardButton("🔔 Ýatlatma goý", callback_data="ýatlatma")],
        [InlineKeyboardButton("📱 Habarlaşmak", callback_data="contact")],
    ])
    await update.message.reply_text(
        "🚗 *Dubai Auksion TEK WAY MOTORS*\n\n"
        "Salam! Men şu günki Dubaý auksionlarynyň maşynlaryny gözlemäge kömek edýärin.\n\n"
        "📌 Nähili ulanmaly:\n"
        "• Maşyn adyny ýaz — meselem: *Camry*, *Hilux*, *Elantra*\n"
        "• Auksion adyny ýaz — meselem: *Marhaba*, *Nojoom*\n"
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
        "Auksion adyny ýaz: `Marhaba`, `Nojoom`, `Emirates`\n\n"
        "🔔 *Ýatlatma goýmak:*\n"
        "`/alert Camry` — Camry çykanda habar ber\n\n"
        "📊 *Şu günki auksionlar:*\n"
        "/today — şu günki auksion tertibi\n\n"
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
            "`/alert Camry` — Camry çykanda habar ber\n"
            "`/alert Camry 2023` — 2023 Camry çykanda habar ber",
            parse_mode="Markdown"
        )
        return

    query = " ".join(context.args).upper()
    user_id = str(update.effective_user.id)
    ýatlatmas = load_ýatlatmas()
    if user_id not in ýatlatmas:
        ýatlatmas[user_id] = []

    if query not in ýatlatmas[user_id]:
        ýatlatmas[user_id].append(query)
        save_ýatlatmas(ýatlatmas)
        await update.message.reply_text(f"✅ Ýatlatma goýuldy: *{query}*\nŞol maşyn çykanda habar bereýin!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"ℹ️ Bu ýatlatma eýýäm bar: *{query}*", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    text_upper = text.upper()
    cars = load_cars()

    # Auksion gözleg
    for key, auction_name in AUCTIONS.items():
        if key in text.lower():
            auction_cars = [c for c in cars if auction_name.upper() in c.get("auction", "").upper()]
            if auction_cars:
                result = f"🏛 *{auction_name}* — {len(auction_cars)} maşyn\n\n"
                for c in auction_cars[:10]:
                    result += f"🚗 {c.get('year')} {c.get('brand')} {c.get('model')} — {c.get('price', 'N/A')} AED\n"
                await update.message.reply_text(result, parse_mode="Markdown", reply_markup=auction_keyboard())
            else:
                await update.message.reply_text(f"📭 {auction_name}-da şu gün maşyn ýok.")
            return

    # Maşyn gözleg
    found = [c for c in cars if text_upper in f"{c.get('brand','')} {c.get('model','')}".upper()]

    if found:
        result = f"🚗 *'{text}'* — {len(found)} maşyn tapyldy:\n\n"
        for c in found[:10]:
            result += f"• {c.get('year')} {c.get('brand')} {c.get('model')} — {c.get('price', 'N/A')} AED — {c.get('auction', '')}\n"
        await update.message.reply_text(result, parse_mode="Markdown", reply_markup=auction_keyboard())
    else:
        await update.message.reply_text(
            f"📭 *'{text}'* şu gün ýok.\n\n🔔 Ýatlatma goýaýynmy? `/alert {text}` ýaz",
            parse_mode="Markdown"
        )

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
        await query.message.reply_text("🚗 Haýsy maşyny gözleýäň? Adyny ýaz (meselem: *Camry*, *Hilux*)", parse_mode="Markdown")
    elif query.data == "auction":
        await query.message.reply_text("🏛 Haýsy auksiony gözleýäň? Adyny ýaz (meselem: *Marhaba*, *Nojoom*)", parse_mode="Markdown")
    elif query.data == "ýatlatma":
        await query.message.reply_text("🔔 `/alert Camry` ýaz — şol maşyn çykanda habar bereýin", parse_mode="Markdown")

# ============================================================
# BOTY IŞLETMEK
# ============================================================

def main():
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

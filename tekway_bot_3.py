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
# FUZZY GÖZLEG — ýalňyş / türkmençe / rusça ýazga çydamly
# (Erkiniň esasy derdi, board 12.08)
#   "kamry"  -> Camry      "hunday"  -> Hyundai
#   "karola" -> Corolla    "камри"   -> Camry
# ============================================================
import difflib

# türkmen we rus harplary -> latyn
_TM_TRANS = str.maketrans({
    "ý": "y", "Ý": "y", "ş": "s", "Ş": "s", "ç": "c", "Ç": "c",
    "ň": "n", "Ň": "n", "ä": "a", "Ä": "a", "ö": "o", "Ö": "o",
    "ü": "u", "Ü": "u", "ž": "z", "Ž": "z", "ı": "i", "İ": "i",
})
_CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _norm(s):
    """Ýazgyny deňeşdirmäge taýýarla: kiçi harp, diakritika ýok, diňe harp/san."""
    s = (s or "").strip().lower().translate(_TM_TRANS)
    s = "".join(_CYR.get(ch, ch) for ch in s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Adam ýazýan görnüş -> hakyky at.  Çepdäki söz NORMALIZE edilen bolmaly.
SYNONYMS = {
    # --- markalar ---
    "hunday": "hyundai", "hunda": "hyundai", "hyunday": "hyundai",
    "hendai": "hyundai", "handai": "hyundai", "hyndai": "hyundai",
    "henday": "hyundai", "hyenday": "hyundai", "hunday i": "hyundai",
    "tayota": "toyota", "toyata": "toyota", "toyot": "toyota",
    "nisan": "nissan", "nissa": "nissan", "nissan": "nissan",
    "kiya": "kia", "kija": "kia",
    "honda": "honda", "honde": "honda",
    "mersedes": "mercedes", "merc": "mercedes", "mers": "mercedes",
    "mercedes benz": "mercedes", "benz": "mercedes",
    "lexsus": "lexus", "leksus": "lexus", "leks": "lexus",
    "shevrole": "chevrolet", "shevrolye": "chevrolet", "chevrole": "chevrolet", "shevrolet": "chevrolet",
    "bmv": "bmw", "beemwe": "bmw",
    "folksvagen": "volkswagen", "folkswagen": "volkswagen", "vw": "volkswagen",
    "mazde": "mazda", "forud": "ford",
    # --- modeller ---
    "kamry": "camry", "kamri": "camry", "camri": "camry", "kemri": "camry",
    "karola": "corolla", "korolla": "corolla", "karolla": "corolla",
    "elantre": "elantra", "elantara": "elantra", "elentra": "elantra",
    "sonate": "sonata", "sanata": "sonata",
    "tuson": "tucson", "taksan": "tucson", "tukson": "tucson",
    "santafe": "santa fe", "santa fe": "santa fe", "santafey": "santa fe",
    "sorenta": "sorento", "sorrento": "sorento",
    "sportaj": "sportage", "sportage": "sportage",
    "altime": "altima", "altyma": "altima",
    "sentre": "sentra", "sentr": "sentra",
    "rogu": "rogue", "rog": "rogue",
    "kiks": "kicks",
    "seltas": "seltos",
    "forte": "forte", "fortey": "forte",
    "karnival": "carnival", "carnaval": "carnival",
    "sivik": "civic", "civik": "civic",
    "akkord": "accord", "akord": "accord",
    "malibu": "malibu", "malybu": "malibu",
    "prius": "prius", "priyus": "prius",
    "land kruzer": "land cruiser", "landkruzer": "land cruiser",
    "kruzak": "land cruiser", "krizer": "land cruiser",
    "prado": "prado", "parado": "prado",
    "hayls": "hilux", "hilaks": "hilux", "haylaks": "hilux",
    "rav": "rav4", "rav 4": "rav4", "raf4": "rav4",
    "haylender": "highlander", "haylander": "highlander",
    "avalon": "avalon", "awalon": "avalon",
    "maksima": "maxima",
    "aksent": "accent", "aksant": "accent",
    "tellurayd": "telluride",
}


def build_vocab(cars):
    """Bazadaky ähli marka/model sözlerini ýygna."""
    vocab = {}
    for c in cars:
        b = _norm(c.get("brand"))
        m = _norm(c.get("model"))
        for t in ([b] if b else []) + (m.split() if m else []):
            if len(t) >= 3:
                vocab[t] = vocab.get(t, 0) + 1
        if b and m:
            first = m.split()[0]
            if len(first) >= 3:
                key = f"{b} {first}"
                vocab[key] = vocab.get(key, 0) + 1
    return vocab


def fuzzy_find(query, cars):
    """(tapylan_soz, masynlar) gaytarya. Tapmasa (None, [])."""
    q = _norm(query)
    if not q or len(q) < 3:
        return None, []

    # 1. Göni sinonim
    target = SYNONYMS.get(q)

    # 2. Sözme-söz sinonim (mysal "gara kamry" -> "camry")
    if not target:
        for w in q.split():
            if w in SYNONYMS:
                target = SYNONYMS[w]
                break

    # 3. Meňzeşlik boýunça (ýalňyş harp, ýitirilen harp)
    if not target:
        vocab = build_vocab(cars)
        if not vocab:
            return None, []
        best, score = None, 0.0
        for cand in vocab:
            for piece in [q] + q.split():
                if len(piece) < 3:
                    continue
                r = difflib.SequenceMatcher(None, piece, cand).ratio()
                # sozun basy den gelse - bal gos
                if cand.startswith(piece[:3]) or piece.startswith(cand[:3]):
                    r += 0.06
                if r > score:
                    best, score = cand, r
        if score >= 0.78:
            target = best

    if not target:
        return None, []

    tn = _norm(target)
    found = [c for c in cars
             if tn in _norm(f"{c.get('brand','')} {c.get('model','')}")]
    if not found:
        # sinonim marka bolsa - dine markadan gozle
        found = [c for c in cars if tn in _norm(c.get("brand", ""))]
    if not found:
        return None, []
    return target, found


# ============================================================
# HOWPSUZLYK KÖMEKÇILERI  (14.08 doly barlag)
# ============================================================
def esc(s):
    """Markdown belgilerini zyýansyzlandyr.

    Sebäp: müşderi `*` ýa `_` ýazsa, ýa OCR model adyna şol belgini goşsa,
    Telegram "Markdown parse error" berýär we HABAR ASLA IBERILMEÝÄR.
    """
    s = str(s or "")
    for ch in ("\\", "_", "*", "[", "]", "`"):
        s = s.replace(ch, "\\" + ch)
    return s


def cb_data(prefix, text, limit=60):
    """callback_data üçin howpsuz kesme.

    Telegram çägi 64 BAÝT. Rus/türkmen harplary 2 baýt —
    40 harp = 80 baýt -> BadRequest -> düwme döremeýär.
    """
    out = prefix
    for ch in str(text or ""):
        if len((out + ch).encode("utf-8")) > limit:
            break
        out += ch
    return out


# Soňky netije (sahypalama üçin). Diňe ýatda, restartda ýitýär — zyýany ýok.
_last_results = {}
MAX_PHOTO_BATCH = 10       # bir gezekde näçe surat
PHOTO_DELAY = 0.35         # suratlaryň arasy (Telegram flood goragy)


# ============================================================
# TEKLIPLER — şu günki bazadan alynýar
# Sebäp (Erkin, 13.08): "Hilux" ýaly ÝOK maşyny teklip etsek,
# müşderi hemişe "tapylmady" görýär -> negatiw duýgy.
# Şoň üçin diňe HAKYKATDAN BAR maşynlar teklip edilýär.
# ============================================================
_JUNK_MODEL = {"cars", "auction", "industrial", "area", "fwd", "awd", "base",
               "below", "avg", "new", "used", "sel", "le", "se", "lx", "ex"}
# Iki sozli modeller - birinji soz yeterlik dal ("Santa" -> "Santa Fe")
_TWO_WORD = {"santa", "land", "grand", "range", "model"}


def _model_name(model):
    parts = (model or "").split()
    if not parts:
        return ""
    if parts[0].lower() in _TWO_WORD and len(parts) > 1:
        return f"{parts[0]} {parts[1]}"
    return parts[0]


def suggest_models(cars, n=6, per_brand=2):
    """Şu gün iň köp bolan modelleri gaýtarýar: ['Camry', 'Elantra', ...]"""
    cnt = {}
    for c in cars:
        m = (c.get("model") or "").strip()
        b = (c.get("brand") or "").strip()
        if not m or not b:
            continue
        first = _model_name(m)
        if len(first) < 2 or first.split()[0].lower() in _JUNK_MODEL:
            continue
        key = (b.title(), first.title())
        cnt[key] = cnt.get(key, 0) + 1

    out, used = [], {}
    for (b, m), _ in sorted(cnt.items(), key=lambda x: -x[1]):
        if used.get(b, 0) >= per_brand:
            continue
        used[b] = used.get(b, 0) + 1
        out.append(m)
        if len(out) >= n:
            break
    return out or ["Camry", "Elantra", "Sonata"]


def suggest_text(cars, n=4):
    s = suggest_models(cars, n)
    return ", ".join(f"*{x}*" for x in s)


def suggest_keyboard(cars, n=6):
    """Basyp gözlär ýaly düwmeler."""
    s = suggest_models(cars, n)
    rows, row = [], []
    for m in s:
        row.append(InlineKeyboardButton(f"🚗 {m}", callback_data=f"find:{m[:30]}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows) if rows else None


# ============================================================
# GÖZLEG ÝAZGYSY — näme gözlenýär, näme tapylmaýar
# Maksat: sinonim sanawyny hakyky müşderi ýazgysyna görä ösdürmek
# ============================================================
SEARCH_FILE = _DATA_DIR / "searches.json"


def _load_searches():
    try:
        d = json.loads(SEARCH_FILE.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    d.setdefault("found", {})    # göni tapylan:  "camry": 12
    d.setdefault("fuzzy", {})    # düzedilen:     "kamry>camry": 5
    d.setdefault("none", {})     # TAPYLMADY:     "hilux": 8   <- iň gymmatly
    d.setdefault("last", [])     # soňky 300 gözleg
    return d


def log_search(query, kind, matched=None, n=0):
    """kind: 'found' | 'fuzzy' | 'none'"""
    try:
        q = (query or "").strip()[:40]
        if not q or q.startswith("/"):
            return
        d = _load_searches()
        if kind == "fuzzy" and matched:
            key = f"{q.lower()}>{matched}"
            d["fuzzy"][key] = d["fuzzy"].get(key, 0) + 1
        elif kind == "none":
            d["none"][q.lower()] = d["none"].get(q.lower(), 0) + 1
        else:
            d["found"][q.lower()] = d["found"].get(q.lower(), 0) + 1

        d["last"].append({
            "t": datetime.now(DUBAI_TZ).strftime("%d.%m %H:%M"),
            "q": q, "k": kind, "n": n,
        })
        d["last"] = d["last"][-300:]

        # sanawlar çäksiz ösmesin
        for sec in ("found", "fuzzy", "none"):
            if len(d[sec]) > 400:
                d[sec] = dict(sorted(d[sec].items(), key=lambda x: -x[1])[:300])

        SEARCH_FILE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.error(f"log_search: {e}")


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


def _code_sort_key(c):
    """!! kod_ber.py-daky sort_key bilen DEŇ bolmaly !!
    Birini üýtgetseň — beýlekisini hem üýtget, ýogsa kodlar deň bolmaz."""
    return (
        c.get("price") or 10 ** 9,
        (c.get("brand") or "").upper(),
        (c.get("model") or "").upper(),
        (c.get("auction") or "").upper(),
        c.get("page") or 0,
        (c.get("image_path") or ""),
    )


def ensure_codes(cars):
    """Bazada "code" ýok bolsa — şu ýerde hasaplaýar.

    14.08 mesele: kod_ber işlemän galdy -> kartda 0814-055,
    botda HAJI-0814-056 -> müşderi tapmady.
    Indi bot kod ýok bolsa-da EDIL ŞOL kadadan hasaplaýar,
    şoň üçin kart bilen hemişe deň bolýar.
    """
    if not cars or all(c.get("code") for c in cars):
        return cars
    days = {}
    for c in cars:
        days.setdefault(str(c.get("date", "")), []).append(c)
    for day, group in days.items():
        if len(day) != 8:
            continue
        mmdd = day[4:6] + day[6:8]
        for i, c in enumerate(sorted(group, key=_code_sort_key), 1):
            if not c.get("code"):
                c["code"] = f"{mmdd}-{i:03d}"
    return cars


def get_car_code(car):
    """Günüň umumy kody: MMDD-NNN (mysal 0814-055).

    Auksion prefiksi ÝOK (Filipiň haýşy 14.08) — kart bilen deň bolmaly.
    """
    code = car.get("code")
    if code:
        return str(code)
    # Bu ýere düşse — load_cars() ensure_codes çagyrmandyr.
    date_str = str(car.get("date", ""))
    ds = date_str[4:8] if len(date_str) == 8 else "0000"
    try:
        ps = f"{int(car.get('page', 0)):03d}"
    except (ValueError, TypeError):
        ps = "000"
    return f"{ds}-{ps}"


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
                return ensure_codes(json.load(f))
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
    name = esc(f"{car.get('year')} {car.get('brand')} {car.get('model')}")
    cap = f"🚗 *{name}*\n"
    cap += f"🏢 {esc(car.get('auction', ''))}\n"
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


async def send_batch(msg, uid, cars_list, title=""):
    """Suratlary 10-lyk toparlar bilen iberýär.

    Sebäp: "Al Qaryah" gözlense 136 maşyn -> 136 habar.
    Telegram sekuntda 1 habar goýberýär -> bot 2+ minut doňýar,
    hatda "flood control" jerimesi düşýär.
    """
    st = _last_results.get(uid) or {}
    if title:
        st = {"title": title, "cars": cars_list, "sent": 0}
    cars_list = st.get("cars", [])
    start = st.get("sent", 0)
    chunk = cars_list[start:start + MAX_PHOTO_BATCH]

    for car in chunk:
        try:
            await send_car_with_photo(msg, car)
            await asyncio.sleep(PHOTO_DELAY)
        except Exception as e:
            logger.error(f"send_batch: {e}")

    st["sent"] = start + len(chunk)
    _last_results[uid] = st

    galan = len(cars_list) - st["sent"]
    if galan > 0:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"⬇️ Ýene {min(galan, MAX_PHOTO_BATCH)} görkez",
                                 callback_data="more")
        ], [
            InlineKeyboardButton("📱 WhatsApp-a ýaz", url=TEKWAY_WHATSAPP)
        ]])
        await msg.reply_text(
            f"📋 *{st['sent']}/{len(cars_list)}* görkezildi.  Ýene *{galan}* maşyn bar.\n\n"
            f"_Has takyk ýazsaň az çykar — meselem `Camry 2023`._",
            parse_mode="Markdown", reply_markup=kb)
    elif len(cars_list) > MAX_PHOTO_BATCH:
        await msg.reply_text(
            f"✅ Hemmesi görkezildi — *{len(cars_list)}* maşyn.",
            parse_mode="Markdown", reply_markup=contact_keyboard())


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
    cars0 = load_cars()
    ex = suggest_text(cars0, 3)
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
        f"• Maşyn adyny ýaz — meselem: {ex}\n"
        "• Auksion adyny ýaz — meselem: *Marhaba*, *Nojoom*\n"
        "• Ýalňyş ýazsaň-da düşünýärin (`kamry`, `hunday`)\n"
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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cars = load_cars()
    ex = ", ".join(f"`{x}`" for x in suggest_models(cars, 3))
    auks = sorted({c.get("auction", "").split()[0] for c in cars if c.get("auction")})[:3]
    exa = ", ".join(f"`{x}`" for x in auks) or "`Marhaba`"
    await update.message.reply_text(
        "📋 *Komandalar:*\n\n"
        f"🚗 *Maşyn gözlemek:* {ex}\n"
        f"🏢 *Auksion gözlemek:* {exa}\n"
        "🔎 Ýalňyş ýazsaň-da düşünýärin: `kamry`, `hunday`\n"
        "🆔 *Kod boýunça:* `0813-013`\n\n"
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
        text += f"🏢 *{esc(a)}* — {n} maşyn\n"
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
        await update.message.reply_text(f"✅ Ýatlatma goýuldy: *{esc(q)}*", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"ℹ️ Eýýäm bar: *{esc(q)}*", parse_mode="Markdown")


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
        await update.message.reply_text(f"✅ Pozuldy: *{esc(arg)}*", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ *{esc(arg)}* tapylmady.", parse_mode="Markdown")




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

    # --- TAZE gelen ulanyjylar (first_seen boyunca) ---
    def _first_day(u):
        fs = str(u.get("first_seen", ""))
        return fs[:10].replace("-", "")     # "2026-08-14 09:12" -> "20260814"

    new_today = sum(1 for u in users.values() if _first_day(u) == today)
    new_week = sum(1 for u in users.values() if _first_day(u) in week_days)
    new_month = sum(1 for u in users.values() if _first_day(u) in month_days)

    txt = "📊 *BOT STATISTIKASY*\n\n"
    txt += f"👥 *Jemi ulanyjy:* {total}\n\n"
    txt += "🆕 *Täze gelenler:*\n"
    txt += f"   Bugün: *{new_today}*\n"
    txt += f"   Şu hepde: *{new_week}*\n"
    txt += f"   Şu aý: *{new_month}*\n\n"
    txt += "🟢 *Aktiw (girip gören):*\n"
    txt += f"   Bugün: {today_active}\n"
    txt += f"   Şu hepde: {week_active}\n"
    txt += f"   Şu aý: {month_active}\n\n"
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


# ============================================================
# MAGLUMAT GOZEGÇILIGI — Erkine duýduryş
# Sagat 10:00 bolup şu günki maşyn gelmedik bolsa — admin-e habar.
# (board 12.08, 3-nji priýoritet)
# ============================================================
DATA_WARN_HOUR = 10          # sagat näçede duýdursyn (Dubaý wagty)
WARN_FILE = _DATA_DIR / "data_warn.json"


def _load_warn():
    try:
        return json.loads(WARN_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_warn(d):
    try:
        WARN_FILE.write_text(json.dumps(d), encoding="utf-8")
    except Exception as e:
        logger.error(f"warn save: {e}")


async def data_watch_loop(app):
    """Her 15 minutda barlaýar. Bir günde bir gezek habar iberýär."""
    await asyncio.sleep(90)
    while True:
        try:
            now = datetime.now(DUBAI_TZ)
            today = get_today()
            st = _load_warn()

            if st.get("day") != today:
                st = {"day": today, "warned": False, "ok": False}

            cars = load_cars()
            fresh = db_is_fresh(cars)

            # 1) Maglumat geldi -> bir gezek "taýýar" habary
            if fresh and not st.get("ok"):
                st["ok"] = True
                _save_warn(st)
                try:
                    await app.bot.send_message(
                        ADMIN_ID,
                        f"✅ *Maglumat taýýar*\n\n"
                        f"📅 {today[6:8]}.{today[4:6]}\n"
                        f"🚗 {len(cars)} maşyn\n"
                        f"🕐 {now.strftime('%H:%M')} (Dubaý)\n\n"
                        f"Bot işleýär.",
                        parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"data ok msg: {e}")

            # 2) Sagat 10:00 boldy, maglumat ýok -> duýduryş
            elif (not fresh and not st.get("warned")
                  and now.hour >= DATA_WARN_HOUR):
                st["warned"] = True
                _save_warn(st)
                try:
                    await app.bot.send_message(
                        ADMIN_ID,
                        f"🔴 *DUÝDURYŞ — bugün maglumat ýok*\n\n"
                        f"Sagat *{now.strftime('%H:%M')}* (Dubaý), "
                        f"şu günki auksion maşynlary heniz gelmedi.\n\n"
                        f"Müşderiler häzir *«entek taýýar däl»* ýazgysyny görýär.\n\n"
                        f"Barla:\n"
                        f"• PDF-ler `In` papka atyldymy?\n"
                        f"• Watcher işleýärmi?\n"
                        f"• GitHub-a iberildimi?\n\n"
                        f"Bazadaky soňky sene: `{max((str(c.get('date','')) for c in cars), default='ýok')}`",
                        parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"data warn msg: {e}")
            else:
                _save_warn(st)

        except Exception as e:
            logger.error(f"data_watch_loop: {e}")
        await asyncio.sleep(900)   # 15 minut


async def post_init(app):
    asyncio.create_task(alert_loop(app))
    asyncio.create_task(data_watch_loop(app))
    logger.info("Alert loop isledildi (her 10 min)")
    logger.info(f"Maglumat gozegciligi isledildi (duyduryş sagat {DATA_WARN_HOUR}:00)")




async def gozleg_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Müşderiler näme gözleýär, näme tapylmaýar (diňe admin)."""
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("⛔ Bu komanda diňe admin üçin.")
        return

    d = _load_searches()
    found, fuzzy, none = d["found"], d["fuzzy"], d["none"]
    total = sum(found.values()) + sum(fuzzy.values()) + sum(none.values())

    if not total:
        await update.message.reply_text(
            "📊 *Gözleg statistikasy*\n\n"
            "Entek gözleg ýok. Müşderiler ýazyp başlanda şu ýerde görüner:\n"
            "• iň köp gözlenen maşynlar\n"
            "• tapylmadyk gözlegler\n"
            "• ýalňyş ýazylyp düzedilen sözler",
            parse_mode="Markdown")
        return

    t = "📊 *GÖZLEG STATISTIKASY*\n\n"
    t += f"🔢 Jemi gözleg: *{total}*\n"
    t += f"✅ Tapyldy: {sum(found.values())}  ·  "
    t += f"🔎 Düzedildi: {sum(fuzzy.values())}  ·  "
    t += f"📭 Tapylmady: {sum(none.values())}\n\n"

    if none:
        t += "🔴 *TAPYLMADY* (iň möhüm — bazada ýok ýa bot düşünmedi)\n"
        for q, n in sorted(none.items(), key=lambda x: -x[1])[:15]:
            t += f"   `{esc(q)}` — {n}×\n"
        t += "\n"

    if fuzzy:
        t += "🔎 *ÝALŇYŞ ÝAZYLYP DÜZEDILEN*\n"
        for k, n in sorted(fuzzy.items(), key=lambda x: -x[1])[:15]:
            a, _, b = k.partition(">")
            t += f"   `{esc(a)}` → *{esc(b)}* — {n}×\n"
        t += "\n"

    if found:
        t += "✅ *IŇ KÖP GÖZLENEN*\n"
        for q, n in sorted(found.items(), key=lambda x: -x[1])[:15]:
            t += f"   `{esc(q)}` — {n}×\n"

    t += "\n_Tapylmadyk sözleri maňa aýt — sinonim sanawyna goşaryn._"

    for i in range(0, len(t), 3800):
        await update.message.reply_text(t[i:i + 3800], parse_mode="Markdown")


async def sonky_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Soňky 30 gözleg — janly görnüş (diňe admin)."""
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("⛔ Bu komanda diňe admin üçin.")
        return
    d = _load_searches()
    last = d.get("last", [])[-30:]
    if not last:
        await update.message.reply_text("📭 Entek gözleg ýok.")
        return
    icon = {"found": "✅", "fuzzy": "🔎", "none": "📭"}
    t = "🕐 *SOŇKY 30 GÖZLEG*\n\n"
    for r in reversed(last):
        t += f"{icon.get(r.get('k'), '•')} `{esc(r.get('q'))}` — {r.get('n', 0)} maşyn  _{r.get('t')}_\n"
    for i in range(0, len(t), 3800):
        await update.message.reply_text(t[i:i + 3800], parse_mode="Markdown")


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
                f"🆔 *{esc(want)}* — tapyldy:", parse_mode="Markdown")
            for car in hit:
                await send_car_with_photo(update, car)
            return
        await update.message.reply_text(
            f"📭 *{esc(want)}* kody bilen maşyn tapylmady.\n\n"
            "Kod her gün täzelenýär — düýnki koda şu gün maşyn ýok bolmagy mümkin.",
            parse_mode="Markdown", reply_markup=contact_keyboard())
        return

    for key, aname in AUCTIONS.items():
        if key in tl:
            ac = [c for c in cars if aname.upper() in c.get("auction", "").upper()]
            if not ac:
                await update.message.reply_text(f"📭 {esc(aname)}-da şu gün maşyn ýok.")
                return
            await update.message.reply_text(
                f"🏢 *{esc(aname)}* — {len(ac)} maşyn tapyldy:", parse_mode="Markdown")
            log_search(text, "found", None, len(ac))
            await send_batch(update.message, str(update.effective_user.id),
                             ac, title=aname)
            return

    found = [c for c in cars if tu in f"{c.get('brand','')} {c.get('model','')}".upper()]

    # --- Göni tapylmasa: ýalňyş/türkmençe/rusça ýazgy bolmagy mümkin ---
    fuzzy_word = None
    if not found:
        fuzzy_word, found = fuzzy_find(text, cars)

    if not found:
        log_search(text, "none")
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"🔔 '{text[:30]}' çykanda habar ber",
                                 callback_data=cb_data("alert:", text))
        ]])
        await update.message.reply_text(
            f"📭 *'{esc(text)}'* şu gün ýok.\n\nÇykanda habar bermegimi isleýäňizmi?",
            parse_mode="Markdown", reply_markup=kb)
        return

    log_search(text, "fuzzy" if fuzzy_word else "found", fuzzy_word, len(found))

    if fuzzy_word:
        await update.message.reply_text(
            f"🔎 *{esc(fuzzy_word.title())}* diýip düşündim — {len(found)} maşyn tapyldy:",
            parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"🚗 *'{esc(text)}'* — {len(found)} maşyn tapyldy:", parse_mode="Markdown")

    await send_batch(update.message, str(update.effective_user.id),
                     found, title=text)


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
                f"✅ Ýatlatma goýuldy: *{esc(st)}*\n\n"
                f"Şol maşyn çykanda size habar bererin.\n"
                f"Ýatlatmalar: /myalerts",
                parse_mode="Markdown")
        else:
            await q.message.reply_text(f"ℹ️ *{esc(st)}* üçin ýatlatma eýýäm bar.", parse_mode="Markdown")

    elif d == "contact":
        await q.message.reply_text("📱 *TEK AUTO MARKET* bilen habarlaş:",
                                   parse_mode="Markdown", reply_markup=contact_keyboard())
    elif d == "search":
        cars = load_cars()
        await q.message.reply_text(
            "🚗 *Haýsy maşyny gözleýäň?*\n\n"
            "Adyny ýaz ýa aşakdakylardan bir düwmä bas.\n"
            "_Şu gün iň köp bar bolanlar:_",
            parse_mode="Markdown", reply_markup=suggest_keyboard(cars, 6))

    elif d.startswith("find:"):
        want = d[5:].strip()
        cars = load_cars()
        if not db_is_fresh(cars):
            await q.message.reply_text(NOT_READY_MSG, parse_mode="Markdown",
                                       reply_markup=contact_keyboard())
            return
        wu = want.upper()
        found = [c for c in cars
                 if wu in f"{c.get('brand','')} {c.get('model','')}".upper()]
        if not found:
            _, found = fuzzy_find(want, cars)
        if not found:
            await q.message.reply_text(f"📭 *{esc(want)}* şu gün ýok.", parse_mode="Markdown")
            return
        log_search(want, "found", None, len(found))
        await q.message.reply_text(
            f"🚗 *{esc(want)}* — {len(found)} maşyn tapyldy:", parse_mode="Markdown")
        await send_batch(q.message, str(q.from_user.id), found, title=want)

    elif d == "more":
        uid = str(q.from_user.id)
        st = _last_results.get(uid)
        if not st or not st.get("cars"):
            await q.message.reply_text(
                "🔄 Gözleg ýatdan çykdy. Maşyn adyny täzeden ýazaý.")
            return
        await send_batch(q.message, uid, st["cars"])

    elif d == "auction":
        cars = load_cars()
        names = sorted({c.get("auction", "") for c in cars if c.get("auction")})
        t = "🏢 *Haýsy auksiony gözleýäň?*\n\nŞu gün bar bolanlar:\n"
        for a in names:
            n = sum(1 for c in cars if c.get("auction") == a)
            t += f"• *{a}* — {n} maşyn\n"
        t += "\nAdyny ýaz — meselem: `Marhaba`"
        await q.message.reply_text(t, parse_mode="Markdown")
    elif d == "myalerts":
        uid = str(q.from_user.id)
        my = load_yatlatmas().get(uid, [])
        if not my:
            await q.message.reply_text(
                "🔔 Sizde ýatlatma ýok.\n\nMaşyn gözläniňizde tapylmasa — düwme bilen goýup bilersiňiz.")
        else:
            t = "🔔 *Siziň ýatlatmalaryňyz:*\n\n"
            for i, a in enumerate(my, 1):
                t += f"{i}. {esc(a)}\n"
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
    app.add_handler(CommandHandler("gozleg", gozleg_command))
    app.add_handler(CommandHandler("sonky", sonky_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Dubai Auksion | TEK AUTO MARKET boty işläp başlady!")
    app.run_polling()


if __name__ == "__main__":
    main()

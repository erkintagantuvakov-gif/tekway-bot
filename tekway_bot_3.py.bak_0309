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

from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup, KeyboardButton)
from telegram.error import Forbidden
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

# --- ZAKAZ moduly (Notion -> işgärler). Token ýok bolsa dymýar. ---
try:
    import zakaz as ZK
except Exception as _e:          # modul ýok bolsa bot öňki ýaly işlesin
    ZK = None
    logger.warning("zakaz moduly ýüklenmedi: %s", _e)


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
    if not q:
        return None, []

    # 19.08 DUZEDIS — GYSGA MODEL ATLARY
    # Onki kada: 3 harpdan gysga sorag ret edilyardi.
    # Netije: "k5", "x5", "q5", "cx5", "gt" YALY HAKYKY MODELLER
    # hic haçan tapylmaýardy. K5 bolsa in kop soralýan modelleriň biri.
    # Indi: harp+san gornushi (k5, x5, q7, cx9, i8...) gonuden gozlenya.
    if len(q) < 3:
        if re.fullmatch(r'[a-z]{1,2}\d{1,2}', q):
            found = [c for c in cars
                     if re.search(rf'\b{re.escape(q)}\b',
                                  _norm(f"{c.get('brand','')} {c.get('model','')}"))]
            if found:
                return q.upper(), found
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


def code_ok(s):
    """`code` bellik ICINDE ulanmak ucin howpsuz tekst.

    20.08: esc() "\\_" goşýardy, Telegram-yn köne Markdown-y bolsa
    entity içinde gaçyrmagy kabul edenok -> habar iberilmeýär.
    Kod belliginde diňe backtick howply — şony aýyrmak ýeterlik.
    """
    return str(s or "").replace("`", "'")


async def _send_md_safe(msg, text, limit=3500, reply_markup=None):
    """Uzyn teksti SETIR araçäginde bölüp iberýär.

    20.08 sapagy — bot näme üçin dymýardy:
      1) Tekst 3800 harpdan bölünende Markdown belgisi ORTASYNDAN kesilýärdi
         (açylan `*` bir bölekde, ýapylany beýlekide) -> "Can't parse entities".
      2) Ýalňyşlyk tutulmaýardy -> habar ASLA iberilmeýärdi, bot dymýardy.

    Indi: setir araçäginde bölünýär, Markdown başartmasa şol bölek
    bellik-siz gaýtadan iberilýär. Bot hiç haçan dymmaly däl.
    """
    parts, cur = [], ""
    for line in str(text).split("\n"):
        if len(cur) + len(line) + 1 > limit and cur:
            parts.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        parts.append(cur)

    for i, p in enumerate(parts):
        # Duwme paneli DIŇE sonky bolege dakylya (24.08)
        rm = reply_markup if i == len(parts) - 1 else None
        try:
            await msg.reply_text(p, parse_mode="Markdown", reply_markup=rm)
        except Exception as e:
            logger.error(f"Markdown basartmady, bellik-siz iberilya: {e}")
            try:
                await msg.reply_text(re.sub(r'[*_`\\]', '', p),
                                     reply_markup=rm)
            except Exception as e2:
                logger.error(f"Habar asla iberilmedi: {e2}")


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
    text += f"🏢 {auksion_ady_yer(car)}\n"
    _ws = _auksion_wagt_setiri(car)
    if _ws:
        text += _ws + "\n"
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
def auksion_ady_yer(car):
    """
    Auksion ady + shahamchasy: "Marhaba Auctions - Souq Al Haraj"
    Marhaba 4 shahamchada ishleya, hersi ayry yer we ayry sagat.
    Mushderi nira gitmelidigini bilmeli.
    """
    ady = (car.get("auction") or "").strip()
    yer = (car.get("auction_branch") or "").strip()
    if yer and yer.upper() not in ady.upper():
        return f"{ady} - {yer}"
    return ady


def auksion_sagady(car):
    """Auksionyn bashlanyan sagady (Dubay wagty). Bolmasa bosh setir."""
    w = (car.get("auction_time") or "").strip()
    return w


def auksion_senesi(car):
    """Auksionyn senesi: '26.08.2026'. Bolmasa bosh setir.

    ⚠️ 26.08 — Erkin: "Dubay wagty bar, emma SENE yok".
    Mushderä WhatsApp-a gidyan tekstde dine sagat bardy. Adam ony
    gije okasa "ertirmi, sho gunmi" bilenokdy — hakykatda ol masyn
    ESHOL GUN oynalyp gutarypdy. Sene indi hokman gorkezilya.
    """
    d = str(car.get("date") or "").strip()
    if len(d) == 8 and d.isdigit():
        return f"{d[6:8]}.{d[4:6]}.{d[0:4]}"
    return ""


def _auksion_wagt_setiri(car, esc_fn=None):
    """'26.08.2026, 17:45 (Dubaý wagty)' — sene we sagat birlikde."""
    e = esc_fn or (lambda x: x)
    sn, wg = auksion_senesi(car), auksion_sagady(car)
    if sn and wg:
        return f"🕐 Auksion: {e(sn)}, {e(wg)} (Dubaý wagty)"
    if sn:
        return f"📅 Auksion: {e(sn)}"
    if wg:
        return f"🕐 Auksion: {e(wg)} (Dubaý wagty)"
    return ""


def build_caption(car):
    name = esc(f"{car.get('year')} {car.get('brand')} {car.get('model')}")
    cap = f"🚗 *{name}*\n"
    cap += f"🏢 {esc(auksion_ady_yer(car))}\n"
    _ws = _auksion_wagt_setiri(car, esc)
    if _ws:
        cap += _ws + "\n"
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

    # 19.08: bu ýat (RAM) hiç haçan arassalanmaýardy. Her müşderiniň
    # doly netije sanawy saklanýardy -> müşderi köpelse bot ýady dolýar.
    # Indi diňe soňky 60 müşderi saklanýar (sahypalama üçin şol ýeterlik).
    if len(_last_results) > 60:
        for _k in list(_last_results.keys())[:-60]:
            _last_results.pop(_k, None)

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
    # Ishgar bolsa — hemishelik duwme panelini gorkez (24.08)
    try:
        if _zk_rugsat(update.effective_user.id):
            await update.message.reply_text(
                "👔 *TEK topary* — düwmeler aşakda taýýar.",
                parse_mode="Markdown", reply_markup=ishgar_klawiatura())
    except Exception:
        pass
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
    # işgärlere goşmaça — müşderi bu bölümi görmeýär
    if _zk_rugsat(update.effective_user.id) and _zk_bar():
        await update.message.reply_text(
            "👔 *TEK topary üçin:*\n\n"
            "📋 */sargyt* — açyk sargytlar\n"
            "🔎 */sargyt ST-4* — şol sargydy aç\n"
            "🔄 */sargyt tazele* — Notion-dan täzeden oka",
            parse_mode="Markdown")


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cars = load_cars()
    if not cars or not db_is_fresh(cars):
        await update.message.reply_text(NOT_READY_MSG, parse_mode="Markdown", reply_markup=contact_keyboard())
        return
    # ⚠️ 24.08 — ŞAHAMÇALAR AÝRY SANALÝAR.
    # Erkin: "şu gün 3 auksion bar, näme üçin ikisini görkezýär?"
    # Sebäbi: Marhaba-nyň IKI şahamçasy (Souq Al Haraj we IND 12)
    # ikisi hem "Marhaba Auctions" ady bilen gelýär — bir setire
    # goşulýardy. Emma olar AÝRY auksion: aýry ýer, aýry sagat.
    # Indi: at + şahamça boýunça toparlanýar, sagady hem görkezilýär.
    counts = {}
    for c in cars:
        a = c.get("auction", "Näbelli")
        sh = (c.get("auction_branch") or "").strip()
        w = (c.get("auction_time") or "").strip()
        acar = (a, sh, w)
        counts[acar] = counts.get(acar, 0) + 1

    # Sagat boýunça tertip — gün nähili gidýär, şeýle görünsin
    def _tertip(x):
        (a, sh, w), n = x
        return (w or "99:99", -n)

    text = "📅 *Şu günki auksionlar:*\n\n"
    for (a, sh, w), n in sorted(counts.items(), key=_tertip):
        setir = f"🏢 *{esc(a)}*"
        if sh:
            setir += f" — {esc(sh)}"
        if w:
            setir += f"  ·  🕐 {esc(w)}"
        text += setir + f"\n     {n} maşyn\n\n"
    text += f"✅ Jemi: *{len(cars)} maşyn*  ·  {len(counts)} auksion"
    await update.message.reply_text(text, parse_mode="Markdown")


async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📱 *TEK AUTO MARKET*\n\nHabarlaş:",
                                    parse_mode="Markdown", reply_markup=contact_keyboard())


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /id — Telegram ID gorkezya.

    Nam uchin gerek: zakaz sistemasy uchin Railway-a STAFF_IDS
    (ishgarlerin ID-leri) we TOPAR_CHAT_ID (topar grupbasy) yazmaly.
    Ol sanlary bashga yol bilen almak kyn - shonun uchin shu komanda.

    Howpsuz: adam dine OZ ID-sini goryar, bashgalarynkyny dal.
    """
    ch = update.effective_chat
    us = update.effective_user
    t = "🆔 *Telegram ID*\n\n"
    t += f"👤 Seniň ID-ň: `{us.id}`\n"
    if us.username:
        t += f"    @{esc(us.username)}\n"
    if ch and ch.type in ("group", "supergroup", "channel"):
        t += f"\n👥 Bu grupbanyň ID-si: `{ch.id}`\n"
        t += f"    {esc(ch.title or '')}\n"
        t += "\n_Grupba ID-si `TOPAR_CHAT_ID` üçin._"
    else:
        t += "\n_Grupbanyň ID-sini almak üçin — boty grupba goş, şol ýerde /id ýaz._"
    await update.message.reply_text(t, parse_mode="Markdown")


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
DATA_WARN_HOUR = 7           # sagat näçede duýdursyn (Dubaý wagty)
# 22.08: on 10:00-dy. Maglumat adatça 01:00-da taýýar bolýar,
# şonuň üçin 10:00 gaty giç — Erkin meseläni bizden öň tapýardy.
# Indi 07:00-da duýdurýar.
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


def load_report(day):
    """Günlik hasabat: haýsy PDF işlendi, näçe maşyn çykdy."""
    p = Path(f"gun_hasabat_{day}.json")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def report_lines(day, cars):
    """Auksion boýunça setirler. Hasabat ýok bolsa bazadan hasaplaýar."""
    rep = load_report(day)
    out = []
    if rep:
        for r in sorted(rep, key=lambda x: -(x.get("kept") or 0)):
            nm = str(r.get("auction", "?"))[:26]
            kept = r.get("kept", 0)
            pages = r.get("pages", 0)
            mark = "⚠️" if kept == 0 else "🏢"
            out.append(f"{mark} {esc(nm)} — *{kept}* maşyn  _({pages} sah.)_")
    else:
        cnt = {}
        for c in cars:
            if str(c.get("date")) == day:
                a = c.get("auction", "?")
                cnt[a] = cnt.get(a, 0) + 1
        for a, n in sorted(cnt.items(), key=lambda x: -x[1]):
            out.append(f"🏢 {esc(str(a)[:26])} — *{n}* maşyn")
    return out


ADMIN_ALERTS_FILE = Path("admin_alerts.json")      # repo-dan gelya
SENT_ADMIN_FILE = _DATA_DIR / "sent_admin_alerts.json"


async def check_parser_alerts(bot):
    """PDF işlenip 0 maşyn çykan bolsa — Erkine habar ber.

    14.08 KHAT sapagy: auksion şablonyny üýtgetdi, 243 sahypadan 0 maşyn
    çykdy we HIÇ KIM BILMEDI. Indi şeýle ýagdaýda derrew habar gelýär.
    """
    try:
        if not ADMIN_ALERTS_FILE.exists():
            return
        alerts = json.loads(ADMIN_ALERTS_FILE.read_text(encoding="utf-8"))
        try:
            sent = set(json.loads(SENT_ADMIN_FILE.read_text(encoding="utf-8")))
        except Exception:
            sent = set()

        # 18.08 DUZEDIS — ÝALAN DUÝDURYŞ
        # Mesele: auksion 0 maşyn berýär -> duýduryş ýazylýar. Soň Pawel
        # düzedip gaýtadan işleýär, 92 maşyn goşulýar. Emma köne duýduryş
        # faýlda galýar we bot restart bolanda ÝENE iberilýär.
        # Erkin "auksion işlenmedi" diýen habary alýar, aslynda maşynlar bar.
        # Indi: iberilmezden öň BAZA barlanýar — şol gün şol auksionda
        # maşyn bar bolsa, duýduryş ugradylmaýar (çözülen hasaplanýar).
        def _cozulenmi(a):
            try:
                pdf = str(a.get("pdf", ""))
                dat = str(a.get("date", ""))
                if not dat:
                    return False
                stem = re.sub(r'[^\w]', '_', pdf.rsplit(".", 1)[0])
                for c in load_cars():
                    if c.get("date") != dat:
                        continue
                    # a) şol PDF-den surat bar
                    if stem and stem in str(c.get("image_path", "")):
                        return True
                    # b) ýa-da şol auksion ady indi bazada bar
                    if c.get("auction") and c["auction"] == a.get("auction"):
                        return True
            except Exception:
                pass
            return False

        yeni = []
        for a in alerts:
            if not a.get("id") or a["id"] in sent:
                continue
            if _cozulenmi(a):
                sent.add(a["id"])          # dymyp ýap - eýýäm düzeldilipdir
                logger.info(f"alert cozulen - ugradylmady: {a['id']}")
                continue
            yeni.append(a)
        if not yeni and sent:
            SENT_ADMIN_FILE.write_text(json.dumps(sorted(sent)), encoding="utf-8")

        for a in yeni:
            d = str(a.get("date", ""))
            ds = f"{d[6:8]}.{d[4:6]}" if len(d) == 8 else d
            txt = (
                f"🔴 *AUKSION IŞLENMEDI*\n\n"
                f"🏢 {esc(a.get('auction', '?'))}\n"
                f"📅 {ds}\n"
                f"📄 {esc(a.get('pdf', ''))}\n\n"
                f"⚠️ {esc(a.get('msg', ''))}\n\n"
                f"Sebäbi köplenç: *auksion PDF şablonyny üýtgedipdir* — "
                f"tekst okalmaýar.\n"
                f"Şu auksionyň maşynlary botda ÝOK. Pawel-a aýt."
            )
            r = a.get("reasons") or {}
            if r:
                txt += "\n\n_Aýrylan sebäpler:_\n"
                for k, v in list(r.items())[:4]:
                    txt += f"• {esc(k)} — {v}\n"
            try:
                await bot.send_message(ADMIN_ID, txt, parse_mode="Markdown")
                sent.add(a["id"])
            except Exception as e:
                logger.error(f"parser alert ugradylmady: {e}")

        if yeni:
            SENT_ADMIN_FILE.write_text(json.dumps(sorted(sent)), encoding="utf-8")
    except Exception as e:
        logger.error(f"check_parser_alerts: {e}")


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

            # Parser duyduryşlary (0 masyn cykan auksionlar)
            await check_parser_alerts(app.bot)

            # 1) Maglumat geldi -> bir gezek "taýýar" habary
            if fresh and not st.get("ok"):
                st["ok"] = True
                _save_warn(st)
                try:
                    await app.bot.send_message(
                        ADMIN_ID,
                        f"✅ *Maglumat taýýar*\n\n"
                        f"📅 {today[6:8]}.{today[4:6]}  ·  "
                        f"🕐 {now.strftime('%H:%M')} (Dubaý)\n"
                        f"🚗 *{len(cars)} maşyn*  ·  "
                        f"{len(report_lines(today, cars))} auksion\n\n"
                        + "\n".join(report_lines(today, cars))
                        + "\n\n_Jikme-jik: /hasabat_",
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
    asyncio.create_task(gundelik_habar_loop(app))
    if ZK is not None and ZK.isleyarmi():
        ZK._hb_oka()          # 26.08: onki habarlar diskden okalya
        asyncio.create_task(zakaz_gozegcilik(app))
        _alyj = (ZK.TOPAR_CHAT_ID or ", ".join(sorted(ZK.STAFF_IDS)) or "—")
        logger.info("ZAKAZ moduly isjen (Notion baglandy)")
        logger.info("SARGYT awtomat habary -> %s (her 30 min)", _alyj)
    else:
        logger.info("ZAKAZ moduly ochuk (NOTION_TOKEN yok)")
    logger.info("Alert loop isledildi (her 10 min)")
    logger.info(f"Maglumat gozegciligi isledildi (duyduryş sagat {DATA_WARN_HOUR}:00)")
    logger.info(f"Gundelik habar isledildi (her gun sagat {HABAR_SAGAT}:00)")

    # ⚠️ 24.08 — TELEGRAMYN "MENU" DUWMESI.
    # Erkin: "panel gitdi, her sapar /start yazmalymy?"
    # Ashakdaky duwme paneli Telegram kate yygnaya (yazyp bashlanda).
    # Emma yazgy meydanynyn CHEP tarapyndaky gok "Menu" duwmesi
    # HIC HACAN yitmeya. Ishgarlere shol menyuda "Sargytlar" chykar.
    try:
        from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

        # Mushderiler uchin — sada
        await app.bot.set_my_commands([
            BotCommand("start", "Başla"),
            BotCommand("today", "Şu günki auksionlar"),
            BotCommand("help", "Kömek"),
            BotCommand("contact", "Habarlaşmak"),
        ], scope=BotCommandScopeDefault())

        # Ishgarler uchin — sargyt komandalary hem bar
        _ishgarler = set(ZK.STAFF_IDS) if ZK else set()
        _ishgarler.add(str(ADMIN_ID))
        for _uid in _ishgarler:
            try:
                await app.bot.set_my_commands([
                    BotCommand("sargyt", "📋 Açyk sargytlar"),
                    BotCommand("today", "📅 Şu günki auksionlar"),
                    BotCommand("start", "Düwmeleri yzyna getir"),
                    BotCommand("help", "Kömek"),
                ], scope=BotCommandScopeChat(chat_id=int(_uid)))
            except Exception as e:
                logger.warning("Menyu goyulmady (%s): %s", _uid, e)
        logger.info("Menyu duwmesi goyuldy (%d isgar)", len(_ishgarler))
    except Exception as e:
        logger.warning("set_my_commands basartmady: %s", e)




async def hasabat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Şu günki PDF-ler doly işlendimi — jikme-jik (diňe admin)."""
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("⛔ Bu komanda diňe admin üçin.")
        return

    cars = load_cars()
    day = max((str(c.get("date", "")) for c in cars), default=get_today())
    rep = load_report(day)

    t = f"📋 *GÜNLIK HASABAT — {day[6:8]}.{day[4:6]}*\n\n"
    if not rep:
        t += ("_Hasabat faýly ýok._\n"
              "Bu köne maglumat bolmagy mümkin — hasabat 15.08-den başlap ýazylýar.\n\n")
        for ln in report_lines(day, cars):
            t += ln + "\n"
        await update.message.reply_text(t, parse_mode="Markdown")
        return

    tot_pages = sum(r.get("pages", 0) for r in rep)
    tot_kept = sum(r.get("kept", 0) for r in rep)
    tot_rej = sum(r.get("rejected", 0) for r in rep)

    t += f"📄 *{len(rep)} PDF* işlendi  ·  {tot_pages} sahypa\n"
    t += f"✅ Alnan: *{tot_kept}*  ·  🚫 Süzülen: {tot_rej}\n\n"

    for r in sorted(rep, key=lambda x: -(x.get("kept") or 0)):
        kept = r.get("kept", 0)
        pages = r.get("pages", 0)
        rej = r.get("rejected", 0)
        mark = "⚠️" if kept == 0 else "✅"
        t += f"{mark} *{esc(str(r.get('auction', '?')))}*\n"
        t += f"    {kept} maşyn  ·  {pages} sahypa  ·  {rej} süzüldi\n"
        # 20.08 DUZEDIS — /hasabat JOGAP BERMEYARDI
        # Onki setir: _{esc(pdf)}_  ->  _20-AUG-2026\_260819\_202619.pdf_
        # Telegram-yn KONE Markdown-y entity ICINDE "\_" kabul edenok.
        # Netije: "Can't parse entities" -> habar ASLA iberilmeya, bot dymya.
        # (West Cars faylynyn adynda "_" kop - sonun ucin sho gun doly dymdy.)
        # Indi: kursiw ayryldy, at `code` gornushinde berilýar - howpsuz.
        _pdf = str(r.get('pdf', ''))[:44].replace('`', "'")
        t += f"    `{_pdf}`  {r.get('time', '')}\n\n"

    bos = [r for r in rep if not r.get("kept")]
    if bos:
        t += "🔴 *Maşyn çykmadyk PDF bar — barla!*\n"
    else:
        t += "_Ähli PDF üstünlikli işlendi._\n"

    t += f"\n🚗 Bazada jemi: *{len([c for c in cars if str(c.get('date')) == day])}* maşyn"

    await _send_md_safe(update.message, t)


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
            t += f"   `{code_ok(q)}` — {n}×\n"
        t += "\n"

    if fuzzy:
        t += "🔎 *ÝALŇYŞ ÝAZYLYP DÜZEDILEN*\n"
        for k, n in sorted(fuzzy.items(), key=lambda x: -x[1])[:15]:
            a, _, b = k.partition(">")
            t += f"   `{code_ok(a)}` → *{esc(b)}* — {n}×\n"
        t += "\n"

    if found:
        t += "✅ *IŇ KÖP GÖZLENEN*\n"
        for q, n in sorted(found.items(), key=lambda x: -x[1])[:15]:
            t += f"   `{code_ok(q)}` — {n}×\n"

    t += "\n_Tapylmadyk sözleri maňa aýt — sinonim sanawyna goşaryn._"

    await _send_md_safe(update.message, t)


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
        t += f"{icon.get(r.get('k'), '•')} `{code_ok(r.get('q'))}` — {r.get('n', 0)} maşyn  `{code_ok(r.get('t'))}`\n"
    await _send_md_safe(update.message, t)


# ============================================================
# ZAKAZ — diňe işgärler üçin (Notion-dan okaýar)
# ============================================================
def _zk_bar():
    return ZK is not None and ZK.isleyarmi()


def _zk_rugsat(uid):
    """Admin hemişe, galanlary STAFF_IDS sanawynda bolmaly."""
    return str(uid) == str(ADMIN_ID) or (ZK and ZK.staffmy(uid))


def _zk_tap(zakazlar, kod):
    for z in zakazlar:
        if z["kod"] == kod:
            return z
    return None


def _zk_duwmeler(z, tapylan=0):
    """
    ⚠️ 24.08 — DUWMELER BULASHYARDY.
    Erkin sorady: "3 sany name zat?"
    Sebabi: "Auksionlardan gozle" (HEREKET) we "Gozlenyar" (STATUS)
    ikisinde hem 🔍 emoji bardy — birmenzesh gorunyardi.
    Indi: hereket duwmesi bashga emoji + uly harp, status duwmeleri
    "→" bilen bashlaya (status BELLEMEK diyip dushnukli bolsun).
    """
    setirler = []
    # 1) HEREKET — auksionlardan gozleyar, sargyda degmeya
    if tapylan:
        setirler.append([InlineKeyboardButton(
            f"🔎 {tapylan} MAŞYNY GÖRKEZ", callback_data=f"zkg:{z['kod']}")])
    else:
        setirler.append([InlineKeyboardButton(
            "🔎 AUKSIONLARDAN GÖZLE", callback_data=f"zkg:{z['kod']}")])
    # 2) STATUS bellemek — Notion-da yagdayy uytgedya
    setirler.append([
        InlineKeyboardButton("→ Gözlenýär", callback_data=f"zks:{z['kod']}:Gözlenýär"),
        InlineKeyboardButton("→ Tapyldy", callback_data=f"zks:{z['kod']}:Tapyldy"),
    ])
    setirler.append([
        InlineKeyboardButton("→ Auksionda", callback_data=f"zks:{z['kod']}:Auksionda"),
        InlineKeyboardButton("→ Alyndy", callback_data=f"zks:{z['kod']}:Alyndy"),
    ])
    if z.get("url"):
        setirler.append([InlineKeyboardButton("🔗 Notion-da aç", url=z["url"])])
    return InlineKeyboardMarkup(setirler)


async def zakazlar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Işlenmeli zakazlaryň sanawy (diňe işgärler)."""
    uid = update.effective_user.id
    if not _zk_rugsat(uid):
        await update.message.reply_text("⛔ Bu komanda diňe TEK topary üçin.")
        return
    if not _zk_bar():
        await update.message.reply_text(
            "⚙️ Zakaz sistemasy entek birikdirilmedik.\n\n"
            "_Railway → Variables → `NOTION_TOKEN` goşulmaly._",
            parse_mode="Markdown")
        return

    await update.message.chat.send_action("typing")
    mejbury = bool(context.args and context.args[0].lower() in ("tazele", "yenile"))
    zakazlar = await ZK.zakazlary_al(mejbury=mejbury)
    if not zakazlar:
        await update.message.reply_text(
            "📭 Notion-da açyk sargyt ýok.",
            reply_markup=ishgar_klawiatura())
        return

    # ⚠️ 24.08: Erkin "panel gitdi" diydi — ol ýazgy meýdanyna
    # bir zat ýazanda Telegram paneli ýygnaýar (adaty özüni alyp baryş).
    # Çözgüt: goşmaça habar ibermän, paneli SANAW habaryna dakýas.
    # Şeýdip her gezek sargyt görende panel özi yzyna gelýär.
    await _send_md_safe(update.message, ZK.sanaw_teksti(zakazlar),
                        reply_markup=ishgar_klawiatura())

    acyk = [z for z in zakazlar if z["status"] in ZK.ACIK_STATUS]
    if acyk:
        knopka, hatar = [], []
        for z in acyk[:12]:
            hatar.append(InlineKeyboardButton(z["kod"], callback_data=f"zk:{z['kod']}"))
            if len(hatar) == 3:
                knopka.append(hatar)
                hatar = []
        if hatar:
            knopka.append(hatar)
        await update.message.reply_text(
            "👇  Açmak üçin bas:",
            reply_markup=InlineKeyboardMarkup(knopka))


async def zakaz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/zakaz ZAK-3 — bir zakazyň jikme-jigi."""
    uid = update.effective_user.id
    if not _zk_rugsat(uid):
        await update.message.reply_text("⛔ Bu komanda diňe TEK topary üçin.")
        return
    if not _zk_bar():
        await update.message.reply_text("⚙️ Zakaz sistemasy birikdirilmedik.")
        return
    if not context.args:
        await update.message.reply_text(
            "Ulanyş: `/zakaz S-3`\n\nÄhli zakazlar: /zakazlar",
            parse_mode="Markdown")
        return

    kod = context.args[0].upper()
    zakazlar = await ZK.zakazlary_al()
    # Prefiks kodda gataldylmayar - bazadaky hakyky kodlardan alynya.
    # Erkin ony Notion-dan uytgedip bilya (ZAK -> S), bot ozi tutya.
    _pre = ZK.prefiks_tap(zakazlar)
    if _pre and not kod.upper().startswith(_pre.upper()):
        kod = f"{_pre}-" + kod.lstrip("-")
    z = _zk_tap(zakazlar, kod)
    if not z:
        await update.message.reply_text(f"📭 `{code_ok(kod)}` tapylmady.",
                                        parse_mode="Markdown")
        return

    cars = load_cars()
    # ⚠️ 26.08 — min_bal=3 (TAKYK gabatlama).
    # On bu yerde adaty gabatla() chagyrylyardy: model tapylmasa
    # MARKA boyuncha gin sanaw beryardi we sany "gabat gelyan masyn"
    # diyip gorkezyardi. Netije: "Lexus ES 350" sargydynda
    # "1 gabat gelyan masyn bar" yazyldy — ol Lexus UX-di.
    # Indi bu san dine hakyky model gabatlamasyny sanaya.
    tapylan = ZK.gabatla(z, cars, _norm, min_bal=3) if db_is_fresh(cars) else []
    await update.message.reply_text(
        ZK.jikme_jik_teksti(z, len(tapylan)),
        parse_mode="Markdown", reply_markup=_zk_duwmeler(z, len(tapylan)))


# ============================================================
# ISHGAR DUWMELERI — hemishelik panel
# ============================================================
# ⚠️ 24.08: Erkin "/sargyt yazmak halamok" diydi. Dogry — her gezek
# "/" basyp soz yazmak howlukmac ishde bogyar.
# Chozgut: ekranyn ashagynda HEMISHE duran duwmeler. Bir basyş.
# Diňe ISHGARLERE gorkezilya, mushderiler gormeya.
ISHGAR_DUWME = {
    "📋 Sargytlar": "sanaw",
    "🔄 Täzele": "tazele",
    "📅 Şu gün": "bugun",
}

def ishgar_klawiatura():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📋 Sargytlar")],
         [KeyboardButton("🔄 Täzele"), KeyboardButton("📅 Şu gün")]],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Maşyn gözlemek üçin ýaz…",
    )


async def sargyt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ESASY KOMANDA — bary bir sozde.

    /sargyt           -> acyk sargytlaryn sanawy
    /sargyt ST-4      -> shol sargydy acya
    /sargyt 4         -> deň (prefiks ozi goshulya)
    /sargyt tazele    -> Notion-dan tazeden okaya

    ⚠️ 24.08: on iki komanda bardy — /zakazlar we /zakaz.
    Erkin: "iki sozi yatda saklamak artykmac".
    Indi birew. Konelerinem ishlap dur (yatda galanlar ucin).
    """
    a = context.args or []
    _tazele = {"tazele", "yenile", "täzele", "ýenile"}
    if a and a[0].lower() not in _tazele:
        return await zakaz_command(update, context)      # bir sargyt
    return await zakazlar_command(update, context)       # sanaw


async def _zk_callback(q, context, d):
    """Zakaz düwmeleri. d — callback_data."""
    uid = q.from_user.id
    if not _zk_rugsat(uid):
        await q.message.reply_text("⛔ Bu diňe TEK topary üçin.")
        return
    if not _zk_bar():
        await q.message.reply_text("⚙️ Zakaz sistemasy birikdirilmedik.")
        return

    zakazlar = await ZK.zakazlary_al()

    # --- jikme-jik ---
    if d.startswith("zk:"):
        z = _zk_tap(zakazlar, d[3:])
        if not z:
            await q.message.reply_text("📭 Zakaz tapylmady.")
            return
        cars = load_cars()
        tapylan = ZK.gabatla(z, cars, _norm, min_bal=3) if db_is_fresh(cars) else []
        await q.message.reply_text(
            ZK.jikme_jik_teksti(z, len(tapylan)),
            parse_mode="Markdown", reply_markup=_zk_duwmeler(z, len(tapylan)))
        return

    # --- auksionlardan gözle ---
    if d.startswith("zkg:"):
        z = _zk_tap(zakazlar, d[4:])
        if not z:
            await q.message.reply_text("📭 Zakaz tapylmady.")
            return
        cars = load_cars()
        if not cars or not db_is_fresh(cars):
            await q.message.reply_text(NOT_READY_MSG, parse_mode="Markdown")
            return
        tapylan, takyk = ZK.gabatla_doly(z, cars, _norm)

        # 24.08 GOSHMACA — "model bar, yone yyly basga"
        # Onki nusga: takyk model tapylmasa gonuden-goni MARKA boyuncha
        # gin sanaw beryardi. Netije: "Camry 2021-2023" zakazyna
        # Hilux/Mirai/Highlander gelyardi - ishgar uchin peydasyz.
        # Emma shol gun 6 sany Camry bardy (2024-2025) we hemmesi
        # byujetden ARZANdy. Ine sholar gorkezilmeli.
        yyl_bellik = ""
        if not takyk:
            baska_yyl = ZK.model_bar_yyl_baska(z, cars, _norm)
            if baska_yyl:
                tapylan = baska_yyl
                takyk = True
                _yy = sorted({int(str(c.get("year"))[:4])
                              for c in baska_yyl if c.get("year")})
                _bahalar = [aed_to_usd(c.get("price")) for c in baska_yyl
                            if c.get("price")]
                _arzan = min(_bahalar) if _bahalar else 0
                _aralyk = (f"{_yy[0]}" if len(_yy) == 1
                           else f"{_yy[0]}-{_yy[-1]}")
                yyl_bellik = (
                    f"\n⚠️ _Zakazdaky ýylda ýok — ýöne şol model_ *{_aralyk}* "
                    f"_ýylda bar_")
                if _arzan:
                    yyl_bellik += f", _iň arzany_ *{_arzan:,} USD*"
                yyl_bellik += "."

        # 24.08 — MARKA BOYUNCHA NETIJE INDI AWTOMAT CHYKMAYA.
        # Sargyt "Mitsubishi L200" (pikap) boldy, bot "Mitsubishi Mirage"
        # (kici sedan) gorkezdi — peydasyz. Emma sargyt dine "Toyota"
        # bolsa marka boyuncha gorkezmek DOGRY. Tapawut: model aydylanmy.
        if not takyk and ZK.model_aydylanmy(z, cars, _norm):
            _n = len(tapylan)
            _dwm = None
            if _n:
                _dwm = InlineKeyboardMarkup([[InlineKeyboardButton(
                    f"Şonda-da görkez — {_n} sany",
                    callback_data=f"zkm:{z['kod']}")]])
            await q.message.reply_text(
                f"📭 `{code_ok(z['kod'])}` — *{esc(z['isleg'])}* "
                f"şu günki auksionlarda ýok.",
                parse_mode="Markdown", reply_markup=_dwm)
            return

        if not tapylan:
            await q.message.reply_text(
                f"📭 `{code_ok(z['kod'])}` — *{esc(z['isleg'])}* üçin "
                f"şu günki auksionlarda gabat gelýän maşyn ýok.",
                parse_mode="Markdown")
            return

        if yyl_bellik:
            bellik = yyl_bellik
        elif takyk:
            bellik = ""
        else:
            bellik = "\n⚠️ _Takyk model tapylmady — diňe marka boýunça._"
        await q.message.reply_text(
            f"🔍 `{code_ok(z['kod'])}` — *{len(tapylan)}* maşyn tapyldy "
            f"(býujet: {ZK._byujet_yaz(z)}){bellik}",
            parse_mode="Markdown")
        await send_batch(q.message, str(uid), tapylan,
                         title=f"zakaz {z['kod']}")

        # kody Notion-a ýazmak üçin düwmeler
        hatar = []
        for c in tapylan[:6]:
            k = get_car_code(c)
            if k:
                hatar.append([InlineKeyboardButton(
                    f"📌 {k} → Notion-a ýaz",
                    callback_data=f"zkk:{z['kod']}:{k}")])
        if hatar:
            await q.message.reply_text(
                "👇 Müşderä hödürlejek maşynyňy saýla — kody Notion-a ýazaryn:",
                reply_markup=InlineKeyboardMarkup(hatar))
        return

    # --- "şonda-da görkez": diňe marka boýunça giň sanaw ---
    if d.startswith("zkm:"):
        z = _zk_tap(zakazlar, d[4:])
        if not z:
            await q.message.reply_text("📭 Sargyt tapylmady.")
            return
        cars = load_cars()
        if not cars or not db_is_fresh(cars):
            await q.message.reply_text(NOT_READY_MSG, parse_mode="Markdown")
            return
        gin = ZK.gabatla(z, cars, _norm, min_bal=2)
        if not gin:
            await q.message.reply_text("📭 Ol marka boýunça-da maşyn ýok.")
            return
        await q.message.reply_text(
            f"🔎 `{code_ok(z['kod'])}` — diňe *marka* boýunça "
            f"*{len(gin)}* maşyn\n"
            f"⚠️ _Model gabat gelenok — müşderä görkezmezden öň seret._",
            parse_mode="Markdown")
        await send_batch(q.message, str(uid), gin, title=f"sargyt {z['kod']}")
        return

    # --- maşyn kodyny Notion-a ýaz ---
    if d.startswith("zkk:"):
        bolek = d[4:].split(":", 1)
        if len(bolek) != 2:
            return
        kod, masyn_kod = bolek
        z = _zk_tap(zakazlar, kod)
        if not z:
            await q.message.reply_text("📭 Zakaz tapylmady.")
            return
        bar = [x.strip() for x in (z.get("masyn_kody") or "").split(",") if x.strip()]
        if masyn_kod not in bar:
            bar.append(masyn_kod)
        ok = await ZK.notion_yaz(z["id"], "Maşyn kody", ", ".join(bar))
        if ok:
            await ZK.notion_yaz(z["id"], "Status", "Tapyldy")
            await q.message.reply_text(
                f"✅ `{code_ok(masyn_kod)}` Notion-a ýazyldy → `{code_ok(kod)}`\n"
                f"Status: *Tapyldy*",
                parse_mode="Markdown")
        elif ok == "meydan_yok":
            # Erkin tablisany sadalashdyranda 'Masyn kody' sutunini pozan
            # bolmagy mumkin. Yalnyshlyk dal - dushnukli aydyas.
            await q.message.reply_text(
                f"ℹ️ Maşyn kody Notion-a ýazylmady — *Maşyn kody* diýen "
                f"sütün tablisada ýok.\n\n"
                f"Saýlanan kod: `{esc(', '.join(bar))}`\n"
                f"_Gerek bolsa Notion-da şol atda tekst sütünini goş._",
                parse_mode="Markdown")
        else:
            await q.message.reply_text("❌ Notion-a ýazyp bolmady. Loga seret.")
        return

    # --- status üýtget ---
    if d.startswith("zks:"):
        bolek = d[4:].split(":", 1)
        if len(bolek) != 2:
            return
        kod, taze = bolek
        z = _zk_tap(zakazlar, kod)
        if not z:
            await q.message.reply_text("📭 Zakaz tapylmady.")
            return
        ok = await ZK.notion_yaz(z["id"], "Status", taze)
        if ok:
            await q.message.reply_text(
                f"✅ `{code_ok(kod)}` → *{esc(taze)}*", parse_mode="Markdown")
        else:
            await q.message.reply_text("❌ Notion-a ýazyp bolmady.")
        return


async def _sargyt_habar_isle(app, hasabat=None):
    """Bir gezek barlap, tapylan masynlar hakda habar iberya.

    ⚠️ 26.08 — AYRY FUNKSIYA EDILDI.
    On bu logika dine 30 minutlyk dowrun ichindedi. Ishlemese
    NAM UCHIN ishlemeyanini gormek MUMKIN DALDI — log Railway-da,
    Erkin bolsa dine "habar gelmedi" goryardi.
    Indi /sargytbarla komandasy shu ayny funksiyany chagyryp,
    her adimin netijesini yazyp beryar.

    hasabat — sanaw berilse, her adim shoňa yazylya.
    """
    def _y(t):
        if hasabat is not None:
            hasabat.append(t)

    if not _zk_bar():
        _y("❌ Sargyt moduly ÖÇÜK (NOTION_TOKEN ýok)")
        return 0
    _y("✅ Sargyt moduly açyk")

    alyjylar = ([ZK.TOPAR_CHAT_ID] if ZK.TOPAR_CHAT_ID
                else sorted(set(ZK.STAFF_IDS) | {str(ADMIN_ID)}))
    _y(f"📬 Alyjylar: {', '.join(alyjylar) if alyjylar else '—'}"
       + ("  _(topar grupbasy)_" if ZK.TOPAR_CHAT_ID else "  _(işgärler)_"))
    if not alyjylar:
        return 0

    cars = load_cars()
    _y(f"📦 Baza: {len(cars)} maşyn  ·  täze: {'hawa' if db_is_fresh(cars) else 'ÝOK'}")
    if not cars or not db_is_fresh(cars):
        _y("❌ Baza şu günki däl — habar iberilmeýär")
        return 0

    try:
        zakazlar = await ZK.zakazlary_al(mejbury=True)
    except Exception as e:
        _y(f"❌ Notion okalmady: {esc(str(e)[:80])}")
        return 0
    _y(f"📋 Notion-da {len(zakazlar)} sargyt")

    ugradyldy = 0
    for z in zakazlar:
        if z["status"] not in ("Täze", "Gözlenýär"):
            _y(f"   ⏭ `{z['kod']}` {esc(z['isleg'][:22])} — status «{esc(z['status'])}»")
            continue
        # AWTOMAT habar diňe TAKYK gabatlamada — ýogsa
        # "Nissan" zakazy her gün 40 maşyn spam eder
        tapylan = ZK.gabatla(z, cars, _norm, min_bal=3)
        gorlen = ZK._habar_berlen.setdefault(z["kod"], set())
        taze = [c for c in tapylan
                if get_car_code(c) and get_car_code(c) not in gorlen]
        _y(f"   • `{z['kod']}` {esc(z['isleg'][:22])} — "
           f"tapylan {len(tapylan)}, täze {len(taze)}")
        if not taze:
            continue
        for c in taze:
            gorlen.add(get_car_code(c))

        kodlar = ", ".join(f"`{get_car_code(c)}`" for c in taze[:8])
        _tekst = (f"🔔 *SARGYT ÜÇIN MAŞYN TAPYLDY*\n\n"
                  f"`{z['kod']}` — {esc(z['at'])}\n"
                  f"🚗 {esc(z['isleg'])}\n"
                  f"💰 {ZK._byujet_yaz(z)}\n\n"
                  f"*{len(taze)}* täze maşyn: {kodlar}\n\n"
                  f"_Görmek üçin_ `/sargyt {z['kod']}`")
        for _al in alyjylar:
            try:
                await app.bot.send_message(chat_id=int(_al), text=_tekst,
                                           parse_mode="Markdown")
                ugradyldy += 1
            except Exception as e:
                logger.error("sargyt habar (%s): %s", _al, e)
                _y(f"      ❌ {_al}: {esc(str(e)[:60])}")
        ZK._hb_yaz()
        await asyncio.sleep(1)
    _y(f"📨 Jemi {ugradyldy} habar iberildi")
    return ugradyldy


async def zakaz_gozegcilik(app):
    """AWTOMAT: her 30 minutda açyk sargytlara gabat gelýän täze
    maşyn bar bolsa habar berýär. Işgär hiç zat barlamaly däl."""
    await asyncio.sleep(120)
    while True:
        try:
            await _sargyt_habar_isle(app)
        except Exception as e:
            logger.error("zakaz_gozegcilik: %s", e)
        await asyncio.sleep(1800)   # 30 minutda bir


async def sargytbarla_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/sargytbarla — awtomat habar ulgamyny HÄZIR işledýär we
    her ädimiň netijesini görkezýär. Diňe admin."""
    if update.effective_user.id != ADMIN_ID:
        return
    hasabat = []
    try:
        await _sargyt_habar_isle(context.application, hasabat)
    except Exception as e:
        hasabat.append(f"❌ ÝALŇYŞLYK: {esc(str(e)[:120])}")
        logger.exception("sargytbarla")
    await update.message.reply_text(
        "🔍 *SARGYT HABAR BARLAGY*\n\n" + "\n".join(hasabat),
        parse_mode="Markdown")


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

    # --- ISHGAR DUWMELERI (24.08) ---
    # Panel duwmesine basylanda Telegram adaty TEKST iberya.
    # Shol tekstleri masyn gozlegine gecirmeli DAL — ilki shu barlag.
    if text in ISHGAR_DUWME and _zk_rugsat(update.effective_user.id):
        isi = ISHGAR_DUWME[text]
        if isi == "bugun":
            return await today_command(update, context)
        context.args = ["tazele"] if isi == "tazele" else []
        return await sargyt_command(update, context)

    tl = text.lower()
    tu = text.upper()
    track_user(update, text)
    cars = load_cars()

    # Arka planda alertleri barla (blokirlemeya)
    try:
        asyncio.create_task(check_alerts(context.bot))
    except Exception as e:
        logger.error(f"alert task: {e}")

    fresh = db_is_fresh(cars)

    # ============================================================
    # KOD boýunça gözleg — SENE BARLAGYNDAN ÖŇ
    # ------------------------------------------------------------
    # Sebäp (Erkin, 15.08): TikTok-a goýlan kart bir günlük däl.
    # Müşderi ertesi gün kody ýazsa "maglumat taýýar däl" görse —
    # reklama puly ýanýar. Kod HEMIŞE jogap bermeli.
    # ============================================================
    mcode = re.search(r'\b(\d{4})\s*[-–—/]\s*(\d{1,3})\b', tu)
    if mcode:
        want = f"{mcode.group(1)}-{int(mcode.group(2)):03d}"
        hit = [c for c in cars if str(c.get("code", "")).upper() == want]
        if hit:
            if fresh:
                await update.message.reply_text(
                    f"🆔 *{esc(want)}* — tapyldy:", parse_mode="Markdown")
            else:
                d = str(hit[0].get("date", ""))
                ds = f"{d[6:8]}.{d[4:6]}" if len(d) == 8 else d
                await update.message.reply_text(
                    f"🆔 *{esc(want)}* — tapyldy\n\n"
                    f"⚠️ Bu maşyn *{ds}* auksionyndan. Şol auksion geçdi.\n"
                    f"Goşmaça soragyňyz bolsa WhatsApp-a ýazyň 👇",
                    parse_mode="Markdown")
            for car in hit:
                await send_car_with_photo(update, car)
            log_search(want, "found", None, len(hit))
            return
        log_search(want, "none")
        await update.message.reply_text(
            f"📭 *{esc(want)}* kody bilen maşyn tapylmady.\n\n"
            "Kody ýene bir gezek barlaň — kartda ýazylan görnüşde ýazyň.",
            parse_mode="Markdown", reply_markup=contact_keyboard())
        return

    if not fresh:
        await update.message.reply_text(NOT_READY_MSG, parse_mode="Markdown", reply_markup=contact_keyboard())
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
# YALNYSHLYK TUTUJY
# ============================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """
    ⚠️ 24.08 SAPAGY — NAM UCHIN BU GEREK:
    Erkin "Auksionlardan gozle" duwmesine basdy — HIC HILI REAKSIYA
    BOLMADY. Sebabi kodda kici yalnyshlyk bardy (KeyError: 'byujet'),
    yone botda yalnyshlyk tutujy YOKDY. Telegram logda
    "No error handlers are registered" diyip yazdy we bot DYMDY.

    Ishgar uchin bu in erbet yagday: duwma basyan, hic zat bolonok,
    name uchindigi belli dal. Sebabini tapmak uchin Railway logyna
    girmeli bolyar.

    Indi: islendik yalnyshlykda ulanyja gysga habar iberilya,
    admine bolsa doly sebabi. Bot yene ishlap dur.
    """
    import traceback
    e = context.error
    logger.error("Tutulmadyk yalnyshlyk: %s", e, exc_info=e)

    # 1) Ulanyja — gysga we dushnukli
    try:
        ch = None
        if isinstance(update, Update):
            if update.callback_query:
                ch = update.callback_query.message
            elif update.message:
                ch = update.message
        if ch:
            await ch.reply_text(
                "⚠️ Bir zat ýalňyş gitdi — ýazgy alyndy, düzediler.\n"
                "_Gaýtadan synanyşyp gör._",
                parse_mode="Markdown")
    except Exception:
        pass

    # 2) Admine — doly sebabi (sebabini gozlap yormeli bolmasyn)
    try:
        nire = ""
        if isinstance(update, Update):
            if update.callback_query:
                nire = f"düwme: `{update.callback_query.data}`"
            elif update.message and update.message.text:
                nire = f"habar: `{update.message.text[:60]}`"
        tb = "".join(traceback.format_exception(
            type(e), e, e.__traceback__))[-1200:]
        await context.bot.send_message(
            ADMIN_ID,
            f"🐞 *Botda ýalňyşlyk*\n{nire}\n\n```\n{tb}\n```",
            parse_mode="Markdown")
    except Exception:
        pass


# ============================================================
# CALLBACK
# ============================================================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data or ""

    # zakaz düwmeleri (diňe işgärler)
    if d.startswith(("zk:", "zkg:", "zkk:", "zks:", "zkm:")):
        await _zk_callback(q, context, d)
        return

    # Gundelik habaryn duwmeleri (25.08)
    if d.startswith("hbr:"):
        nam = d[4:]
        uid = str(q.from_user.id)
        _habar_basyldy(nam, uid)
        if nam == "today":
            await today_command(q, context)
        elif nam == "gozle":
            await q.message.reply_text(
                "🔎 *Maşyn gözlemek*\n\n"
                "Marka ýa model ýazyň — mysal üçin:\n"
                "`camry` · `rav4` · `sonata` · `k5`\n\n"
                "Ýyl hem goşup bilersiňiz: `camry 2023`",
                parse_mode="Markdown")
        elif nam == "off":
            users = load_users()
            if uid in users:
                users[uid]["habar_ochuk"] = True
                save_users(users)
            await q.message.reply_text(
                "🔕 Gündelik habar öçürildi.\n\n"
                "Bot öňküsi ýaly işleýär — islän wagtyňyz marka ýazyp "
                "maşyn gözläp bilersiňiz.\n\n"
                "Yzyna açmak: /habar\_ac")
        return

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
# GUNDELIK HABAR — mushderileri bota yzyna getirmek  (25.08)
#
# Erkin: "Maksat mushderilerimize telegram bota girer yaly etmek,
#         ya-da botun barlygyny yatlatmak."
#
# ⚠️ SHONUN UCHIN BU HABAR STATISTIKA HASABATY DAL.
#    Adam sany okap dal, DUWMÄ BASSYN diyip yazylan:
#      - gysga (bir ekran)
#      - bir sany uly san (gyzyklandyryjy)
#      - ashagynda 2 duwme: "Shu gunki auksionlar" / "Masyn gozle"
#
# ⚠️ ÖCHÜRMEK DUWMESI HÖKMAN.
#    Hemme ulanyja gidyar. Halamadyk adam bota BLOK etse — ony
#    hemishelik yitirdik. "Habary ochur" duwmesi bolsa, ol dine
#    habary ochurya, bot ozi yerinde galya.
# ============================================================
HABAR_FILE = _DATA_DIR / "gundelik_habar.json"
HABAR_SAGAT = 9              # Dubay wagty. Ahli PDF 02:30-a chenli tayyar.


def _habar_yagdayi():
    try:
        return json.loads(HABAR_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _habar_yaz(d):
    try:
        HABAR_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    except Exception as e:
        logger.error("habar yagdayi yazylmady: %s", e)


_AYLAR = ["ýanwar", "fewral", "mart", "aprel", "maý", "iýun",
          "iýul", "awgust", "sentýabr", "oktýabr", "noýabr", "dekabr"]
# ⚠️ 25.08 — Erkin: "sişenbe, duşenbe diyip yazmada, 3-nji gun diyip yazay".
# Tertip AUKSION EKSELI bilen deň: 1 GUN = duşenbe ... 7 GUN = ýekşenbe.
# (Python-yn weekday() hem şeýle: duşenbe=0, şonuň üçin +1 edilýär.)
_GUN_ATLARY = ["1-nji gün", "2-nji gün", "3-nji gün", "4-nji gün",
               "5-nji gün", "6-njy gün", "7-nji gün"]


def _habar_basyldy(nam, uid):
    """Duwma basylanda hasaba alya — habar ishleyarmi, sho bilinsin."""
    try:
        st = _habar_yagdayi()
        if st.get("gun") != get_today():
            return
        b = st.setdefault("basyldy", {})
        b[nam] = b.get(nam, 0) + 1
        adamlar = st.setdefault("basan_adamlar", [])
        if uid not in adamlar:
            adamlar.append(uid)
        _habar_yaz(st)
    except Exception as e:
        logger.warning("habar basyldy: %s", e)


def gundelik_habar_tekst(cars, today):
    """Gysga, gyzyklandyryjy habar. Uzyn sanaw YOK — ol /today-da."""
    bu_gun = [c for c in cars if str(c.get("date")) == today]
    if not bu_gun:
        return None

    # auksion = at + shahamcha + sagat (Marhaba 4 yerde ishleya)
    auk = {}
    for c in bu_gun:
        acar = (c.get("auction", "?"), (c.get("auction_branch") or "").strip(),
                (c.get("auction_time") or "").strip())
        auk[acar] = auk.get(acar, 0) + 1

    sagatlar = sorted(w for (_a, _s, w) in auk if w)
    yerler = sorted({s for (_a, s, _w) in auk if s})
    markalar = {}
    for c in bu_gun:
        b = str(c.get("brand") or "").strip()
        if b:
            markalar[b] = markalar.get(b, 0) + 1
    top = [m for m, _ in sorted(markalar.items(), key=lambda x: -x[1])[:4]]

    d = datetime.strptime(today, "%Y%m%d")
    sene = f"{d.day} {_AYLAR[d.month - 1]}, {_GUN_ATLARY[d.weekday()]}"

    # ⚠️ 25.08 — Erkin sada gornushi saylady.
    # "tayyar", "baslayar" yaly sozler her gun gaytalansa gury sese
    # owrulya. Chenňek SAN — "584 masyn". Sozlem dine tanatma.
    t = "🌅 *Şu günki auksionlar*\n\n"
    t += f"📅 {sene}\n"
    t += f"🚗 *{len(bu_gun)} maşyn*  ·  {len(auk)} auksion\n"
    if sagatlar:
        t += f"🕐 {esc(sagatlar[0])} — {esc(sagatlar[-1])}\n"
    if yerler:
        t += f"📍 {esc(' · '.join(yerler))}\n"
    if top:
        t += f"\n🔥 Iň köp: {esc(' · '.join(top))}\n"
    t += "\n_Marka ýa model ýaz — men tapyp bereýin._"
    return t


def _habar_duwmeler():
    # ⚠️ 25.08 — "Bu habary ochur" DUWMESI AYRYLDY (Erkin).
    #   "her gun yekeje bildiris olaryn yuregine dushmez.
    #    son statistika seredip karar bereris."
    # Kod ozi YERINDE galya: /habar_ochur komandasy we habar_ochuk
    # belligi ishleya. Yagny biri sikayat etse, ishgar shol adam uchin
    # ochurip bilya — bot bloklanmaz. Duwmani yzyna getirmek bir setir.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Auksionlary gör", callback_data="hbr:today")],
        [InlineKeyboardButton("🔎 Maşyn gözle", callback_data="hbr:gozle")],
    ])


async def gundelik_habar_ugrat(app, diňe_uid=None):
    """Habary ugradýar. diňe_uid berilse — synag, dine sho adama."""
    cars = load_cars()
    today = get_today()
    t = gundelik_habar_tekst(cars, today)
    if not t:
        return 0, 0, "maglumat yok"

    kb = _habar_duwmeler()
    if diňe_uid:
        await app.bot.send_message(int(diňe_uid), t, parse_mode="Markdown",
                                   reply_markup=kb)
        return 1, 0, "synag"

    users = load_users()
    gitdi = bolmady = 0
    for uid, u in list(users.items()):
        if u.get("habar_ochuk") or u.get("bloklady"):
            continue
        try:
            await app.bot.send_message(int(uid), t, parse_mode="Markdown",
                                       reply_markup=kb)
            gitdi += 1
        except Forbidden:
            # Adam boty blok edipdir — indi synanyshmaly dal
            u["bloklady"] = True
            bolmady += 1
        except Exception as e:
            logger.warning("gundelik habar (%s): %s", uid, e)
            bolmady += 1
        # ⚠️ Telegram sekuntda ~30 habar gechirya. 25-e chenli sakla.
        await asyncio.sleep(0.05)
    save_users(users)
    return gitdi, bolmady, "ok"


async def gundelik_habar_loop(app):
    """Her 10 minutda barlaýar. Bir günde BIR gezek ugradýar."""
    await asyncio.sleep(120)
    while True:
        try:
            now = datetime.now(DUBAI_TZ)
            today = get_today()
            st = _habar_yagdayi()
            if (st.get("gun") != today
                    and now.hour >= HABAR_SAGAT
                    and db_is_fresh(load_cars())):
                # ⚠️ ILKI BELLIK, SONRA UGRAT. Ugratmak birnache minut
                # dowam edip biler; shol wagt loop yene gelse IKI GEZEK
                # gitmezi yaly gun derrew belgilenya.
                _habar_yaz({"gun": today, "wagt": now.strftime("%H:%M")})
                g, b, _ = await gundelik_habar_ugrat(app)
                _habar_yaz({"gun": today, "wagt": now.strftime("%H:%M"),
                            "gitdi": g, "bolmady": b})
                logger.info("Gundelik habar: %d gitdi, %d bolmady", g, b)
                try:
                    await app.bot.send_message(
                        ADMIN_ID,
                        f"📣 *Gündelik habar ugradyldy*\n\n"
                        f"✅ {g} adama gitdi\n"
                        f"⚠️ {b} bolmady (blok eden ýa öçüren)",
                        parse_mode="Markdown")
                except Exception:
                    pass
        except Exception as e:
            logger.error("gundelik_habar_loop: %s", e)
        await asyncio.sleep(600)


def _basyldy_setir(st):
    b = st.get("basyldy", {})
    if not b:
        return "entek ýok"
    at = {"today": "auksionlar", "gozle": "gözleg"}
    return " · ".join(f"{at.get(k, k)} {v}" for k, v in b.items())


async def habar_ochur_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/habar_ochur — gundelik habary ochurya.

    ⚠️ Duwme hokmunde GORKEZILMEYA (Erkin, 25.08). Emma komanda
    yerinde — biri "maňa habar gelmesin" diyse, bot ony blok
    etmeginin deregine shu komandany ulanyp biler.
    """
    uid = str(update.effective_user.id)
    users = load_users()
    if uid in users:
        users[uid]["habar_ochuk"] = True
        save_users(users)
    await update.message.reply_text(
        "🔕 Gündelik habar öçürildi.\n\nYzyna açmak: /habar\_ac")


async def habar_ac_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/habar_ac — ochurilen gundelik habary yzyna achya."""
    uid = str(update.effective_user.id)
    users = load_users()
    if uid in users:
        users[uid]["habar_ochuk"] = False
        save_users(users)
    await update.message.reply_text(
        "🔔 Gündelik habar yzyna açyldy.\n\n"
        "Her gün ir bilen şol günki auksionlar barada gysgaça habar bererin.")


async def habar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/habar — diňe admin. Habary görkezýär (hiç kime gitmeýär)."""
    if update.effective_user.id != ADMIN_ID:
        return
    arg = (context.args[0].lower() if context.args else "")
    if arg == "ugrat":
        g, b, ýagdaý = await gundelik_habar_ugrat(context.application)
        await update.message.reply_text(
            f"📣 Ugradyldy: {g} adam · {b} bolmady ({ýagdaý})")
        return
    cars = load_cars()
    t = gundelik_habar_tekst(cars, get_today())
    if not t:
        await update.message.reply_text("⚠️ Şu günki maglumat entek ýok.")
        return
    st = _habar_yagdayi()
    users = load_users()
    ochuk = sum(1 for u in users.values() if u.get("habar_ochuk"))
    blok = sum(1 for u in users.values() if u.get("bloklady"))
    await update.message.reply_text(t, parse_mode="Markdown",
                                    reply_markup=_habar_duwmeler())
    await update.message.reply_text(
        f"👆 _Şu görnüşde gider._\n\n"
        f"👥 Aljak: *{len(users) - ochuk - blok}* adam\n"
        f"🔕 Öçüren: {ochuk}  ·  🚫 Blok eden: {blok}\n"
        f"🕘 Her gün sagat {HABAR_SAGAT}:00 (Dubaý)\n\n"
        f"📆 *Iň soňky ugradylan:* {st.get('gun', '—')} {st.get('wagt', '')}\n"
        f"   ✅ {st.get('gitdi', 0)} gitdi  ·  ⚠️ {st.get('bolmady', 0)} bolmady\n"
        f"   👆 {len(st.get('basan_adamlar', []))} adam düwmä basdy"
        f"  ({_basyldy_setir(st)})\n\n"
        f"_Häzir ugratmak: /habar ugrat_",
        parse_mode="Markdown")


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
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("alert", alert_command))
    app.add_handler(CommandHandler("myalerts", myalerts_command))
    app.add_handler(CommandHandler("delalert", delalert_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("checkalerts", checkalerts_command))
    app.add_handler(CommandHandler("hasabat", hasabat_command))
    app.add_handler(CommandHandler("habar", habar_command))
    app.add_handler(CommandHandler("habar_ac", habar_ac_command))
    app.add_handler(CommandHandler("habar_ochur", habar_ochur_command))
    app.add_handler(CommandHandler("sargytbarla", sargytbarla_command))
    app.add_handler(CommandHandler("gozleg", gozleg_command))
    app.add_handler(CommandHandler("sonky", sonky_command))
    # Yalnyshlyk tutujy — bot indi dymmaya (24.08)
    app.add_error_handler(error_handler)

    # ESASY: /sargyt — sanaw hem, bir sargyt hem, tazelemek hem
    app.add_handler(CommandHandler("sargyt", sargyt_command))
    app.add_handler(CommandHandler("sargytlar", sargyt_command))
    # Koneler — yatda galanlar ucin ishlap dur
    app.add_handler(CommandHandler("zakazlar", zakazlar_command))
    app.add_handler(CommandHandler("zakaz", zakaz_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Dubai Auksion | TEK AUTO MARKET boty işläp başlady!")
    app.run_polling()


if __name__ == "__main__":
    main()

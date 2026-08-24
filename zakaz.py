#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZAKAZ MODULY  —  Notion  ->  Telegram (diňe işgärler üçin)
==========================================================
Erkin müşderi bilen gepleşýär, ähli maglumaty alýar, NOTION-a ýazýar.
Işgärler şol zakazlary TELEGRAM BOTDA görýär we işleýär.

Müşderi bu komandalary GÖRMEÝÄR. Diňe STAFF_IDS-däki adamlar.

NÄME EDÝÄR
----------
1. Notion "Zakazlar" bazasyny okaýar (5 minutda bir gezek keşleýär).
2. /zakazlar        -> işlenmeli zakazlaryň sanawy
3. Zakaza basylanda -> jikme-jik + "auksionlardan gözle" düwmesi
4. AWTOMAT GABATLAMA: her gün täze maşynlar gelende, açyk zakazlara
   gabat gelýän maşyn bar bolsa TOPAR GRUPBASYNA habar berýär.
5. Tapylan maşynyň kody bir düwme bilen NOTION-a ýazylýar
   -> Erkin iki gezek ýazmaly bolmaýar.

GEREK ÜÝTGEÝJILER (Railway -> Variables)
----------------------------------------
  NOTION_TOKEN     ntn_...        <- Notion integrasiýa açary (hökman)
  STAFF_IDS        123,456,789    <- işgärleriň Telegram ID-leri
  TOPAR_CHAT_ID    -1001234567890 <- topar grupbasy (islege bagly)
  NOTION_ZAKAZ_DB  (aşakda ýazyldy, üýtgetmeseň bolýar)

NOTION_TOKEN ÝOK BOLSA: modul dymýar, bot öňki ýaly işleýär. Ýykylmaýar.
"""
import asyncio
import difflib
import json
import logging
import os
import re
from datetime import datetime, timedelta

# httpx — python-telegram-bot bilen bile gelýär, goşmaça gurnama gerek däl.
# Bolmasa-da modul ýykylmaýar, diňe Notion öçük galýar.
try:
    import httpx
except Exception:                                    # pragma: no cover
    httpx = None

try:
    import byujet as BYUJET
except Exception:                                    # pragma: no cover
    BYUJET = None

logger = logging.getLogger(__name__)

# ============================================================
# SAZLAMALAR
# ============================================================
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "").strip()
NOTION_VER = "2022-06-28"
ZAKAZ_DB = os.environ.get(
    "NOTION_ZAKAZ_DB", "6cc94eb79db0489c9a3c12e489e37838").replace("-", "")

TOPAR_CHAT_ID = os.environ.get("TOPAR_CHAT_ID", "").strip()

# Işgärler — diňe şular zakaz görýär
_raw_staff = os.environ.get("STAFF_IDS", "")
STAFF_IDS = {s.strip() for s in _raw_staff.replace(";", ",").split(",") if s.strip()}

USD_RATE = 3.67

# Işlenmeli hasap edilýän statuslar (gutaranlar sanawda görünmeýär)
ACIK_STATUS = {"Täze", "Gözlenýär", "Tapyldy", "Auksionda"}

# Keş — Notion-a her gezek soramaz ýaly
_cache = {"wagt": None, "zakazlar": []}
CACHE_MIN = 5

# Haýsy zakaza haýsy maşyn eýýäm habar berildi (gaýtalanmaz ýaly)
_habar_berlen = {}   # {zakaz_id: set(car_code)}


def isleyarmi():
    """Modul işjeňmi — token hem httpx bar bolsa hawa."""
    return bool(NOTION_TOKEN) and httpx is not None


def staffmy(user_id):
    """Şu adam işgärmi?"""
    return str(user_id) in STAFF_IDS


# ============================================================
# NOTION OKAMAK
# ============================================================
def _hdr():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VER,
        "Content-Type": "application/json",
    }


def _tekst(prop):
    """Notion property -> arassa tekst/san. Ähli görnüşi tutýar."""
    if not prop:
        return ""
    t = prop.get("type")
    if t == "title":
        return "".join(x.get("plain_text", "") for x in prop.get("title", []))
    if t == "rich_text":
        return "".join(x.get("plain_text", "") for x in prop.get("rich_text", []))
    if t == "select":
        s = prop.get("select")
        return s.get("name", "") if s else ""
    if t == "number":
        return prop.get("number")
    if t == "phone_number":
        return prop.get("phone_number") or ""
    if t == "unique_id":
        u = prop.get("unique_id") or {}
        pre = u.get("prefix") or ""
        num = u.get("number")
        return f"{pre}-{num}" if num is not None else ""
    if t == "created_time":
        return prop.get("created_time") or ""
    if t == "relation":
        return [r.get("id") for r in prop.get("relation", [])]
    if t == "formula":
        f = prop.get("formula") or {}
        return f.get(f.get("type"), "")
    return ""


def _at_tap(p):
    """
    Zakazyn ADYNY (title meydany) tapya.

    ⚠️ 24.08 SAPAGY — NAM UCHIN ADY BOYUNCHA GOZLEMEYAS:
    Notion-da forma sazlananda "Sync with property name" achyk bolsa,
    forma soragynyn ady UYTGESE — bazadaky sutunin ady hem uytgeya.
    Shol gun "Zakaz" sutuni "Müşderiniň ady" bolup uytgedi we
    p.get("Zakaz") None gaytardy — hemme zakaz "(atsyz)" bolup chykardy.

    Indi: ady dal-de TIPI boyuncha gozleyas. Notion bazasynda title
    meydany diňe BIREW bolya, shon uchin bu usul hemishe dogry.
    At uytgese-de bot dowulmeya.

    Yzyna gaytarylyan: title meydanynyn teksti (bosh bolup biler).
    """
    # 1. Tip boyuncha (esasy usul - at uytgese-de ishleya)
    for ad, prop in p.items():
        if isinstance(prop, dict) and prop.get("type") == "title":
            t = _tekst(prop)
            if t:
                return t
    # 2. Atiyachlyk: kone atlar (tip tapylmadyk yagdayda)
    for ad in ("Zakaz", "Müşderiniň ady", "Name", "Title"):
        t = _tekst(p.get(ad))
        if t:
            return t
    return ""


def _kod_tap(p):
    """
    Sargyt KODUNY (unique_id meydany) tapya: 'S-3'.

    ⚠️ 24.08 SAPAGY — bashlyk meydanda bolshy yaly, ADY BOYUNCHA DAL.
    Shol gun 'Zakaz ID' sutuni 'Sargyt №' bolup uytgedi.
    Ady boyuncha okasak, hemme kod 'S-?' bolup chykardy.
    Notion bazasynda unique_id meydany adatda birew bolya.
    """
    for ad, prop in p.items():
        if isinstance(prop, dict) and prop.get("type") == "unique_id":
            t = _tekst(prop)
            if t:
                return t
    # Atiyachlyk: kone/adaty atlar
    for ad in ("Sargyt №", "Zakaz ID", "ID"):
        t = _tekst(p.get(ad))
        if t:
            return t
    return ""


def prefiks_tap(zakazlar):
    """
    Zakaz kodlarynyn PREFIKSINI tapya: 'S-3' -> 'S',  'ZAK-7' -> 'ZAK'.

    ⚠️ 24.08: prefiks kodda GATALDYLMALY DAL.
    Erkin ony Notion-dan islendik wagt uytgedip bilya (ZAK -> S).
    Onki nusgada 'ZAK' kodda yazylgydy — uytgedilende
    '/zakaz 3' komandasy ishlemesini bes ederdi.
    Indi: bazadaky hakyky kodlardan okalya.
    """
    for z in zakazlar or []:
        k = (z.get("kod") or "").strip()
        if "-" in k:
            p = k.rsplit("-", 1)[0]
            if p and p != "?":
                return p
    return ""


def _byujet_meydan(p):
    """
    Byujet sutunini ADY BOYUNCHA DAL, adynyn ICINDAKI soz boyuncha tapya.
    'Býujet $' / 'Býujet' / 'Byujet AED' — hemmesi ishleya.
    (24.08 sapagy: gataldylan atlar dowulya.)
    """
    for ad, prop in p.items():
        a = str(ad).upper().replace("Ý", "Y").replace("Ü", "U")
        if "BYUJET" in a or "BUDJET" in a or "BUJET" in a:
            return _tekst(prop)
    return ""


def _setir(page):
    """Notion sahypasy -> ýönekeý dict."""
    p = page.get("properties", {})
    _b_asyl = _byujet_meydan(p)
    _b = BYUJET.oka(_b_asyl) if (BYUJET and _b_asyl) else None
    return {
        "byujet_asyl": _b_asyl,                       # Erkinin yazany
        "byujet_max": (_b or {}).get("max_usd"),      # suzguc uchin (USD)
        "byujet_okaldy": _b,                          # doly netije
        "id": page.get("id", ""),
        "url": page.get("url", ""),
        "kod": _kod_tap(p) or "?",
        "at": _at_tap(p) or "(atsyz)",
        "telefon": _tekst(p.get("Telefon")),
        "kanal": _tekst(p.get("Kanal")),
        "isleg": _tekst(p.get("Isleýän maşyny")),
        "status": _tekst(p.get("Status")) or "Täze",
        "masyn_kody": _tekst(p.get("Maşyn kody")),
        "bellik": _tekst(p.get("Bellik")),
        "gosulan": _tekst(p.get("Goşulan")),
    }


async def zakazlary_al(mejbury=False):
    """Notion-dan zakazlary alýar. 5 minut keşlenýär."""
    if not isleyarmi():
        return []

    indi = datetime.utcnow()
    if (not mejbury and _cache["wagt"]
            and indi - _cache["wagt"] < timedelta(minutes=CACHE_MIN)):
        return _cache["zakazlar"]

    out = []
    cursor = None
    try:
        async with httpx.AsyncClient(timeout=20) as cl:
            while True:
                body = {"page_size": 100}
                if cursor:
                    body["start_cursor"] = cursor
                r = await cl.post(
                    f"https://api.notion.com/v1/databases/{ZAKAZ_DB}/query",
                    headers=_hdr(), json=body)
                if r.status_code != 200:
                    logger.error("Notion %s: %s", r.status_code, r.text[:300])
                    return _cache["zakazlar"]
                d = r.json()
                for pg in d.get("results", []):
                    out.append(_setir(pg))
                if not d.get("has_more"):
                    break
                cursor = d.get("next_cursor")
    except Exception as e:
        logger.error("Notion okalmady: %s", e)
        return _cache["zakazlar"]

    # MYSAL setirini gizle
    out = [z for z in out if not z["at"].upper().startswith("MYSAL")]

    _cache["wagt"] = indi
    _cache["zakazlar"] = out
    logger.info("Notion: %d zakaz okaldy", len(out))
    return out


async def notion_yaz(page_id, meydan, bahasy):
    """
    Notion setirine ýazýar. meydan: 'Maşyn kody' ýa 'Status'.

    Yzyna:
      True          — yazyldy
      "meydan_yok"  — sheyle sutun Notion-da yok (Erkin pozan bolmagy mumkin)
      False         — bashga yalnyshlyk

    ⚠️ 24.08: Erkin tablisany SADALASHDYRYA — gereksiz sutunleri pozya.
    Sutun pozulsa bot "yalnyshlyk" diyip gorkezmeli dal, sebabini
    dushnukli aytmaly. Shon uchin ayratyn jogap goshuldy.
    """
    if not isleyarmi():
        return False
    if meydan == "Status":
        prop = {"select": {"name": bahasy}}
    else:
        prop = {"rich_text": [{"text": {"content": str(bahasy)[:1900]}}]}
    try:
        async with httpx.AsyncClient(timeout=20) as cl:
            r = await cl.patch(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=_hdr(), json={"properties": {meydan: prop}})
            if r.status_code == 200:
                _cache["wagt"] = None   # keşi täzele
                return True
            # Sutun yok bolsa Notion 400 + "is not a property" diyya
            jogap = (r.text or "").lower()
            if r.status_code == 400 and (
                    "is not a property" in jogap
                    or "property does not exist" in jogap
                    or "validation_error" in jogap and meydan.lower() in jogap):
                logger.warning("Notion-da '%s' sutuni yok", meydan)
                return "meydan_yok"
            logger.error("Notion ýazmady %s: %s", r.status_code, r.text[:300])
            return False
    except Exception as e:
        logger.error("Notion ýazmady: %s", e)
        return False


# ============================================================
# GABATLAMA — zakaz  <->  auksion maşynlary
# ============================================================
_DUR = {
    "ak", "gara", "cal", "gyzyl", "gok", "ak yada", "yada", "ya", "we", "bilen",
    "white", "black", "grey", "gray", "red", "blue", "silver", "kumus",
    "masyn", "masyny", "model", "yyl", "yyly", "arasy", "cenli", "cen",
    "gowy", "arzan", "gaty", "hokman", "islegli", "renk", "renkli",
}


def _yyllar(text):
    """Tekstden ýyllary çykar: '2021-2023' -> (2021, 2023)."""
    ys = [int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", text or "")]
    if not ys:
        return None, None
    return min(ys), max(ys)


def _sozluk(cars, norm_fn):
    """Bazadaky ähli marka/model sözleri — ýalňyş ýazgyny düzetmek üçin."""
    v = set()
    for c in cars:
        for s in (c.get("brand", ""), c.get("model", "")):
            for t in norm_fn(s).split():
                if len(t) > 2:
                    v.add(t)
    return v


def _fonetik(s):
    """Sesi meňzeş harplary birleşdirýär — türkmen/rus ýazgysy üçin.

    NÄME ÜÇIN: müşderi "kamry", "korola", "hunday" diýip ýazýar.
    Diňe difflib ulansaň bosaga peseltmeli bolýar, onda "patrol" -> "quattro"
    ýaly ÝALŇYŞ gabatlama çykýar (22.08-de synagda çykdy — müşderä Patrol
    ýerine Audi hödürlenerdi). Fonetika ony aradan aýyrýar:
        camry / kamry / kamri  ->  kamri
        corolla / korola       ->  korola
        hyundai / hunday       ->  hiundai / hundai  (0.93 meňzeş)
        patrol vs quattro      ->  patrol vs kuatro  (daş — ret edilýär)
    """
    s = (s or "").lower()
    s = s.replace("ck", "k").replace("ph", "f").replace("x", "ks")
    s = s.replace("c", "k").replace("q", "k").replace("w", "v")
    s = s.replace("y", "i")
    out = []
    for ch in s:
        if not out or out[-1] != ch:      # goşa harplary ýygna: ll -> l
            out.append(ch)
    return "".join(out)


def _duzet(toks, sozluk):
    """'kamry' -> 'camry',  'korola' -> 'corolla',  'hunday' -> 'hyundai'.

    Zakazy Erkin ýazýar, ýöne müşderiniň sözlerini göçürip ýazýar —
    şoň üçin ýalňyş ýazga çydamly bolmaly. Ýöne ÝALŇYŞ gabatlama
    hiç haçan bolmaly däl: müşderä Patrol ýerine Audi görkezmek —
    hiç zat tapmazlykdan erbet.
    """
    fon = {}
    for w in sozluk:
        fon.setdefault(_fonetik(w), w)

    out = set()
    for t in toks:
        if t in sozluk:
            out.add(t)
            continue
        ft = _fonetik(t)
        if ft in fon:                      # fonetik doly gabat — iň ynamly
            out.add(fon[ft])
            continue
        yakyn = difflib.get_close_matches(ft, list(fon.keys()), n=1, cutoff=0.78)
        out.add(fon[yakyn[0]] if yakyn else t)
    return out


def gabatla(zakaz, cars, norm_fn, min_bal=None, yyl_barla=True):
    """Zakaza gabat gelýän maşynlary tapýar.

    norm_fn — botuň öz _norm() funksiýasy (türkmen/rus harplaryny düzedýär).

    Iki geçiş:
      1) model gabat gelmeli (has takyk)
      2) hiç zat çykmasa — diňe marka boýunça
    Netije: bal boýunça tertipli sanaw.
    """
    isleg = zakaz.get("isleg") or zakaz.get("at") or ""
    want = norm_fn(isleg)
    if not want or not cars:
        return []

    y1, y2 = _yyllar(isleg)
    # bir ýyl ýazylsa ±1 ýyl rugsat, aralyk ýazylsa takyk aralyk
    if y1 and y1 == y2:
        y1, y2 = y1 - 1, y2 + 1

    toks = {t for t in want.split() if len(t) > 1 and t not in _DUR
            and not re.fullmatch(r"(?:19|20)\d{2}", t)}
    if not toks:
        return []
    toks = _duzet(toks, _sozluk(cars, norm_fn))

    try:
        byujet = float(zakaz.get("byujet_max") or 0)
    except Exception:
        byujet = 0

    def _gec(bosag):
        netije = []
        for c in cars:
            marka = norm_fn(c.get("brand", ""))
            model = norm_fn(c.get("model", ""))

            marka_hit = bool(marka) and marka.split()[0] in toks
            model_hit = any(t in toks for t in model.split() if len(t) > 2)
            bal = (3 if model_hit else 0) + (2 if marka_hit else 0)
            if bal < bosag:
                continue

            # ýyl süzgüji
            if y1 and yyl_barla:
                try:
                    cy = int(str(c.get("year") or 0)[:4])
                except Exception:
                    cy = 0
                if cy and not (y1 <= cy <= y2):
                    continue

            # býujet süzgüji (AED -> USD), 15% ýokary rugsat
            if byujet > 0:
                try:
                    aed = float(str(c.get("price") or 0).replace(",", "") or 0)
                except Exception:
                    aed = 0
                if aed > 0 and (aed / USD_RATE) > byujet * 1.15:
                    continue

            netije.append((bal, c))

        netije.sort(key=lambda x: -x[0])
        return [c for _, c in netije]

    if min_bal is not None:
        return _gec(min_bal)
    return _gec(3) or _gec(2)


def gabatla_doly(zakaz, cars, norm_fn):
    """gabatla() bilen deň, ýöne netijäniň TAKYKlygyny hem gaýtarýar.

    (maşynlar, takyk)
      takyk=True   -> model derejesinde gabat geldi (ynamly)
      takyk=False  -> diňe marka boýunça (giň netije, seresap bol)

    Bu tapawut möhüm: awtomat habar diňe TAKYK netijede iberilýär,
    ýogsa "Nissan" zakazy her gün 40 maşyn spam ederdi.
    """
    takyk = gabatla(zakaz, cars, norm_fn, min_bal=3)
    if takyk:
        return takyk, True
    return gabatla(zakaz, cars, norm_fn, min_bal=2), False


def model_aydylanmy(zakaz, cars, norm_fn):
    """
    Sargytda MODEL aydylanmy, yogsa dine MARKA barmy?

    ⚠️ 24.08 SAPAGY:
    Sargyt "Mitsubishi L200" (pikap) boldy. Shol gun L200 yokdy,
    bot bolsa marka boyuncha "Mitsubishi Mirage G4" (kici sedan)
    gorkezdi. Ishgar uchin peydasyz — mushderi pikap isleya.

    Emma sargyt dine "Toyota" bolsa, marka boyuncha gorkezmek DOGRY.
    Tapawut shu funksiyada:

      "Mitsubishi L200"  -> True  (model aydylan, takyk gerek)
      "Toyota"           -> False (dine marka, gin sanaw dogry)
      "Nissan Patrol"    -> True

    Nadip: sargydyn sozlerinden MARKA atlaryny we YYLLARY ayyras.
    Galan soz bar bolsa — model aydylan.
    """
    isleg = zakaz.get("isleg") or zakaz.get("at") or ""
    want = norm_fn(isleg)
    if not want:
        return False

    markalar = {norm_fn(c.get("brand", "")).split()[0]
                for c in (cars or []) if c.get("brand")}
    markalar.discard("")

    galan = []
    for t in want.split():
        if len(t) < 2 or t in _DUR:
            continue
        if re.fullmatch(r"(?:19|20)\d{2}", t):     # yyl
            continue
        if t in markalar:                          # marka ady
            continue
        galan.append(t)
    return bool(galan)


def model_bar_yyl_baska(zakaz, cars, norm_fn):
    """
    Isleyan MODELI bar, yone YYLY aralyga girenok — shony gaytarya.

    ⚠️ 24.08 SAPAGY — nam uchin bu gerek:
    Zakaz "Toyota Camry 2021-2023" boldy. Shol gun bazada 6 sany Camry
    bardy, hemmesi 2024-2025 we $7,760-dan bashlayardy — yagny $22,000
    byujetden ARZAN. Emma bot "Camry tapylmady" diyip, yerine
    Hilux, Mirai, Highlander gorkezdi.

    Ishgar uchin peydasyz jogap: mushderi Camry isleya, oňa Hilux
    gorkezmek soragyny chozenok. Emma "Camry bar, bir yyl taze,
    ustesine arzan" diymek — sowda.

    Shonun uchin: takyk model tapylmasa, ilki YYLDAN BASHGA hemme
    zady gabat gelyan maslynlary gozleyas. Tapylsa — ishgar sholary
    goryar, marka boyuncha giň sanaw dal.

    Byujet suzguji ISHLEYA (arzan bolsa gowy, gymmat bolsa gerek dal).
    Diňe yyl suzguji ayrylya.
    """
    isleg = zakaz.get("isleg") or zakaz.get("at") or ""
    y1, y2 = _yyllar(isleg)
    if not y1:
        return []                      # zakazda yyl yok - denesdirer zat yok
    if y1 == y2:                       # gabatla() bilen deň giňelme
        y1, y2 = y1 - 1, y2 + 1

    hemmesi = gabatla(zakaz, cars, norm_fn, min_bal=3, yyl_barla=False)
    dashynda = []
    for c in hemmesi:
        try:
            cy = int(str(c.get("year") or 0)[:4])
        except Exception:
            cy = 0
        if cy and not (y1 <= cy <= y2):
            dashynda.append(c)
    # Taze yyl ilki - mushderi kop halatda tazesini alya
    dashynda.sort(key=lambda c: -(int(str(c.get("year") or 0)[:4]) or 0))
    return dashynda


# ============================================================
# TEKST DÜZMEK
# ============================================================
def _byujet_yaz(b):
    # 24.08: byujet indi TEKST — "33000 AED", "10-12 mun dollar".
    # Erkinin yazany shol gornushde gorkezilya, gapdalynda USD garshylygy.
    if isinstance(b, dict):
        if BYUJET:
            return BYUJET.gorkez(b.get("byujet_okaldy")) \
                if b.get("byujet_okaldy") else (b.get("byujet_asyl") or "—")
        return b.get("byujet_asyl") or "—"
    # Kone gornush (san) — atiyachlyk uchin
    try:
        n = float(b or 0)
    except Exception:
        n = 0
    return f"${n:,.0f}".replace(",", " ") if n else "—"


def sanaw_teksti(zakazlar):
    """/zakazlar üçin sanaw."""
    acyk = [z for z in zakazlar if z["status"] in ACIK_STATUS]
    if not acyk:
        return "✅ *Açyk sargyt ýok.*\n\nHemmesi gutaryldy ýa ýatyryldy."

    tertip = {"Täze": 0, "Auksionda": 1, "Gözlenýär": 2, "Tapyldy": 3}
    acyk.sort(key=lambda z: (tertip.get(z["status"], 9), z.get("gosulan", "")))

    nyshan = {"Täze": "🆕", "Gözlenýär": "🔍", "Tapyldy": "📸",
              "Auksionda": "🔨"}

    # 24.08 — KART GORNUSHI (Erkin sayl ady)
    # Onki nusga: "ZAKAZLAR — 1 sany islenmeli" diyyardi, dushnuksizdi.
    # Indi: her sargyt ayratyn charchuwaly kart, arassa we resmi.
    # 24.08 — ÇARÇUWA AÝRYLDY.
    # ╭──╮ belgileri Telegramda gyşyk chykya: hat shrifti deň giňlikde
    # dal, shonun uchin cyzyk "tolkun" bolup gorunya. Erkin: "ayyr".
    # Indi: her setirin bashynda emoji — gurluş şondan gorunya.
    setirler = [f"📋 *AÇYK SARGYTLAR*  ·  {len(acyk)}"]
    for z in acyk:
        n = nyshan.get(z["status"], "•")
        kart = [
            f"{n} *{z['kod']}*  ·  {z['status']}",
            f"👤 {z['at']}",
            f"🚗 {z['isleg'] or '—'}",
            f"💰 {_byujet_yaz(z)}",
        ]
        if z.get("masyn_kody"):
            kart.append(f"🔖 `{z['masyn_kody']}`")
        setirler.append("\n".join(kart))
    return "\n\n".join(setirler)


def jikme_jik_teksti(z, tapylan=0):
    """
    Bir sargydyn doly maglumaty — sanaw bilen DEŇ kart gornushinde.

    24.08: "jikme-jik" sozi ayryldy (Erkin halamady), interfeys
    kart gornushine getirildi.
    """
    nyshan = {"Täze": "🆕", "Gözlenýär": "🔍", "Tapyldy": "📸",
              "Auksionda": "🔨"}
    n = nyshan.get(z["status"], "•")

    s = [
        f"{n} *{z['kod']}*  ·  {z['status']}",
        f"👤 {z['at']}",
        f"🚗 {z['isleg'] or '—'}",
        f"💰 {_byujet_yaz(z)}",
    ]
    if z["telefon"]:
        s.append(f"📞 {z['telefon']}")
    if z["kanal"]:
        s.append(f"📥 {z['kanal']}")
    if z["masyn_kody"]:
        s.append(f"🔖 `{z['masyn_kody']}`")
    if z["bellik"]:
        s.append(f"📝 _{z['bellik']}_")
    if tapylan:
        s.append(f"\n🔎 Auksionlarda *{tapylan}* gabat gelýän maşyn bar.")
    # Duwmeleriň nameligini dushundirya — Erkin bulashdyrdy (24.08)
    s.append("\n_Ýokarky düwme maşyn gözleýär._")
    s.append("_«→» düwmeleri sargydyň ýagdaýyny belleýär._")
    return "\n".join(s)

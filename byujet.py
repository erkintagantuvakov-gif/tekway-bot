# -*- coding: utf-8 -*-
"""
TEK — BYUJET OKAYJY
====================

MESELE (Erkin, 24.08):
  1. Kabir mushderi AED aydya, kabiri USD. Onki nusgada san
     hemishe USD hasaplanyardy — "33 000" AED yazylanda bot ony
     $33 000 (=121 000 AED) diyip okayardy, byujet suzguji ishlemeyardi.
  2. Kabir mushderide anyk baha yok: "10-12 mun dollar aralykda".

NAM UCHIN IKI SUTUN DAL:
  Erkin "AED sutunine yazsam USD sutuni ozi dolsun" diydi.
  Notion-da beyle bolmaya — formula sutunine EL BILEN yazyp bolmaya,
  iki tarapa awtomat doldurmak bolsa AYLAW (circular) bolya.
  Shonun ucin: BIR TEKST setir, bot ozi okaya.

ULANYSH:
    >>> oka("10-12 mun dollar")
    {'min_usd': 10000, 'max_usd': 12000, 'walyuta': 'USD', ...}

Okap bilmese max_usd=None gaytarya — sheyle yagdayda byujet
suzguji ULANYLMAYA (hemme masyn gorkezilya) we ishgare duydurylya.
Yalnysh suzmekden — suzmezlik gowy.
"""

import re

AED_USD = 3.6725          # 1 USD = 3.6725 AED (dur, uytgemeya)

# Walyuta achar sozleri
_AED = ("AED", "DHS", "DH", "DIRHEM", "DIRHAM", "DIRHEMLIK", "ДИРХАМ", "ДХС")
_USD = ("USD", "$", "DOLLAR", "DOLAR", "DOLLARLYK", "ДОЛЛАР", "БАКС")

# "mun" = mun/müň/tysyacha/k
_MUN = ("MÜŇ", "MUN", "MÜN", "MUŇ", "MYŇ", "MIN", "K", "ТЫС", "ТЫСЯЧ")


def _kadala(s):
    s = str(s or "").upper().strip()
    s = s.replace(",", " ").replace(" ", " ")
    s = s.replace("–", "-").replace("—", "-").replace("~", " ")
    return re.sub(r"\s+", " ", s)


def _walyuta_tap(t):
    """Tekstde AED ya USD barmy. Tapylmasa None."""
    for a in _USD:
        if a in t:
            return "USD"
    for a in _AED:
        # 'DH' gysga - baska sozun icinde bolmasyn
        if re.search(rf"\b{re.escape(a)}\b", t):
            return "AED"
    return None


def _munmi(t):
    """'10-12 mun' ya '10k' — sanlar mun bilen aydylanmy."""
    for m in _MUN:
        if re.search(rf"\b\d+\s*{re.escape(m)}\b", t) or re.search(
                rf"\b{re.escape(m)}\b", t):
            return True
    return False


def oka(tekst, ansat_walyuta="AED"):
    """
    Byujet tekstini okaya.

    ansat_walyuta — walyuta yazylmadyk bolsa nahili hasaplamaly.
      'AED' saylandy, sebabi YALNYSHSAK ZYYANY AZ:
        AED diyip okasak (hakykatda USD bolsa)  -> az masyn gorkezilya
        USD diyip okasak (hakykatda AED bolsa)  -> mushderа gotermejek
                                                   gymmat masyn hodurlenya
      Ikinjisi has erbet — shonun ucin seresap tarapy saylandy.

    Yzyna dict:
      asyl      — Erkinin yazan teksti (kartda shol gornushde gorkezilya)
      min_usd   — aralygyn ashaky cagi (bolmasa None)
      max_usd   — YOKARKY chak. Suzguc SHUNY ulanya. Okalmasa None.
      walyuta   — 'AED' / 'USD'
      anyk      — walyuta tekstde acyk yazylanmy (True/False)
    """
    asyl = str(tekst or "").strip()
    netije = {"asyl": asyl, "min_usd": None, "max_usd": None,
              "walyuta": ansat_walyuta, "anyk": False}
    if not asyl:
        return netije

    t = _kadala(asyl)

    w = _walyuta_tap(t)
    if w:
        netije["walyuta"] = w
        netije["anyk"] = True
    w = netije["walyuta"]

    # Sanlary chykar (nokat/otur ayrylan: 33.000 / 33 000)
    tt = re.sub(r"(?<=\d)[.\s](?=\d{3}\b)", "", t)
    sanlar = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", tt)]
    # Walyuta/yyl sanlaryny ayyr (1990-2030 aralygy — yyl bolmagy mumkin
    # diyip ATMAYAS, sebabi byujet 2000 AED bolup biler. Diňe 4 belgili
    # we '20xx' gornushli sanlar yyl hasap edilya EGER bashga san bar bolsa)
    if len(sanlar) > 1:
        galan = [s for s in sanlar if not (1990 <= s <= 2035 and s == int(s))]
        if galan:
            sanlar = galan
    if not sanlar:
        return netije

    mun = _munmi(t)

    def kadala_san(s):
        if mun:
            return s * 1000
        # "10-12" yaly kici sanlar — hokman mun (hic bir masyn $12 dal)
        if s < 500:
            return s * 1000
        return s

    sanlar = [kadala_san(s) for s in sanlar]
    sanlar.sort()

    ashak = sanlar[0]
    yokar = sanlar[-1]

    if w == "AED":
        ashak /= AED_USD
        yokar /= AED_USD

    netije["min_usd"] = int(round(ashak))
    netije["max_usd"] = int(round(yokar))
    return netije


def gorkez(b):
    """
    Kartda gorkezilyan setir.
    Erkinin yazany + USD garshylygy (eger AED yazylan bolsa).
    """
    if not b or not b.get("asyl"):
        return "—"
    asyl = b["asyl"]
    mx = b.get("max_usd")
    if mx is None:
        return f"{asyl}  ⚠️"
    # USD-de yazylan bolsa gaytalap gorkezmeyas
    if b.get("walyuta") == "USD" and b.get("anyk"):
        return asyl
    mn = b.get("min_usd")
    if mn and mn != mx:
        return f"{asyl}   ·   ≈ ${mn:,}-{mx:,}".replace(",", " ")
    return f"{asyl}   ·   ≈ ${mx:,}".replace(",", " ")


if __name__ == "__main__":
    synaglar = [
        "33000 AED", "33 000 AED", "$22000", "22 000 USD",
        "10-12 mun dollar", "10-12 müň $", "10 - 12 mun dollar",
        "25 mun dirhem", "40000", "8000", "$10 000 - 12 000",
        "12k usd", "120 000 AED", "2021-2023 Camry ucin 15 mun dollar",
        "", "bilemok",
    ]
    print(f"{'YAZYLAN':<34} {'WAL':<5} {'ANYK':<5} {'USD aralyk':<20} KARTDA")
    print("-" * 100)
    for s in synaglar:
        b = oka(s)
        ar = (f"{b['min_usd']}-{b['max_usd']}"
              if b["min_usd"] != b["max_usd"] else str(b["max_usd"]))
        print(f"{s or '(bosh)':<34} {b['walyuta']:<5} "
              f"{str(b['anyk']):<5} {ar:<20} {gorkez(b)}")

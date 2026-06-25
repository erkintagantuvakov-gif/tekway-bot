#!/usr/bin/env python3
"""
TEK WAY MOTORS — PDF to Database Converter
PDF-den maşyn suratlaryny we maglumatlaryny çykarýar
cars_database.json döredýär
"""

import json
import re
import sys
from pathlib import Path
import subprocess

# ============================================================
# TM SÜZGÜJI
# ============================================================

YEAR_MIN = 2021
YEAR_MAX = 2026

BANNED_BRANDS = [
    "DODGE", "CADILLAC", "FERRARI", "PORSCHE", "LAMBORGHINI",
    "LAND", "RANGE", "GMC", "TESLA", "JEEP", "MASERATI",
    "POLARIS", "BMW",  # TM-a girmeýär
]

BANNED_MODELS = ["SUPRA", "MUSTANG", "CORVETTE", "BZ4X"]

# ============================================================
# AUKSION ADY - faýl adyndan çykar
# ============================================================

def get_auction_name(pdf_path):
    name = Path(pdf_path).stem.upper()
    if "FADAK" in name:
        return "Fadak Cars Auction"
    elif "MARHABA" in name:
        return "Marhaba Auction"
    elif "NOJOOM" in name:
        return "Nojoom Cars Auction"
    elif "EMIRATES" in name:
        return "Emirates Auction"
    elif "QARYAH" in name:
        return "Al Qaryah Auctions"
    elif "WEST" in name:
        return "West Cars Auctions"
    elif "GULF" in name:
        return "Gulf Cars Auction"
    elif "BURJ" in name:
        return "Burj Khaibar Cars Auction"
    else:
        return Path(pdf_path).stem.replace("_", " ").title()

# ============================================================
# MAŞYN MAGLUMATYNY TEKSTEN ÇYKAR
# ============================================================

def parse_car_text(text):
    """Teksten year, brand, model çykar"""
    if not text:
        return None
    
    text_upper = text.upper().strip()
    
    # "2024 TOYOTA CAMRY" ýaly format
    m = re.search(r'\b(20[2-9]\d)\s+([A-Z][A-Z\-]+)\s+([A-Z][A-Z0-9\s\-]+)', text_upper)
    if m:
        year = int(m.group(1))
        brand = m.group(2).strip()
        model = m.group(3).strip()
        # Modeli ilkinji 2 söze çenli kes
        model_words = model.split()[:2]
        model = " ".join(model_words)
        return {"year": year, "brand": brand, "model": model}
    
    return None

# ============================================================
# TM SÜZGÜJI
# ============================================================

def is_allowed(car):
    """Maşyn TM-a girip bilermi?"""
    if not car:
        return False
    
    year = car.get("year", 0)
    brand = car.get("brand", "").upper()
    model = car.get("model", "").upper()
    
    if year < YEAR_MIN or year > YEAR_MAX:
        return False
    
    for banned in BANNED_BRANDS:
        if banned in brand:
            return False
    
    for banned_model in BANNED_MODELS:
        if banned_model in model:
            return False
    
    return True

# ============================================================
# ESASY FUNKSIYA
# ============================================================

def pdf_to_database(pdf_path, output_dir, output_json, skip_pages=4):
    """
    PDF-den surat + maglumat çykar, JSON döret
    skip_pages: başdaky neçe sahypany geç (baş sahypalar)
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    auction_name = get_auction_name(pdf_path)
    print(f"Auksion: {auction_name}")
    print(f"PDF: {pdf_path.name}")
    
    # Sahypa sany
    import pdfplumber
    with pdfplumber.open(str(pdf_path)) as pdf:
        total_pages = len(pdf.pages)
        print(f"Jemi sahypa: {total_pages}")
        
        cars = []
        skipped = 0
        banned = 0
        
        for i in range(skip_pages, total_pages):
            page_num = i + 1
            
            # Teksti al
            page = pdf.pages[i]
            text = page.extract_text() or ""
            
            # Maşyn maglumatyny çykar
            car_info = parse_car_text(text)
            
            if not car_info:
                continue
            
            # TM süzgüji
            if not is_allowed(car_info):
                banned += 1
                print(f"  ❌ Sahypa {page_num}: {car_info['year']} {car_info['brand']} {car_info['model']} — gadagan")
                continue
            
            # Sahypany surat et
            img_filename = f"car_{page_num:03d}_{car_info['brand']}_{car_info['model'].replace(' ', '_')}.jpg"
            img_path = output_dir / img_filename
            
            result = subprocess.run([
                "pdftoppm", "-jpeg", "-r", "120",
                "-f", str(page_num), "-l", str(page_num),
                str(pdf_path), str(output_dir / f"tmp_{page_num:03d}")
            ], capture_output=True)
            
            # pdftoppm faýl adyny özi goşýar
            import glob
            tmp_files = glob.glob(str(output_dir / f"tmp_{page_num:03d}*.jpg"))
            if tmp_files:
                import shutil
                shutil.move(tmp_files[0], str(img_path))
            
            car_record = {
                "brand": car_info["brand"].title(),
                "model": car_info["model"].title(),
                "year": car_info["year"],
                "price": None,
                "auction": auction_name,
                "image_path": str(img_path),
                "page": page_num
            }
            
            cars.append(car_record)
            print(f"  ✅ Sahypa {page_num}: {car_info['year']} {car_info['brand']} {car_info['model']}")
        
        # JSON ýaz
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(cars, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Jemi: {len(cars)} maşyn saklandi")
        print(f"❌ Gadagan: {banned} maşyn aýyryldy")
        print(f"📁 Suratlar: {output_dir}")
        print(f"📄 JSON: {output_json}")
        
        return cars


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Ulanylyş: python pdf_to_database.py input.pdf [output_dir] [output.json]")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "car_images"
    out_json = sys.argv[3] if len(sys.argv) > 3 else "cars_database.json"
    
    pdf_to_database(pdf_file, out_dir, out_json)

